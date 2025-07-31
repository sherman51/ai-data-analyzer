import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Master Pick Ticket Generator", layout="wide")
st.title("📦 Master Pick Ticket Generator – Pick by Cart")

# Upload Section
st.sidebar.header("📂 Upload Input Files")
picking_pool_file = st.sidebar.file_uploader("Upload Picking Pool Excel file", type=["xlsx"])
sku_master_file = st.sidebar.file_uploader("Upload SKU Master Excel file", type=["xlsx"])

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

        desc = f"{cartons} Commercial Carton + {looseBox}" if cartons > 0 else looseBox
        totalC = cartons + 1
    else:
        desc = f"{cartons} Commercial Carton"
        totalC = cartons

    return pd.Series({'CartonCount': totalC, 'CartonDescription': desc})

if picking_pool_file and sku_master_file:
    # Step 1: Load files
    picking_pool = pd.read_excel(picking_pool_file)
    sku_master = pd.read_excel(sku_master_file)

    # Exclude GIs with missing critical SKU info
    merged_check = picking_pool.merge(sku_master, how='left', left_on='SKU', right_on='SKU Code')
    missing_info = merged_check[
        merged_check['Qty Commercial Box'].isna() |
        merged_check['Qty per Carton'].isna() |
        merged_check['Item Vol'].isna()
    ]['IssueNo'].unique()

    picking_pool_filtered = picking_pool[~picking_pool['IssueNo'].isin(missing_info)]

    # Step 2: Merge again with filtered picking pool
    df = picking_pool_filtered.merge(sku_master, how='left', left_on='SKU', right_on='SKU Code')

    # Step 3: Calculate Total Item Vol
    df['PickingQty'] = df['PickingQty'].fillna(0)
    df['Item Vol'] = df['Item Vol'].fillna(0)
    df['Qty Commercial Box'] = df['Qty Commercial Box'].replace(0, 1).fillna(1)
    df['Qty per Carton'] = df['Qty per Carton'].replace(0, 1).fillna(1)

    df['Total Item Vol'] = (df['PickingQty'] / df['Qty Commercial Box']) * df['Item Vol']

    # Step 4: Calculate Total GI Vol per IssueNo
    gi_volume = df.groupby('IssueNo')['Total Item Vol'].sum().reset_index()
    gi_volume = gi_volume.rename(columns={'Total Item Vol': 'Total GI Vol'})
    df = df.merge(gi_volume, on='IssueNo', how='left')

    # Step 5: Count lines per GI
    line_counts = df.groupby('IssueNo').size().reset_index(name='Line Count')
    df = df.merge(line_counts, on='IssueNo', how='left')

    # Step 6: Split into Single-line and Multi-line
    single_line = df[df['Line Count'] == 1].copy()
    multi_line = df[df['Line Count'] > 1].copy()

    # Step 7A: Assign Jobs to Single-line (grouped by ShipToName, 5 GIs per job)
    single_jobs = []
    job_counter = 1

    for name, group in single_line.groupby('ShipToName'):
        group = group.copy()
        group = group.sort_values('IssueNo')
        group['GI_Group_Index'] = group.groupby('IssueNo').ngroup()
        group['JobNo'] = group['GI_Group_Index'].apply(lambda x: f"Job{str(job_counter + x // 5).zfill(3)}")
        job_counter += (group['GI_Group_Index'].nunique() + 4) // 5
        single_jobs.append(group)

    single_line_final = pd.concat(single_jobs)

    # Step 7B: Assign Jobs to Multi-line (grouped by GI volume ≤ 600000)
    multi_summary = multi_line[['IssueNo', 'Total GI Vol']].drop_duplicates().sort_values('Total GI Vol')
    multi_line['JobNo'] = None
    current_job = []
    current_vol = 0
    job_id = job_counter

    for _, row in multi_summary.iterrows():
        issue_no = row['IssueNo']
        vol = row['Total GI Vol']
        if current_vol + vol > 600000:
            for gi in current_job:
                multi_line.loc[multi_line['IssueNo'] == gi, 'JobNo'] = f"Job{str(job_id).zfill(3)}"
            job_id += 1
            current_job = []
            current_vol = 0

        current_job.append(issue_no)
        current_vol += vol

    # Assign remaining
    for gi in current_job:
        multi_line.loc[multi_line['IssueNo'] == gi, 'JobNo'] = f"Job{str(job_id).zfill(3)}"

    # Combine both groups
    final_df = pd.concat([single_line_final, multi_line], ignore_index=True)

    # Step 8: Add Carton Info columns
    carton_info = final_df.apply(calculate_carton_info, axis=1)
    final_df = pd.concat([final_df, carton_info], axis=1)

    # Step 9: Add GI Class column (Bin, Layer, Carton)
    def classify_gi(row):
        vol = row['Total GI Vol']
        if vol < 35000:
            return 'Bin'
        elif vol < 248500:
            return 'Layer'
        else:
            return 'Carton'

    final_df['GI Class'] = final_df.apply(classify_gi, axis=1)

    # Step 10: Add Batch No column from Storage Location, and Commercial Box Count column
    final_df['Batch No'] = final_df['Storage Location']
    final_df['Commercial Box Count'] = final_df['PickingQty'] / final_df['Qty Commercial Box']

    # Step 11: Drop unwanted columns
    final_df = final_df.drop(columns=[
        'Item Vol',
        'Qty Commercial Box',
        'Qty per Carton',
        'Total Item Vol',
        'CartonCount',
        'CartonDescription',
        'Total GI Vol'
    ])

    # Optional cleanup and reorder columns
    cols_order = [
        'IssueNo', 'SKU', 'ShipToName', 'PickingQty', 'Batch No',
        'Commercial Box Count', 'GI Class', 'JobNo'
    ]

    # Keep only existing columns to avoid errors if any missing
    cols_order = [col for col in cols_order if col in final_df.columns]

    final_df = final_df[cols_order].drop_duplicates()

    st.success("✅ Processing complete!")

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
