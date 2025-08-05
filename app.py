# Modified section of your Streamlit app - Full code with corrected multi-line JobNo logic

import streamlit as st
import pandas as pd
from io import BytesIO
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill
from itertools import cycle

# ------------------------ UI CONFIGURATION ------------------------
st.set_page_config(page_title="Master Pick Ticket Generator", layout="wide")
st.title("📦 Master Pick Ticket Generator – Pick by Cart")

# ------------------------ FILE UPLOADS ------------------------
st.sidebar.header("📂 Upload Input Files")
picking_pool_file = st.sidebar.file_uploader("Upload Picking Pool Excel file", type=["xlsx"])
sku_master_file = st.sidebar.file_uploader("Upload SKU Master Excel file", type=["xlsx"])

# ------------------------ HELPER FUNCTIONS ------------------------
def calculate_carton_info(row):
    pq = row.get('PickingQty', 0) or 0
    qpc = row.get('Qty per Carton', 0) or 0
    iv = row.get('Item Vol', 0) or 0
    qpco = row.get('Qty Commercial Box', 0) or 0

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
        looseVol = loose / qpco * iv
        looseBox = next(name for max_vol, name in carton_sizes if looseVol <= max_vol)
        desc = f"{cartons} Commercial Carton + {looseBox}" if cartons > 0 else looseBox
        totalC = cartons + 1
    else:
        desc = f"{cartons} Commercial Carton"
        totalC = cartons

    return pd.Series({'CartonCount': totalC, 'CartonDescription': desc})

def classify_gi(volume):
    if pd.isna(volume):
        return 'Unknown'
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

        picking_pool['DeliveryDate'] = pd.to_datetime(picking_pool['DeliveryDate'], errors='coerce')
        picking_pool = picking_pool[picking_pool['DeliveryDate'].notna()]
        picking_pool['DeliveryDateStr'] = picking_pool['DeliveryDate'].dt.strftime("%Y-%m-%d")

        picking_pool['LocationType'] = picking_pool['LocationType'].astype(str).str.strip().str.lower()
        grnos_with_storage = picking_pool[picking_pool['LocationType'] == 'storage']['IssueNo'].unique()
        picking_pool = picking_pool[~picking_pool['IssueNo'].isin(grnos_with_storage)]
        picking_pool = picking_pool[(picking_pool['Zone'] == 'A') & (
            picking_pool['Location'].astype(str).str.startswith('A-') |
            picking_pool['Location'].astype(str).str.startswith('SOFT-')
        )]

        gi_type = st.sidebar.radio("Filter by GI Type", ("All", "Single-line", "Multi-line"))

        min_date, max_date = picking_pool['DeliveryDate'].min(), picking_pool['DeliveryDate'].max()
        delivery_range = st.sidebar.date_input("🗕️ Filter by Delivery Date", (min_date, max_date), min_value=min_date, max_value=max_date)

        if isinstance(delivery_range, tuple) and len(delivery_range) == 2:
            start, end = pd.to_datetime(delivery_range[0]), pd.to_datetime(delivery_range[1])
            picking_pool = picking_pool[(picking_pool['DeliveryDate'] >= start) & (picking_pool['DeliveryDate'] <= end)]

        merged_check = picking_pool.merge(sku_master, how='left', left_on='SKU', right_on='SKU Code')
        missing_issues = merged_check[
            merged_check['Qty Commercial Box'].isna() |
            merged_check['Qty per Carton'].isna() |
            merged_check['Item Vol'].isna()
        ]['IssueNo'].unique()
        picking_pool = picking_pool[~picking_pool['IssueNo'].isin(missing_issues)]

        df = picking_pool.merge(sku_master, how='left', left_on='SKU', right_on='SKU Code')
        df['PickingQty'] = df['PickingQty'].fillna(0)
        df['Item Vol'] = df['Item Vol'].fillna(0)
        df['Qty Commercial Box'] = df['Qty Commercial Box'].replace(0, 1).fillna(1)
        df['Qty per Carton'] = df['Qty per Carton'].replace(0, 1).fillna(1)
        df['Total Item Vol'] = (df['PickingQty'] / df['Qty Commercial Box']) * df['Item Vol']

        df = df.merge(df.groupby('IssueNo')['Total Item Vol'].sum().rename('Total GI Vol'), on='IssueNo')
        df = df.merge(df.groupby('IssueNo').size().rename('Line Count'), on='IssueNo')

        df['GI Class'] = df['Total GI Vol'].apply(classify_gi)
        df = df[df['Total GI Vol'] <= 248500]


        bin_gi_issues = df[df['GI Class'] == 'Bin']['IssueNo'].unique()
        layer_gi_issues = df[df['GI Class'] == 'Layer']['IssueNo'].unique()

        bin_no_mapping = {issue: f"Bin{str(i+1).zfill(3)}" for i, issue in enumerate(sorted(bin_gi_issues))}
        layer_no_mapping = {issue: f"Layer{str(i+1).zfill(3)}" for i, issue in enumerate(sorted(layer_gi_issues))}

        df['BinNo'] = df['IssueNo'].map(bin_no_mapping)
        df['LayerNo'] = df['IssueNo'].map(layer_no_mapping)
        df['Type'] = df.apply(lambda row: row['BinNo'] if row['GI Class'] == 'Bin' else row['LayerNo'], axis=1)

        single_line = df[df['Line Count'] == 1].copy()
        multi_line = df[df['Line Count'] > 1].copy()

        # --- Assign Jobs to Single Line GIs ---
        job_counter = 1
        single_jobs = []
        for name, group in single_line.groupby('ShipToName'):
            group = group.sort_values('IssueNo')
            group['GI_Group_Index'] = group.groupby('IssueNo').ngroup()
            group['JobNo'] = group['GI_Group_Index'].apply(lambda x: f"Job{str(job_counter + x // 5).zfill(3)}")
            job_counter += (group['GI_Group_Index'].nunique() + 4) // 5
            single_jobs.append(group)
        single_line_final = pd.concat(single_jobs)

        # --- Assign Jobs to Multi-line GIs ---
        issue_vols = multi_line.groupby('IssueNo')['Total GI Vol'].first().to_dict()
        # ✅ Corrected version: only one row per IssueNo
        multi_summary = (
            multi_line
            .drop_duplicates(subset='IssueNo')  # Ensures only one entry per GI
            [['IssueNo', 'Total GI Vol']]
            .sort_values(by="Total GI Vol", ascending=False)
        )

        jobs = []
        job_limits = []
        max_vol = 600000

        for _, row in multi_summary.iterrows():
            issue_no = row['IssueNo']
            volume = row['Total GI Vol']
            placed = False
            for i, used_vol in enumerate(job_limits):
                if used_vol + volume <= max_vol:
                    jobs[i].append((issue_no, volume))
                    job_limits[i] += volume
                    placed = True
                    break
            if not placed:
                jobs.append([(issue_no, volume)])
                job_limits.append(volume)

        job_assignments = {}
        for i, job in enumerate(jobs, start=job_counter):
            job_no = f"Job{str(i).zfill(3)}"
            total_vol = sum(vol for _, vol in job)
            if total_vol > max_vol:
                st.warning(f"⚠️ {job_no} exceeds 600000 vol: {total_vol}")
            for issue_no, _ in job:
                job_assignments[issue_no] = job_no

        multi_line['JobNo'] = multi_line['IssueNo'].map(job_assignments)

        # Combine final
        final_df = pd.concat([single_line_final, multi_line], ignore_index=True)

        if gi_type == "Single-line":
            final_df = final_df[final_df['Line Count'] == 1]
        elif gi_type == "Multi-line":
            final_df = final_df[final_df['Line Count'] > 1]

        final_df = pd.concat([final_df, final_df.apply(calculate_carton_info, axis=1)], axis=1)
        final_df['Batch No'] = final_df.get('StorageLocation')
        final_df['Commercial Box Count'] = final_df['PickingQty'] / final_df['Qty Commercial Box']

        output_df = final_df[[
            'IssueNo', 'SKU', 'Location_x', 'SKUDescription', 'Batch No', 'PickingQty',
            'Qty per Carton', 'Commercial Box Count', 'DeliveryDate', 'ShipToName',
            'Type', 'JobNo', 'CartonDescription', 'Total GI Vol'
        ]].drop_duplicates()

        st.success("✅ Processing complete!")
        st.dataframe(output_df.head(20))

        # --- Excel Export ---
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            output_df.to_excel(writer, index=False, sheet_name='Master Pick Ticket')
            worksheet = writer.sheets['Master Pick Ticket']

            for col_idx, column_cells in enumerate(worksheet.columns, 1):
                max_length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
                worksheet.column_dimensions[get_column_letter(col_idx)].width = max_length + 2

            sku_batch_group = output_df.groupby('SKU')['Batch No'].nunique()
            skus_with_diff_batch = sku_batch_group[sku_batch_group > 1].index

            color_cycle = cycle([
                PatternFill(start_color="CCC0DA", end_color="CCC0DA", fill_type="solid"),
                PatternFill(start_color="FCD5B4", end_color="FCD5B4", fill_type="solid"),
                PatternFill(start_color="E6B8B7", end_color="E6B8B7", fill_type="solid"),
                PatternFill(start_color="D8E4BC", end_color="D8E4BC", fill_type="solid"),
                PatternFill(start_color="FFFF99", end_color="FFFF99", fill_type="solid"),
            ])

            sku_color_map = {sku: next(color_cycle) for sku in skus_with_diff_batch}

            for row in worksheet.iter_rows(min_row=2, min_col=1, max_col=worksheet.max_column):
                sku_cell = row[1]
                if sku_cell.value in sku_color_map:
                    for cell in row:
                        cell.fill = sku_color_map[sku_cell.value]

            output.seek(0)

        st.download_button(
            label="Download Master Pick Ticket",
            data=output,
            file_name="master_pick_ticket.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.session_state["final_df"] = final_df

    except Exception as e:
        st.error(f"❌ Error during processing: {e}")

else:
    st.info("👈 Please upload both Picking Pool and SKU Master Excel files to begin.")


