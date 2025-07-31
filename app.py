import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Master Pick Ticket Generator", layout="wide")
st.title("📦 Master Pick Ticket Generator – Pick by Cart")

# Upload Section
st.sidebar.header("📂 Upload Input Files")
picking_pool_file = st.sidebar.file_uploader("Upload Picking Pool Excel file", type=["xlsx"])
sku_master_file = st.sidebar.file_uploader("Upload SKU Master Excel file", type=["xlsx"])

# Function to calculate carton info
def calculate_carton_info(row):
    pq = row.get('PickingQty', 0) or 0
    qpc = row.get('Qty per Carton', 0) or 0
    iv = row.get('Item Vol', 0) or 0

    if pq == 0 or qpc == 0 or iv == 0:
        return pd.Series({'CartonCount': None, 'CartonDescription': 'Invalid'})

    cartons = pq // qpc
    loose = pq % qpc

    if loose > 0:
        looseVol = loose * iv
        if looseVol <= 1200:
            looseBox = "1XS"
        elif looseVol <= 6000:
            looseBox = "1S"
        elif looseVol <= 12000:
            looseBox = "1Rectangle"
        elif looseVol <= 48000:
            looseBox = "1L"
        else:
            looseBox = "1L"

        desc = f"{cartons}.0 Commercial Carton + {looseBox}" if cartons > 0 else looseBox
        totalC = cartons + 1
    else:
        desc = f"{cartons}.0 Commercial Carton"
        totalC = cartons

    return pd.Series({'CartonCount': totalC, 'CartonDescription': desc})

# Function to classify GI type
def classify_gi(row):
    vol = row['Total GI Vol']
    if vol < 35000:
        return 'Bin'
    elif vol < 248500:
        return 'Layer'
    else:
        return 'Carton'

if picking_pool_file and sku_master_file:
    # Load files
    picking_pool = pd.read_excel(picking_pool_file)
    sku_master = pd.read_excel(sku_master_file)

    # Initial merge for validation
    merged_check = picking_pool.merge(sku_master, how='left', left_on='SKU', right_on='SKU Code')
    missing_info = merged_check[
        merged_check['Qty Commercial Box'].isna() |
        merged_check['Qty per Carton'].isna() |
        merged_check['Item Vol'].isna()
    ]['IssueNo'].unique()

    excluded_gis_df = picking_pool[picking_pool['IssueNo'].isin(missing_info)]

    # Keep necessary columns in filtered picking pool
    picking_pool_filtered = picking_pool[~picking_pool['IssueNo'].isin(missing_info)]

    # Merge and retain important fields
    df = picking_pool_filtered.merge(sku_master, how='left', left_on='SKU', right_on='SKU Code')

    # Step 3: Calculate Total Item Vol
    df['PickingQty'] = df['PickingQty'].fillna(0)
    df['Item Vol'] = df['Item Vol'].fillna(0)
    df['Qty Commercial Box'] = df['Qty Commercial Box'].replace(0, 1).fillna(1)
    df['Qty per Carton'] = df['Qty per Carton'].replace(0, 1).fillna(1)

    df['Total Item Vol'] = (df['PickingQty'] / df['Qty Commercial Box']) * df['Item Vol']

    # Step 4: Calculate GI Vol
    gi_volume = df.groupby('IssueNo')['Total Item Vol'].sum().reset_index()
    gi_volume = gi_volume.rename(columns={'Total Item Vol': 'Total GI Vol'})
    df = df.merge(gi_volume, on='IssueNo', how='left')

    # Step 5: Count lines
    line_counts = df.groupby('IssueNo').size().reset_index(name='Line Count')
    df = df.merge(line_counts, on='IssueNo', how='left')

    # Split into single/multi
    single_line = df[df['Line Count'] == 1].copy()
    multi_line = df[df['Line Count'] > 1].copy()

    # Step 7A: Assign Jobs - Single-line
    single_jobs = []
    job_counter = 1
    for name, group in single_line.groupby('ShipToName'):
        group = group.copy().sort_values('IssueNo')
        group['GI_Group_Index'] = group.groupby('IssueNo').ngroup()
        group['JobNo'] = group['GI_Group_Index'].apply(lambda x: f"Job{str(job_counter + x // 5).zfill(3)}")
        job_counter += (group['GI_Group_Index'].nunique() + 4) // 5
        single_jobs.append(group)
    single_line_final = pd.concat(single_jobs)

    # Step 7B: Assign Jobs - Multi-line
    multi_summary = multi_line[['IssueNo', 'Total GI Vol']].drop_duplicates().sort_values('Total GI Vol')
    multi_line['JobNo'] = None
    current_job, current_vol = [], 0
    job_id = job_counter

    for _, row in multi_summary.iterrows():
        issue_no, vol = row['IssueNo'], row['Total GI Vol']
        if current_vol + vol > 600000:
            for gi in current_job:
                multi_line.loc[multi_line['IssueNo'] == gi, 'JobNo'] = f"Job{str(job_id).zfill(3)}"
            job_id += 1
            current_job, current_vol = [], 0
        current_job.append(issue_no)
        current_vol += vol

    for gi in current_job:
        multi_line.loc[multi_line['IssueNo'] == gi, 'JobNo'] = f"Job{str(job_id).zfill(3)}"

    # Combine single and multi
    final_df = pd.concat([single_line_final, multi_line], ignore_index=True)

    # Step 8: Add carton info
    carton_info = final_df.apply(calculate_carton_info, axis=1)
    final_df = pd.concat([final_df, carton_info], axis=1)

    # Step 9: Classify GI
    final_df['GI Class'] = final_df.apply(classify_gi, axis=1)

    # Step 10: Batch No from Storage Location
    final_df['Batch No'] = final_df['Storage Location']

    # Step 11: Calculate number of Commercial Boxes
    final_df['Commercial Box Count'] = final_df['PickingQty'] / final_df['Qty Commercial Box']

    # Final display columns
    cols_order = [
        'IssueNo', 'DeliveryDate', 'SKU', 'ShipToName', 'PickingQty', 'Batch No',
        'Commercial Box Count', 'CartonDescription', 'GI Class', 'JobNo'
    ]

    final_df_display = final_df[cols_order].drop_duplicates()

    st.success("✅ Processing complete!")
    st.dataframe(final_df_display.head(30))

    # Download processed file
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        final_df_display.to_excel(writer, index=False, sheet_name='Master Pick Ticket')
        if not excluded_gis_df.empty:
            excluded_gis_df.to_excel(writer, index=False, sheet_name='Excluded GIs')
    output.seek(0)

    st.download_button(
        label="⬇️ Download Master Pick Ticket Excel",
        data=output,
        file_name="MasterPickTicket.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Display excluded GIs
    if not excluded_gis_df.empty:
        st.subheader("🚫 Excluded GIs due to missing SKU data")
        st.dataframe(excluded_gis_df[['IssueNo', 'SKU', 'ShipToName']].drop_duplicates())

else:
    st.info("👈 Please upload both Picking Pool and SKU Master Excel files to begin.")
