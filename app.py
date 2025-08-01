import streamlit as st
import pandas as pd
from io import BytesIO
import openai

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

def classify_gi(row):
    return 'Bin' if row['Total GI Vol'] < 600000 else 'Layer'

# ------------------------ DATA PROCESSING ------------------------
if picking_pool_file and sku_master_file:
    try:
        picking_pool = pd.read_excel(picking_pool_file)
        sku_master = pd.read_excel(sku_master_file)

        # Filter valid delivery dates
        picking_pool['DeliveryDate'] = pd.to_datetime(picking_pool['DeliveryDate'], errors='coerce')
        picking_pool = picking_pool[picking_pool['DeliveryDate'].notna()]

        # 🆕 Filter for Zone "A" and Location starting with "A-" or "SOFT-"
        picking_pool = picking_pool[
            (picking_pool['Zone'] == 'A') &
            (picking_pool['Location'].astype(str).str.startswith('A-') | picking_pool['Location'].astype(str).str.startswith('SOFT-'))
        ]

        
        # Sidebar date input
        min_date, max_date = picking_pool['DeliveryDate'].min(), picking_pool['DeliveryDate'].max()
        delivery_range = st.sidebar.date_input("📅 Filter by Delivery Date", (min_date, max_date), min_value=min_date, max_value=max_date)

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

        # Carton Info + GI Class
        final_df = pd.concat([final_df, final_df.apply(calculate_carton_info, axis=1)], axis=1)
        final_df['GI Class'] = final_df.apply(classify_gi, axis=1)
        # 🆕 Add running index per GI
        final_df['GI Index'] = final_df.groupby('IssueNo').cumcount() + 1
        # 🆕 Merge GI Class and Index into "Type" column (e.g., "Bin 1", "Layer 2")
        final_df['Type'] = final_df['GI Class'] + ' ' + final_df['GI Index'].astype(str)


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
            'Commercial Box Count',
            'DeliveryDate',
            'ShipToName',
            'Type',             # 🆕 Merged column: GI Class + GI Index
            'JobNo',            
            'CartonDescription'       
        ]].drop_duplicates()



        st.success("✅ Processing complete!")
        st.dataframe(output_df.head(20))

        # Download
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            output_df.to_excel(writer, index=False, sheet_name='Master Pick Ticket')
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

# ------------------------ AI ASSISTANT ------------------------
st.sidebar.title("🤖 AI Assistant")
if st.sidebar.checkbox("Open Chat Assistant"):

    st.subheader("🤖 Ask me about the pick ticket data!")

    if "final_df" in st.session_state:
        final_df = st.session_state["final_df"]
        chat_history = st.session_state.get("chat_history", [])

        for msg in chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        prompt = st.chat_input("Ask a question about the pick ticket data...")
        if prompt:
            with st.chat_message("user"):
                st.markdown(prompt)

            df_info = final_df.describe(include='all').to_string()
            full_prompt = f"""
You are a data assistant. Answer questions about the pick ticket data below:

{df_info}

User question: {prompt}
"""

            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You're a helpful assistant that answers questions about logistics and order picking data."},
                        {"role": "user", "content": full_prompt}
                    ]
                )
                answer = response['choices'][0]['message']['content']
            except Exception as e:
                answer = f"❌ Failed to call OpenAI API: {e}"

            with st.chat_message("assistant"):
                st.markdown(answer)

            chat_history.extend([
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": answer}
            ])
            st.session_state["chat_history"] = chat_history
    else:
        st.warning("Please upload and process data first.")
