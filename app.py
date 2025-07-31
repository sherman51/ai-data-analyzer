import streamlit as st
import pandas as pd
from io import BytesIO

# Streamlit Setup
st.set_page_config(page_title="Master Pick Ticket Generator", layout="wide")
st.title("📦 Master Pick Ticket Generator – Pick by Cart")

# Upload Section
st.sidebar.header("📂 Upload Input Files")
picking_pool_file = st.sidebar.file_uploader("Upload Picking Pool Excel file", type=["xlsx"])
sku_master_file = st.sidebar.file_uploader("Upload SKU Master Excel file", type=["xlsx"])

# User input for filtering GI type (Single-line or Multi-line)
gi_type = st.sidebar.radio("Filter by GI Type", ("All", "Single-line", "Multi-line"))

# Function to calculate Carton Info
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

# Define Chatbot function
def chatbot(query, final_df):
    # Example responses
    if 'reprocess' in query.lower():
        return "Sure! You can filter the data by Delivery Date, GI Type, or other options. What would you like to adjust?"
    
    if 'total carton count' in query.lower():
        total_cartons = final_df['CartonCount'].sum()
        return f"The total carton count is {total_cartons}."

    if 'gi count' in query.lower():
        gi_count = final_df['IssueNo'].nunique()
        return f"There are {gi_count} unique GI numbers in the dataset."

    return "I'm sorry, I didn't understand that. Please ask about reprocessing or a specific query on the data."

# If both files are uploaded
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

    # Filter rows missing critical SKU information
    merged_check = picking_pool.merge(sku_master, how='left', left_on='SKU', right_on='SKU Code')
    missing_info = merged_check[
        merged_check['Qty Commercial Box'].isna() |
        merged_check['Qty per Carton'].isna() |
        merged_check['Item Vol'].isna()
    ]['IssueNo'].unique()

    picking_pool_filtered = picking_pool[~picking_pool['IssueNo'].isin(missing_info)]

    # Step 2: Merge picking pool and SKU master
    df = picking_pool_filtered.merge(sku_master, how='left', left_on='SKU', right_on='SKU Code')

    # Step 3: Calculate Total Item Vol
    df['PickingQty'] = df['PickingQty'].fillna(0)
    df['Item Vol'] = df['Item Vol'].fillna(0)
    df['Qty Commercial Box'] = df['Qty Commercial Box'].replace(0, 1).fillna(1)
    df['Qty per Carton'] = df['Qty per Carton'].replace(0, 1).fillna(1)

    df['Total Item Vol'] = (df['PickingQty'] / df['Qty Commercial Box']) * df['Item Vol']

    # Process the data as in your current script...

    # Step 8: Add Carton Info columns
    carton_info = df.apply(calculate_carton_info, axis=1)
    final_df = pd.concat([df, carton_info], axis=1)

    # Filter by GI Type
    if gi_type == "Single-line":
        final_df = final_df[final_df['Line Count'] == 1]
    elif gi_type == "Multi-line":
        final_df = final_df[final_df['Line Count'] > 1]

    # Step 9: Add GI Class column (Bin or Layer)
    final_df['GI Class'] = final_df.apply(lambda row: 'Bin' if row['Total GI Vol'] < 600000 else 'Layer', axis=1)

    # Step 10: Add Batch No (from Storage Location)
    final_df['Batch No'] = final_df['StorageLocation'] if 'StorageLocation' in final_df.columns else None

    # Step 11: Calculate Commercial Box Count = PickingQty / Qty Commercial Box
    final_df['Commercial Box Count'] = final_df['PickingQty'] / final_df['Qty Commercial Box']

    # Step 12: Final cleanup
    final_df = final_df[['IssueNo', 'DeliveryDate', 'SKU', 'ShipToName', 'Location_x', 'PickingQty',
                         'CartonDescription', 'GI Class', 'JobNo', 'Batch No', 'Commercial Box Count']].drop_duplicates()

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

    # Chatbot Section - Ensure it's outside of download interaction
    st.subheader("💬 Chatbot Interaction")
    user_query = st.text_input("Ask a question or request reprocessing:")

    if user_query:
        response = chatbot(user_query, final_df)
        st.write(f"🤖 Chatbot: {response}")

else:
    st.info("👈 Please upload both Picking Pool and SKU Master Excel files to begin.")
