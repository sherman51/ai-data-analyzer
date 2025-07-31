import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Master Pick Ticket Generator", layout="wide")
st.title("📦 Master Pick Ticket Generator – Pick by Cart")

# Upload Section
st.sidebar.header("📂 Upload Input Files")
picking_pool_file = st.sidebar.file_uploader("Upload Picking Pool Excel file", type=["xlsx"])
sku_master_file = st.sidebar.file_uploader("Upload SKU Master Excel file", type=["xlsx"])

def get_loose_box_size(loose_vol):
    # Explicitly cast loose_vol to float to avoid comparison issues
    loose_vol = float(loose_vol)
    if loose_vol <= 1200:
        return "1XS"
    elif loose_vol <= 6000:
        return "1S"
    elif loose_vol <= 12000:
        return "1Rectangle"
    elif loose_vol <= 48000:
        return "1L"
    else:
        return "1L"  # Cap at L

def calculate_carton_info(row):
    try:
        pq = float(row.get('PickingQty', 0) or 0)
        qpc = float(row.get('Qty per Carton', 0) or 0)
        iv = float(row.get('Item Vol', 0) or 0)
    except Exception as e:
        # If any conversion fails
        return pd.Series({'CartonCount': None, 'CartonDescription': 'Invalid'})

    # Validate inputs
    if pq == 0 or qpc == 0 or iv == 0:
        return pd.Series({'CartonCount': None, 'CartonDescription': 'Invalid'})

    cartons = int(pq // qpc)
    loose = int(pq % qpc)

    if loose > 0:
        looseVol = loose * iv
        # Debug print for loose volume calculation
        print(f"DEBUG: PickingQty={pq}, Qty per Carton={qpc}, Item Vol={iv}, Loose={loose}, LooseVol={looseVol}")

        looseBox = get_loose_box_size(looseVol)

        if cartons > 0:
            desc = f"{cartons} Commercial Carton + {looseBox}"
        else:
            desc = looseBox
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

    # Step 3: Fill NA and fix zeros
    df['PickingQty'] = pd.to_numeric(df['PickingQty'], errors='coerce').fillna(0)
    df['Item Vol'] = pd.to_numeric(df['Item Vol'], errors='coerce').fillna(0)
    df['Qty Commercial Box'] = pd.to_numeric(df['Qty Commercial Box'], errors='coerce').replace(0, 1).fillna(1)
    df['Qty per Carton'] = pd.to_numeric(df['Qty per Carton'], errors='coerce').replace(0, 1).fillna(1)

    # Step 4: Calculate Total Item Vol
    df['Total Item Vol'] = (df['PickingQty'] / df['Qty Commercial Box']) * df['Item Vol']

    # Step 5: Calculate Total GI Vol per IssueNo
    gi_volume = df.groupby('IssueNo')['Total Item Vol'].sum().reset_index().rename(columns={'Total Item Vol': 'Total GI Vol'})
    df = df.merge(gi_volume, on='IssueNo', how='left')

    # Step 6: Count lines per GI
    line_counts = df.groupby('IssueNo').size().reset_index(name='Line Count')
    df = df.merge(line_counts, on='IssueNo', how='left')

    # Step 7: Split Single-line and Multi-line
    single_line = df[df['Line Count'] == 1].copy()
    multi_line = df[df['Line Count'] > 1].copy()

    # Step 8A: Assign Jobs to Single-line (grouped by ShipToName, 5 GIs per job)
    single_jobs = []
    job_counter = 1
    for name, group in single_line.groupby('ShipToName'):
        group = group.sort_values('IssueNo').copy()
        group['GI_Group_Index'] = group.groupby('IssueNo').ngroup()
        group['JobNo'] = group['GI_Group_Index'].apply(lambda x: f"Job{str(job_counter + x // 5).zfill(3)}")
        job_counter += (group['GI_Group_Index'].nunique() + 4) // 5
        single_jobs.append(group)
    single_line_final = pd.concat(single_jobs)

    # Step 8B: Assign Jobs to Multi-line (grouped by GI volume ≤ 600000)
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

    # Assign remaining GIs in current_job
    for gi in current_job:
        multi_line.loc[multi_line['IssueNo'] == gi, 'JobNo'] = f"Job{str(job_id).zfill(3)}"

    # Step 9: Combine both groups
    final_df = pd.concat([single_line_final, multi_line], ignore_index=True)

    # Step 10: Add Carton Info columns
    carton_info = final_df.apply(calculate_carton_info, axis=1)
    final_df = pd.concat([final_df, carton_info], axis=1)

    # Step 11: Add GI Class column (Bin, Layer, Carton)
    def classify_gi(row):
        vol = row['Total GI Vol']
        if vol < 35000:
            return 'Bin'
        elif vol < 248500:
            return 'Layer'
        else:
            return 'Carton'

    final_df['GI Class'] = final_df.apply(classify_gi, axis=1)

    # Step 12: Optional cleanup and reordering columns
    final_df = final_df[[
        'IssueNo', 'SKU', 'ShipToName', 'PickingQty', 'Item Vol',
        'Qty Commercial Box', 'Qty per Carton', 'Total Item Vol', 'Total GI Vol',
        'CartonCount', 'CartonDescription', 'GI Class', 'JobNo'
    ]].drop_duplicates()

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
