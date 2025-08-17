Your code is quite organized, but I see some areas where we can make it more compact, readable, and efficient. Here's a tidied-up version with some optimizations, better structure, and comments:

### Changes:

1. **Imports**: Cleaned up the imports, grouping standard libraries and third-party libraries together for clarity.
2. **Helper Functions**: Reorganized function definitions to reduce redundancy.
3. **General Formatting**: Cleaned up spaces, indentation, and comments to make it easier to follow.
4. **Error Handling**: Added some consistency in error messaging.
5. **Function Structure**: Reduced repetitive lines (like `fillna(0)` and `replace(0, 1)`).

Here’s the revised version:

```python
import streamlit as st
import pandas as pd
from io import BytesIO
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill
from itertools import cycle
from datetime import datetime
from zoneinfo import ZoneInfo

# ------------------------ UI CONFIGURATION ------------------------
st.set_page_config(page_title="Master Pick Ticket Generator", layout="wide")
st.title("📦 Master Pick Ticket Generator – Pick by Cart")

# ------------------------ FILE UPLOADS ------------------------
st.sidebar.header("📂 Upload Input Files")
picking_pool_file = st.sidebar.file_uploader("Upload Picking Pool Excel file", type=["xlsx"])
sku_master_file = st.sidebar.file_uploader("Upload SKU Master Excel file", type=["xlsx"])

# ------------------------ HELPER FUNCTIONS ------------------------

def calculate_carton_info(row):
    pq, qpc, iv, qpco = row.get('PickingQty', 0), row.get('Qty per Carton', 0), row.get('Item Vol', 0), row.get('Qty Commercial Box', 0)

    if pq == 0 or qpc == 0 or iv == 0:
        return pd.Series({'CartonCount': None, 'CartonDescription': 'Invalid'})

    cartons, loose = divmod(pq, qpc)
    carton_sizes = [(1200, "1XS"), (6000, "1S"), (12000, "1Rectangle"), (48000, "1L"), (float('inf'), "Too Big")]

    if loose > 0:
        looseVol = loose / qpco * iv
        looseBox = next(name for max_vol, name in carton_sizes if looseVol <= max_vol)
        desc = f"{cartons} Commercial Carton + {looseBox}" if cartons > 0 else looseBox
        totalC = cartons + 1
    else:
        desc, totalC = f"{cartons} Commercial Carton", cartons

    return pd.Series({'CartonCount': totalC, 'CartonDescription': desc})

def classify_gi(volume):
    if pd.isna(volume): return 'Unknown'
    return 'Bin' if volume < 35000 else ('Layer' if volume < 248500 else 'Pick by Orders')

def load_data(picking_pool_file, sku_master_file):
    picking_pool = pd.read_excel(picking_pool_file)
    sku_master = pd.read_excel(sku_master_file)

    picking_pool['DeliveryDate'] = pd.to_datetime(picking_pool['DeliveryDate'], errors='coerce')
    picking_pool = picking_pool[picking_pool['DeliveryDate'].notna()]
    picking_pool['Delivery Date'] = picking_pool['DeliveryDate'].dt.strftime("%Y-%m-%d")
    
    return picking_pool, sku_master

def filter_picking_pool(df):
    df['LocationType'] = df['LocationType'].str.strip().str.lower()
    grnos_with_storage = df[df['LocationType'] == 'storage']['IssueNo'].unique()
    df = df[~df['IssueNo'].isin(grnos_with_storage)]
    return df[df['Zone'] == 'A' & (df['Location'].str.startswith('A-') | df['Location'].str.startswith('SOFT-'))]

def apply_delivery_date_filter(df, delivery_range):
    if isinstance(delivery_range, tuple) and len(delivery_range) == 2:
        start, end = pd.to_datetime(delivery_range[0]), pd.to_datetime(delivery_range[1])
        return df[(df['DeliveryDate'] >= start) & (df['DeliveryDate'] <= end)]
    return df

def merge_and_clean(df, sku_master):
    df = df.merge(sku_master, how='left', left_on='SKU', right_on='SKU Code')
    df = df.dropna(subset=['Qty Commercial Box', 'Qty per Carton', 'Item Vol'])
    df['PickingQty'] = df['PickingQty'].fillna(0)
    df['Qty Commercial Box'] = df['Qty Commercial Box'].replace(0, 1).fillna(1)
    df['Qty per Carton'] = df['Qty per Carton'].replace(0, 1).fillna(1)
    df['Total Item Vol'] = (df['PickingQty'] / df['Qty Commercial Box']) * df['Item Vol']
    return df

def add_line_count(df):
    line_counts = df.groupby('IssueNo').size()
    df['Line Count'] = df['IssueNo'].map(line_counts)
    return df

def classify_and_assign(df):
    df = df.merge(df.groupby('IssueNo')['Total Item Vol'].sum().rename('Total GI Vol'), on='IssueNo')
    df = add_line_count(df)
    df['GI Class'] = df['Total GI Vol'].apply(classify_gi)
    df = df[df['Total GI Vol'] <= 248500]

    bin_gi_issues, layer_gi_issues = df[df['GI Class'] == 'Bin']['IssueNo'].unique(), df[df['GI Class'] == 'Layer']['IssueNo'].unique()

    bin_no_mapping = {issue: f"Bin{str(i+1).zfill(3)}" for i, issue in enumerate(sorted(bin_gi_issues))}
    layer_no_mapping = {issue: f"Layer{str(i+1).zfill(3)}" for i, issue in enumerate(sorted(layer_gi_issues))}
    df['BinNo'] = df['IssueNo'].map(bin_no_mapping)
    df['LayerNo'] = df['IssueNo'].map(layer_no_mapping)
    df['Type'] = df.apply(lambda row: row['BinNo'] if row['GI Class'] == 'Bin' else row['LayerNo'], axis=1)

    return df

def assign_job_numbers_with_scenarios(df):
    """
    Assign Job No with advanced logic:
    - Combine 2 Bins + 1 Layer
    - Group 3 to 4 Bins per Job No
    - Group 2 to 3 Layers per Job No
    """
    df_copy = df.copy()
    gi_info = df_copy[['IssueNo', 'ShipToName', 'Line Count', 'GI Class', 'DeliveryDate']].drop_duplicates('IssueNo')
    single_line, multi_line = gi_info[gi_info['Line Count'] == 1], gi_info[gi_info['Line Count'] > 1]

    job_no_counter = 1

    # Single-line GIs: Group by ShipToName + DeliveryDate
    for (shipto, delivery_date), group in single_line.groupby(['ShipToName', 'DeliveryDate']):
        issues = group['IssueNo'].tolist()
        chunks = [issues[i:i+5] for i in range(0, len(issues), 5)]
        for chunk in chunks:
            job_no_str = f"Job{str(job_no_counter).zfill(3)}"
            single_line.loc[single_line['IssueNo'].isin(chunk), 'Job No'] = job_no_str
            job_no_counter += 1

    # Multi-line GIs: Group by DeliveryDate
    multi_line['Job No'] = None
    for delivery_date, group in multi_line.groupby('DeliveryDate'):
        bins, layers = group[group['GI Class'] == 'Bin']['IssueNo'].tolist(), group[group['GI Class'] == 'Layer']['IssueNo'].tolist()
        assigned_issues = set()

        # Combine 2 Bins + 1 Layer
        while len(bins) >= 2 and len(layers) >= 1:
            selected_bins = bins[:2]
            selected_layer = layers[0]
            job_issues = selected_bins + [selected_layer]
            job_no_str = f"Job{str(job_no_counter).zfill(3)}"
            multi_line.loc[multi_line['IssueNo'].isin(job_issues), 'Job No'] = job_no_str
            job_no_counter += 1
            assigned_issues.update(job_issues)
            bins, layers = bins[2:], layers[1:]

        # Remaining Bins or Layers
        for remaining_issue in bins + layers:
            if remaining_issue not in assigned_issues:
                job_no_str = f"Job{str(job_no_counter).zfill(3)}"
                multi_line.loc[multi_line['IssueNo'] == remaining_issue, 'Job No'] = job_no_str
                job_no_counter += 1

    # Merge job numbers back to dataframe
    job_no_map = pd.concat([single_line[['IssueNo', 'Job No']], multi_line[['IssueNo', 'Job No']]])
    df_copy = df_copy.merge(job_no_map.drop_duplicates('IssueNo'), on='IssueNo', how='left')
    
    return df_copy

def finalize_output(df, gi_type):
    if gi_type == "Single-line":
        df = df[df['Line Count'] == 1]
    elif gi_type == "Multi-line":
        df = df[df['Line Count'] > 1]

    # Calculate carton info and add required columns
    df[['CartonCount', 'CartonDescription']] = df.apply(calculate_carton_info, axis=1)
    df['Batch No'] = df.get('StorageLocation')
    df['Commercial Box Count'] = df['PickingQty'] / df['Qty Commercial Box']

    # Final output columns
    return df[[
        'IssueNo', 'SKU', 'Location_x', 'SKUDescription', 'Batch No', 'PickingQty',
        'Commercial Box Count', 'Delivery Date', 'ShipToName', 'Type', 'Job No', 'CartonDescription'
    ]].drop_duplicates()

def export_to_excel(output_df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        output_df.to_excel(writer, index=False, sheet_name='Master Pick Ticket')
        worksheet = writer.sheets['Master Pick Ticket']

        # Adjust column widths
        for col_idx, column_cells in enumerate(worksheet.columns, 1):
            max_length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
            worksheet.column_dimensions[get_column_letter(col_idx)].width = max_length + 2

        # Color cells based on different Batch No
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

    return output

# ------------------------ MAIN LOGIC ------------------------

def main():
    try:
        # Load the data
        picking_pool, sku_master = load_data(picking_pool_file, sku_master_file)

        # Filter the data
        picking_pool = filter_picking_pool(picking_pool)

        # Get GI type filter from the user
        gi_type = st.sidebar.radio("Filter by GI Type", ("All", "Single-line", "Multi-line"))

        # Get date range for filtering
        min_date, max_date = picking_pool['DeliveryDate'].min(), picking_pool['DeliveryDate'].max()
        delivery_range = st.sidebar.date_input("🗕️ Filter by Delivery Date", (min_date, max_date), min_value=min_date, max_value=max_date)

        # Apply delivery date filter
        picking_pool = apply_delivery_date_filter(picking_pool, delivery_range)

        # Merge and clean data
        df = merge_and_clean(picking_pool, sku_master)

        # Classify and assign bins/layers
        df = classify_and_assign(df)

        # Assign job numbers with advanced logic
        df = assign_job_numbers_with_scenarios(df)

        # Finalize output based on GI type
        output_df = finalize_output(df, gi_type)

        st.success("✅ Processing complete!")
        st.dataframe(output_df.head(20))

        # Export to Excel
        output = export_to_excel(output_df)

        # Get the current timestamp
        now = datetime.now(ZoneInfo("Asia/Singapore"))
        timestamp = now.strftime("%d %b - %H%M")
        filename = f"master_pick_ticket_{timestamp}.xlsx"

        # Provide download button for Excel file
        st.download_button(
            label="Download Master Pick Ticket",
            data=output,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.session_state["final_df"] = output_df

    except Exception as e:
        st.error(f"❌ Error during processing: {e}")

# ------------------------ EXECUTE ------------------------
if picking_pool_file and sku_master_file:
    main()
else:
    st.info("👈 Please upload both Picking Pool and SKU Master Excel files to begin.")
