import streamlit as st
import pandas as pd
from io import BytesIO
import openai
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill
import hashlib


# ------------------------ UI CONFIGURATION ------------------------
st.set_page_config(page_title="Master Pick Ticket Generator", layout="wide")
st.title("📦 Master Pick Ticket Generator – Pick by Cart")

# ------------------------ FILE UPLOADS ------------------------
st.sidebar.header("📂 Upload Input Files")
picking_pool_file = st.sidebar.file_uploader("Upload Picking Pool Excel file", type=["xlsx"])
sku_master_file = st.sidebar.file_uploader("Upload SKU Master Excel file", type=["xlsx"])

# Filter option
gi_type = st.sidebar.radio("Filter by GI Type", ("All", "Single-line", "Multi-line"))

# ------------------------ HELPER FUNCTIONS ------------------------
def calculate_carton_info(row):
    pq = row.get('PickingQty', 0) or 0
    qpc = row.get('Qty per Carton', 0) or 0
    iv = row.get('Item Vol', 0) or 0
    qpco = row.get('Qty Commercial Box',0) or 0

    if pq == 0 or qpc == 0 or iv == 0:
        return pd.Series({'CartonCount': None, 'CartonDescription': 'Invalid'})

    cartons = int(pq // qpc)
    loose = pq % qpc

    carton_sizes = [
        (1200, "1XS"),
        (6000, "1S"),
        (12000, "1Rectangle"),
        (48000, "1L"),
        (float('inf'), "Too Big")
    ]

    if loose > 0:
            # For loose >=1, calculate loose volume normally
            looseVol = loose/qpco * iv

            looseBox = next(name for max_vol, name in carton_sizes if looseVol <= max_vol)
    
            desc = f"{cartons} Commercial Carton + {looseBox}" if cartons > 0 else looseBox
            totalC = cartons + 1
    else:
            desc = f"{cartons} Commercial Carton"
            totalC = cartons

    return pd.Series({'CartonCount': totalC, 'CartonDescription': desc})



def classify_gi(volume):
    if volume < 35000:
        return 'Bin'
    elif volume < 248500:
        return 'Layer'
    else:
        return 'Pick by Orders'


# ------------------------ DATA PROCESSING ------------------------
if picking_pool_file and sku_master_file:
    try:
        picking_pool = pd.read_excel(picking_pool_file)
        sku_master = pd.read_excel(sku_master_file)

        # Filter valid delivery dates
        picking_pool['DeliveryDate'] = pd.to_datetime(picking_pool['DeliveryDate'], errors='coerce')
        picking_pool = picking_pool[picking_pool['DeliveryDate'].notna()]
        picking_pool['DeliveryDate'] = picking_pool['DeliveryDate'].dt.normalize()  # time set to 00:00:00



        # 🆕 Filter for Zone "A" and Location starting with "A-" or "SOFT-"
        picking_pool['LocationType'] = picking_pool['LocationType'].astype(str).str.strip().str.lower()
        
        picking_pool = picking_pool[
            (picking_pool['Zone'] == 'A') &
            (
                picking_pool['Location'].astype(str).str.startswith('A-') |
                picking_pool['Location'].astype(str).str.startswith('SOFT-')
            ) &
            (picking_pool['LocationType'] != 'storage')
        ]


        # Sidebar date input
        min_date, max_date = picking_pool['DeliveryDate'].min(), picking_pool['DeliveryDate'].max()
        delivery_range = st.sidebar.date_input("🗕️ Filter by Delivery Date", (min_date, max_date), min_value=min_date, max_value=max_date)

        if isinstance(delivery_range, tuple) and len(delivery_range) == 2:
            start, end = pd.to_datetime(delivery_range[0]), pd.to_datetime(delivery_range[1])
            picking_pool = picking_pool[(picking_pool['DeliveryDate'] >= start) & (picking_pool['DeliveryDate'] <= end)]

        # Remove GIs with missing info
        merged_check = picking_pool.merge(sku_master, how='left', left_on='SKU', right_on='SKU Code')
        missing_issues = merged_check[
            merged_check['Qty Commercial Box'].isna() |
            merged_check['Qty per Carton'].isna() |
            merged_check['Item Vol'].isna()
        ]['IssueNo'].unique()
        picking_pool = picking_pool[~picking_pool['IssueNo'].isin(missing_issues)]

        # Merge actual data
        df = picking_pool.merge(sku_master, how='left', left_on='SKU', right_on='SKU Code')

        # Fill & compute
        df['PickingQty'] = df['PickingQty'].fillna(0)
        df['Item Vol'] = df['Item Vol'].fillna(0)
        df['Qty Commercial Box'] = df['Qty Commercial Box'].replace(0, 1).fillna(1)
        df['Qty per Carton'] = df['Qty per Carton'].replace(0, 1).fillna(1)
        df['Total Item Vol'] = (df['PickingQty'] / df['Qty Commercial Box']) * df['Item Vol']

        # GI volume and line count
        df = df.merge(df.groupby('IssueNo')['Total Item Vol'].sum().rename('Total GI Vol'), on='IssueNo')
        df = df.merge(df.groupby('IssueNo').size().rename('Line Count'), on='IssueNo')

        # STEP 1: Classify GI (e.g., Bin or Layer)
        df['GI Class'] = df['Total GI Vol'].apply(classify_gi)

        # 🚫 Exclude GIs classified as "Pick by Orders"
        df = df[df['GI Class'] != 'Pick by Orders']
        # ✅ Assign unique BinNo per GI (only for 'Bin' class)
        bin_gi_issues = df[df['GI Class'] == 'Bin']['IssueNo'].unique()
        bin_no_mapping = {issue: f"Bin{str(i+1).zfill(3)}" for i, issue in enumerate(sorted(bin_gi_issues))}
        df['BinNo'] = df['IssueNo'].map(bin_no_mapping)


        # STEP 2: Assign GI Index (per GI No)
        df['GI Index'] = df.groupby('IssueNo').cumcount() + 1

        # STEP 3: Merge into 'Type'
        df['Type'] = df['GI Class'] + ' ' + df['GI Index'].astype(str)

        # Split data
        single_line = df[df['Line Count'] == 1].copy()
        multi_line = df[df['Line Count'] > 1].copy()

        # Job Assignment - Single line
        job_counter = 1
        single_jobs = []
        for name, group in single_line.groupby('ShipToName'):
            group = group.sort_values('IssueNo')
            group['GI_Group_Index'] = group.groupby('IssueNo').ngroup()
            group['JobNo'] = group['GI_Group_Index'].apply(lambda x: f"Job{str(job_counter + x // 5).zfill(3)}")
            job_counter += (group['GI_Group_Index'].nunique() + 4) // 5
            single_jobs.append(group)
        single_line_final = pd.concat(single_jobs)

        # Job Assignment - Multi-line
        multi_summary = multi_line[['IssueNo', 'Total GI Vol']].drop_duplicates().sort_values('Total GI Vol')
        multi_line['JobNo'] = None
        current_job, current_vol, job_id = [], 0, job_counter

        for _, row in multi_summary.iterrows():
            if current_vol + row['Total GI Vol'] > 600000:
                for gi in current_job:
                    multi_line.loc[multi_line['IssueNo'] == gi, 'JobNo'] = f"Job{str(job_id).zfill(3)}"
                job_id += 1
                current_job, current_vol = [], 0
            current_job.append(row['IssueNo'])
            current_vol += row['Total GI Vol']
        for gi in current_job:
            multi_line.loc[multi_line['IssueNo'] == gi, 'JobNo'] = f"Job{str(job_id).zfill(3)}"

        # Combine all
        final_df = pd.concat([single_line_final, multi_line], ignore_index=True)

        # GI type filter
        if gi_type == "Single-line":
            final_df = final_df[final_df['Line Count'] == 1]
        elif gi_type == "Multi-line":
            final_df = final_df[final_df['Line Count'] > 1]

        # Carton Info
        final_df = pd.concat([final_df, final_df.apply(calculate_carton_info, axis=1)], axis=1)

        # Extra columns
        final_df['Batch No'] = final_df.get('StorageLocation')
        final_df['Commercial Box Count'] = final_df['PickingQty'] / final_df['Qty Commercial Box']

        output_df = final_df[[ 
            'IssueNo',
            'SKU',
            'Location_x',
            'SKUDescription',
            'Batch No',
            'PickingQty',
            'Qty per Carton',
            'Commercial Box Count',
            'DeliveryDate',
            'ShipToName',
            'Type',
            'JobNo',
            'CartonDescription',
            'LocationType',
            'Total GI Vol'
        ]].drop_duplicates()

        st.success("✅ Processing complete!")
        st.dataframe(output_df.head(20))

        # Download
                # Download
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            output_df.to_excel(writer, index=False, sheet_name='Master Pick Ticket')
            workbook = writer.book
            worksheet = writer.sheets['Master Pick Ticket']
        
            # --- Autofit column widths ---
            for col_idx, column_cells in enumerate(worksheet.columns, 1):
                max_length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
                adjusted_width = max_length + 2
                worksheet.column_dimensions[get_column_letter(col_idx)].width = adjusted_width
        
        
        # --- Find SKUs with multiple Batch No ---
        sku_batch_groups = output_df.groupby('SKU')['Batch No'].nunique()
        skus_with_multiple_batches = sku_batch_groups[sku_batch_groups > 1].index.tolist()
        


        # Clean whitespace and ensure strings
        output_df['Batch No'] = output_df['Batch No'].astype(str).str.strip()
        output_df['SKU'] = output_df['SKU'].astype(str).str.strip()
    
        # Group and identify SKUs with multiple Batch Nos
        sku_batch_groups = output_df.groupby('SKU')['Batch No'].nunique()
        print("SKUs with multiple Batch Nos:")
        print(sku_batch_groups[sku_batch_groups > 1])  # DEBUG: check if your SKU appears here
        
        skus_with_multiple_batches = sku_batch_groups[sku_batch_groups > 1].index.tolist()
    
    def get_color_for_sku(sku):
        hex_hash = hashlib.md5(str(sku).encode()).hexdigest()
        return hex_hash[:6].upper()
    
    used_fills = {}
    
    sku_rows = output_df[output_df['SKU'].isin(skus_with_multiple_batches)].index
    
    for idx in sku_rows:
        sku = output_df.at[idx, 'SKU']
        fill_color = get_color_for_sku(sku)
        
        if fill_color not in used_fills:
            used_fills[fill_color] = PatternFill(start_color=fill_color, end_color=fill_color, fill_type='solid')
        
        row_num = idx + 2  # Adjust for header and Excel indexing
        for col in range(1, worksheet.max_column + 1):
            worksheet.cell(row=row_num, column=col).fill = used_fills[fill_color]



        


        st.download_button(
            label="⬇️ Download Master Pick Ticket Excel",
            data=output.getvalue(),
            file_name="MasterPickTicket.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Store for AI
        st.session_state["final_df"] = final_df

    except Exception as e:
        st.error(f"❌ Error during processing: {e}")

else:
    st.info("👈 Please upload both Picking Pool and SKU Master Excel files to begin.")
