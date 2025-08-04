import streamlit as st
import pandas as pd
import plotly.express as px

# ------------------------ PAGE CONFIG ------------------------
st.set_page_config(page_title="📊 Good Receive Analysis Dashboard", layout="wide")
st.title("📦 Good Receive Analysis Dashboard")

# ------------------------ FILE UPLOAD ------------------------
uploaded_file = st.sidebar.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file:
    # Skip top metadata rows (header at row 5)
    df_raw = pd.read_excel(uploaded_file, skiprows=4)

    # Drop columns with all NaNs
    df = df_raw.dropna(axis=1, how="all")

    # Drop rows where all are NaNs
    df.dropna(how="all", inplace=True)

    # Parse date columns safely
    date_columns = ["ExpectedDate", "GateInDate", "GRDate", "CreatedOn", "FinalizedOn"]
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Sidebar filters
    st.sidebar.header("🔍 Filters")
    supplier_list = df["Supplier"].dropna().unique().tolist() if "Supplier" in df.columns else []
    gr_type_list = df["GRType"].dropna().unique().tolist() if "GRType" in df.columns else []

    supplier_filter = st.sidebar.multiselect("Select Supplier", supplier_list, default=supplier_list)
    gr_type_filter = st.sidebar.multiselect("Select GR Type", gr_type_list, default=gr_type_list)

    # Filtered Data
    if "Supplier" in df.columns:
        df = df[df["Supplier"].isin(supplier_filter)]
    if "GRType" in df.columns:
        df = df[df["GRType"].isin(gr_type_filter)]

    # Display data
    st.subheader("🧹 Cleaned Dataset Preview")
    st.dataframe(df.head(50), use_container_width=True)

    # Summary Metrics
    st.subheader("📈 Summary Metrics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total GRNs", df["GRNO"].nunique() if "GRNO" in df.columns else "N/A")
    with col2:
        st.metric("Unique Suppliers", df["Supplier"].nunique() if "Supplier" in df.columns else "N/A")
    with col3:
        st.metric("Total Rows", len(df))

    # Plotly Visualization
    st.subheader("📅 GR Count Over Time")
    if "GRDate" in df.columns:
        df_plot = df.groupby(df["GRDate"].dt.date).size().reset_index(name="Count")
        fig = px.line(df_plot, x="GRDate", y="Count", title="GRs Over Time")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("GRDate column not found, can't plot timeline.")

else:
    st.info("⬅ Please upload a Good Receive Excel file to begin.")
