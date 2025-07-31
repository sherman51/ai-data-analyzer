import streamlit as st
import pandas as pd

st.title("Master Pick Ticket Generator - Pick by Cart")

# Upload files
picking_pool_file = st.file_uploader("Upload Picking Pool Excel file", type=["xlsx"])
sku_master_file = st.file_uploader("Upload SKU Master Excel file", type=["xlsx"])

if picking_pool_file and sku_master_file:
    picking_pool = pd.read_excel(picking_pool_file)
    sku_master = pd.read_excel(sku_master_file)

    merged = picking_pool.merge(sku_master, how='left', left_on='SKU', right_on='SKU Code')
    st.success("Files uploaded and merged successfully!")
    st.write("Sample Merged Data:", merged.head())

    output = merged.to_excel(index=False, engine='openpyxl')
    st.download_button(
        label="Download Master Pick Ticket",
        data=output,
        file_name="MasterPickTicket.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("Please upload both files to begin.")
