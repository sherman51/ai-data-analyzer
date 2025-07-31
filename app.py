import streamlit as st
import pandas as pd

# Assuming final_df is your DataFrame loaded from a file (e.g., CSV, Excel, etc.)
final_df = pd.read_csv('your_data.csv')  # Replace with your actual file path

# Streamlit widgets (slicers) for user input
# Filter by SKU
sku_options = final_df['SKU'].unique()  # All unique SKUs in the DataFrame
selected_sku = st.selectbox("Select SKU", sku_options)

# Filter by Delivery Date
# Assuming DeliveryDate is in datetime format, if not, you may need to convert it first
final_df['DeliveryDate'] = pd.to_datetime(final_df['DeliveryDate'])  # Ensure date format
date_options = final_df['DeliveryDate'].unique()  # All unique Delivery Dates
selected_date = st.date_input("Select Delivery Date", min_value=min(date_options), max_value=max(date_options), value=min(date_options))

# Filter the DataFrame based on user input (SKU and DeliveryDate)
filtered_df = final_df[
    (final_df['SKU'] == selected_sku) & 
    (final_df['DeliveryDate'] == pd.to_datetime(selected_date))  # Ensure the date matches exactly
]

# Display filtered Data
st.write("Filtered Data:", filtered_df)

# Now, process the filtered data further
# Select relevant columns and remove duplicates
final_df_processed = filtered_df[[
    'IssueNo', 'DeliveryDate', 'SKU', 'ShipToName', 'PickingQty', 
    'CartonDescription', 'GI Class', 'JobNo', 'Batch No', 
    'Commercial Box Count', 'Location'
]].drop_duplicates()

# Display the processed data (without duplicates)
st.write("Processed Data (without duplicates):", final_df_processed)

# Optionally, you can perform further operations on `final_df_processed`
# Example: Create some charts, export the data, or save the output.
