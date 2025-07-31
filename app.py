import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Master Pick Ticket Generator", layout="wide")
st.title("📦 Master Pick Ticket Generator – Pick by Cart")

# Upload Section
st.sidebar.header("📂 Upload Input Files")
picking_pool_file = st.sidebar.file_uploader("Upload Picking Pool Excel file", type=["xlsx"])
sku_master_file = st.sidebar.file_uploader("Upload SKU Master Excel file", type=["xlsx"])

# User input for filtering GI type (Single-line or Multi-line)
gi_type = st.sidebar.radio("Filter by GI Type", ("All", "Single-line", "Multi-line"))

# Date slicer to filter data by delivery date range
st.sidebar.header("🗓️ Select Delivery Date Range")
date_range = st.sidebar.date_input("Select Date Range", [], min_value=None, max_value=None)

def calculate_carton_info(row):
    pq = row.get('PickingQty', 0) or 0
    qpc = row.get('Qty per Carton', 0) or 0
    iv = row.get('Item Vol', 0) or 0

    # Validate inputs
    if pq == 0 or qpc == 0 or iv == 0:
        return pd.Series({'CartonCount': None, 'CartonDescription': 'Invalid'})

    cartons = pq // qpc
    loose = pq % qpc

    if loose > 0:
        looseVol = loose * iv
        # Only 4 carton sizes for loose: XS, S, Rectangle, L
        if looseVol <= 1200:
            looseBox = "1XS"
        elif looseVol <= 6000:
            looseBox = "1S"
        elif looseVol <= 12000:
            looseBox = "1Rectangle"
        elif looseVol <= 48000:
            looseBox = "1L"
        else:
            looseBox = "1L"  # Cap at L

        desc = f"{cartons} Commercial Carton + {looseBox}" if cartons > 0 else looseBox
        totalC = cartons + 1
    else:
        # No loose cartons, just full commercial cartons
        desc = f"{cartons} Commercial Carton"
        totalC = cartons

    return pd.Series({'CartonCount': totalC, 'CartonDescription': desc})

if picking_pool_file and sku_master_file:
    # Step 1: Load files
    picking_pool = pd.read_excel(picking_pool_file)
    sku_master = pd.read_excel(sku_master_file)

    # Ensure DeliveryDate is in datetime format
    picking_pool['DeliveryDate'] = pd.to_datetime(picking_pool['DeliveryDate'], errors='coerce')

    # Step 2: Apply the Date Range Filter
    if date_range:
        start_date, end_date = date_range
        picking_pool = picking_pool[(picking_pool['DeliveryDate'] >= pd.to_datetime(start_date)) &
                                    (picking_pool['DeliveryDate'] <= pd.to_datetime(end_date))]

    # Step 3: Exclude GIs with missing critical SKU info
    merged_check = picking_pool.merge(sku_master, how='left', left_on='SKU', right_on='SKU Code')
    missing_info = merged_check[
        merged_check['Qty Commercial Box'].isna() |
        merged_check['Qty per Carton'].isna() |
        merged_check['Item Vol'].isna()
    ]['IssueNo'].unique()

    picking_pool_filtered = picking_pool[~picking_pool['IssueNo'].isin(missing_info)]

    # Step 4: Merge filtered picking pool and sku_master (keep Storage Location)
    df = picking_pool_filtered.merge(sku_master, how='left', left_on='SKU', right_on='SKU Code')

    # Step 5: Calculate Total Item Vol
    df['PickingQty'] = df['PickingQty'].fillna(0)
    df['Item Vol'] = df['Item Vol'].fillna(0)
    df['Qty Commercial Box'] = df['Qty Commercial Box'].replace(0, 1).fillna(1)
    df['Qty per Carton'] = df['Qty per Carton'].replace(0, 1).fillna(1)

    df['Total Item Vol'] = (df['PickingQty'] / df['Qty Commercial Box']) * df['Item Vol']

    # Step 6: Calculate Total GI Vol per IssueNo
    gi_volume = df.groupby('IssueNo')['Total Item Vol'].sum().reset_index()
    gi_volume = gi_volume.rename(columns={'Total Item Vol': 'Total GI Vol'})
    df = df.merge(gi_volume, on='IssueNo', how='left')

    # Step 7: Count lines per GI
    line_counts = df.groupby('IssueNo').size().reset_index(name='Line Count')
    df = df.merge(line_counts, on='IssueNo', how='left')

    # Step 8: Filter Single-line and Multi-line
    if gi_type == "Single-line":
        final_df = df[df['Line Count'] == 1]
    elif gi_type == "Multi-line":
        final_df = df[df['Line Count'] > 1]
    else:
        final_df = df.copy()  # Include all GIs for "All" option

    # Step 9: Add Carton Info columns
    carton_info = final_df.apply(calculate_carton_info, axis=1)
    final_df = pd.concat([final_df, carton_info], axis=1)

    # Step 10: Add GI Class column (Bin or Layer)
    def classify_gi(row):
        vol = row['Total GI Vol']
        if vol < 600000:  # Cap volume at 600,000 for a "Bin" classification
            return 'Bin'
        else:
            return 'Layer'  # If the volume exceeds the threshold, classify as 'Layer'

    final_df['GI Class'] = final_df.apply(classify_gi, axis=1)

    # Step 11: Add Batch No (from Storage Location)
    if 'StorageLocation' in final_df.columns:
        final_df['Batch No'] = final_df['StorageLocation']
    else:
        final_df['Batch No'] = None

    # Step 12: Calculate Commercial Box Count = PickingQty / Qty Commercial Box
    final_df['Commercial Box Count'] = final_df['PickingQty'] / final_df['Qty Commercial Box']

    # Optional cleanup and reordering columns
    final_df = final_df[[ 
        'IssueNo', 'DeliveryDate', 'SKU', 'ShipToName', 'Location_x', 'PickingQty',
        'Total GI Vol', 'CartonDescription', 'GI Class', 'JobNo', 'Batch No', 'Commercial Box Count'
    ]].drop_duplicates()

    # Success message
    st.success("✅ Processing complete!")

    # Show the filtered data (first 20 rows for preview)
    st.dataframe(final_df.head(20))

    # Download button
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        final_df.to_excel(writer, index=False, sheet_name='Master Pick Ticket')
    output.seek(0)

    st.download_button(
        label="⬇️ Download Master Pick Ticket Excel",
        data=output,
        file_name="MasterPickTicket.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("👈 Please upload both Picking Pool and SKU Master Excel files to begin.")
