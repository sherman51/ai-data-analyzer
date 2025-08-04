import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# ------------------------ PAGE CONFIG ------------------------
st.set_page_config(page_title="📊 Good Receive Analysis Dashboard", layout="wide")
st.title("📦 Good Receive Analysis Dashboard")

# ------------------------ FILE UPLOAD ------------------------
uploaded_file = st.sidebar.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file:
    # Skip metadata rows, header starts on row 6 (index 5)
    df_raw = pd.read_excel(uploaded_file, skiprows=5)

    # Clean up
    df = df_raw.dropna(axis=1, how="all")  # Remove empty columns
    df.dropna(how="all", inplace=True)     # Remove empty rows

    # Parse date columns
    date_columns = ["ExpectedDate", "GateInDate", "GRDate", "CreatedOn", "FinalizedOn"]
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Sidebar Filters
    st.sidebar.header("🔍 Filters")
    supplier_list = df["Supplier"].dropna().unique().tolist() if "Supplier" in df.columns else []
    gr_type_list = df["GRType"].dropna().unique().tolist() if "GRType" in df.columns else []

    supplier_filter = st.sidebar.multiselect("Select Supplier", supplier_list, default=supplier_list)
    gr_type_filter = st.sidebar.multiselect("Select GR Type", gr_type_list, default=gr_type_list)

    if "Supplier" in df.columns:
        df = df[df["Supplier"].isin(supplier_filter)]
    if "GRType" in df.columns:
        df = df[df["GRType"].isin(gr_type_filter)]

    # ------------------------ DATA PREVIEW ------------------------
    st.subheader("🧹 Cleaned Dataset Preview")
    st.dataframe(df.head(50), use_container_width=True)

    # ------------------------ SUMMARY METRICS ------------------------
    st.subheader("📈 Summary Metrics")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total GRNs", df["GRNO"].nunique() if "GRNO" in df.columns else "N/A")
    with col2:
        st.metric("Unique Suppliers", df["Supplier"].nunique() if "Supplier" in df.columns else "N/A")
    with col3:
        st.metric("Total Rows", len(df))

# ------------------------ VISUALIZATION 1: MONTHLY GR SUMMARY ------------------------
st.subheader("📊 Monthly GR Summary (Grouped by GRDate)")

if "GRDate" in df.columns:
    df_monthly = df.dropna(subset=["GRDate"]).copy()
    df_monthly["GR_Month"] = df_monthly["GRDate"].dt.to_period("M").astype(str)
    month_summary = df_monthly.groupby("GR_Month").size().reset_index(name="Total GRs")

    fig1 = px.bar(
        month_summary,
        x="GR_Month",
        y="Total GRs",
        text="Total GRs",
        title="Monthly GR Summary",
        labels={"GR_Month": "Month", "Total GRs": "Goods Received"},
    )
    fig1.update_traces(textposition="outside")
    fig1.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig1, use_container_width=True)
else:
    st.info("GRDate column not found, can't plot monthly summary.")


    # ------------------------ VISUALIZATION 2: BAR CHART (Today vs Forecast) ------------------------
    st.subheader("📦 Today's Progress & Upcoming Forecast")

    # Use ExpectedDate for forecasting (can change to GRDate if needed)
    if "ExpectedDate" in df.columns:
        today = pd.to_datetime(datetime.now().date())
        tomorrow = today + timedelta(days=1)
        next_7 = today + timedelta(days=7)

        df_expected = df.dropna(subset=["ExpectedDate"])

        today_count = df_expected[df_expected["ExpectedDate"].dt.date == today.date()].shape[0]
        tomorrow_count = df_expected[df_expected["ExpectedDate"].dt.date == tomorrow.date()].shape[0]
        next_7_count = df_expected[
            (df_expected["ExpectedDate"].dt.date > tomorrow.date()) &
            (df_expected["ExpectedDate"].dt.date <= next_7.date())
        ].shape[0]

        forecast_df = pd.DataFrame({
            "Period": ["Today", "Tomorrow", "Next 7 Days"],
            "Expected GRs": [today_count, tomorrow_count, next_7_count]
        })

        fig2 = px.bar(forecast_df, x="Period", y="Expected GRs", text="Expected GRs",
                      title="GR Forecast", color="Period")
        st.plotly_chart(fig2, use_container_width=True)

    else:
        st.warning("ExpectedDate column not found. Forecast chart not available.")

else:
    st.info("⬅ Please upload a Good Receive Excel file to begin.")

