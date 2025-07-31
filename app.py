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

    # Convert DeliveryDate to datetime and drop rows with invalid dates
    picking_pool['DeliveryDate'] = pd.to_datetime(picking_pool['DeliveryDate'], errors='coerce')
    picking_pool = picking_pool[picking_pool['DeliveryDate'].notna()]

    # Sidebar date filter
    min_date = picking_pool['DeliveryDate'].min()
    max_date = picking_pool['DeliveryDate'].max()

    delivery_date_range = st.sidebar.date_input(
        "📅 Filter by Delivery Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    # Apply delivery date filter
    if isinstance(delivery_date_range, tuple) and len(delivery_date_range) == 2:
        start_date, end_date = pd.to_datetime(delivery_date_range[0]), pd.to_datetime(delivery_date_range[1])
        picking_pool = picking_pool[
            (picking_pool['DeliveryDate'] >= start_date) &
            (picking_pool['DeliveryDate'] <= end_date)
        ]

    # Exclude GIs with missing critical SKU info
    merged_check = picking_pool.merge(sku_master, how='left', left_on='SKU', right_on='SKU Code')
    missing_info = merged_check[
        merged_check['Qty Commercial Box'].isna() |
        merged_check['Qty per Carton'].isna() |
        merged_check['Item Vol'].isna()
    ]['IssueNo'].unique()

    picking_pool_filtered = picking_pool[~picking_pool['IssueNo'].isin(missing_info)]

    # Step 2: Merge filtered picking pool and sku_master (keep Storage Location)
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

    for gi in current_job:
        multi_line.loc[multi_line['IssueNo'] == gi, 'JobNo'] = f"Job{str(job_id).zfill(3)}"

    # Combine both groups
    final_df = pd.concat([single_line_final, multi_line], ignore_index=True)

    # Filter by GI Type
    if 'Line Count' in final_df.columns:
        if gi_type == "Single-line":
            final_df = final_df[final_df['Line Count'] == 1]
        elif gi_type == "Multi-line":
            final_df = final_df[final_df['Line Count'] > 1]
    else:
        st.error("Column 'Line Count' not found. Please check the data processing steps.")

    # Step 8: Add Carton Info columns
    carton_info = final_df.apply(calculate_carton_info, axis=1)
    final_df = pd.concat([final_df, carton_info], axis=1)

    # Step 9: Add GI Class column (Bin or Layer)
    def classify_gi(row):
        vol = row['Total GI Vol']
        return 'Bin' if vol < 600000 else 'Layer'

    final_df['GI Class'] = final_df.apply(classify_gi, axis=1)

    # Step 10: Add Batch No (from Storage Location)
    final_df['Batch No'] = final_df['StorageLocation'] if 'StorageLocation' in final_df.columns else None

    # Step 11: Calculate Commercial Box Count = PickingQty / Qty Commercial Box
    final_df['Commercial Box Count'] = final_df['PickingQty'] / final_df['Qty Commercial Box']

    # Step 12: Final cleanup
    final_df = final_df[[ 
        'IssueNo', 'DeliveryDate', 'SKU', 'ShipToName', 'Location_x', 'PickingQty',
        'CartonDescription', 'GI Class', 'JobNo', 'Batch No', 'Commercial Box Count'
    ]].drop_duplicates()

    # Display result
    st.success("✅ Processing complete!")
    st.dataframe(final_df.head(20))

    # Download section
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
    
import openai
import streamlit as st
import os

import openai
import streamlit as st

# Retrieve OpenAI API key from Streamlit secrets (this is secure)
openai.api_key = st.secrets["OPENAI_API_KEY"]

# Your other Streamlit and OpenAI code here
st.markdown("## 🤖 AI Assistant")
st.info("You can ask questions like:\n- How many SKUs are in the data?\n- What’s the total PickingQty?\n- What’s the average item volume?\n- Suggest optimization for multi-line GIs")

user_query = st.text_area("Ask a question about your GI data (natural language)", height=100)

# Optionally convert top 100 rows to CSV for context (avoid flooding prompt)
if 'final_df' in locals():
    data_sample = final_df.head(100).to_csv(index=False)
else:
    data_sample = "No data available."

if st.button("Ask AI") and user_query:
    with st.spinner("Thinking..."):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You're a data analyst assistant. The user will ask questions about a DataFrame "
                            "used to generate warehouse pick tickets based on GI data. Here's the top part of the data:\n\n"
                            f"{data_sample}"
                        )
                    },
                    {"role": "user", "content": user_query}
                ]
            )
            ai_reply = response['choices'][0]['message']['content']
            st.success("AI Response:")
            st.markdown(ai_reply)
        except Exception as e:
            st.error(f"AI Error: {e}")
