import streamlit as st
import pandas as pd
import numpy as np

# ----------------------------
# Data Cleaning & Preparation
# ----------------------------

@st.cache_data
@st.cache_data
def load_data(file_path):
    # Skip first 4 rows, row 5 becomes header
    df = pd.read_excel(file_path, sheet_name="GIanalysis", skiprows=4)

    # Drop columns with all NaNs or unnamed
    df = df.loc[:, ~df.columns.astype(str).str.contains("^Unnamed")]

    # Ensure key columns exist
    expected_cols = ["Account", "GINo", "CustRef", "Priority", "PONumber",
                     "ShippedOn", "CreatedOn", "ExpectedDate", "ShipToCode"]
    # Only keep those that exist in file
    df = df[[col for col in expected_cols if col in df.columns]]

    # Convert relevant date columns to datetime
    date_cols = ["ShippedOn", "CreatedOn", "ExpectedDate"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Drop rows without GI number (invalid)
    if "GINo" in df.columns:
        df = df[df["GINo"].notna()]

    return df


# ----------------------------
# Metrics Computation
# ----------------------------

def compute_metrics(df):
    # Last 6 months filter
    today = pd.Timestamp.today()
    six_months_ago = today - pd.DateOffset(months=6)
    df_6m = df[df["CreatedOn"] >= six_months_ago]

    # KPI Metrics
    total_gi_lines = len(df_6m)
    outstanding_orders = df[df["ShippedOn"].isna()]
    urgent_orders = df[df["Priority"].str.contains("3-ADHOC Urgent", na=False)]

    # Top 10 SKUs (assuming PONumber is SKU)
    top_skus = (
        df_6m["PONumber"]
        .value_counts()
        .head(10)
        .reset_index()
        .rename(columns={"index": "SKU", "PONumber": "Count"})
    )

    # Monthly trend
    monthly_trend = (
        df_6m.groupby(pd.Grouper(key="CreatedOn", freq="M"))["GINo"]
        .count()
        .reset_index()
        .rename(columns={"GINo": "GI Lines"})
    )

    # Priority breakdown
    priority_breakdown = df_6m["Priority"].value_counts().reset_index()
    priority_breakdown.columns = ["Priority", "Count"]

    return {
        "total_gi_lines": total_gi_lines,
        "outstanding_count": len(outstanding_orders),
        "urgent_count": len(urgent_orders),
        "top_skus": top_skus,
        "monthly_trend": monthly_trend,
        "priority_breakdown": priority_breakdown,
        "urgent_orders_table": urgent_orders[["GINo", "Account", "PONumber", "ShipToCode", "CreatedOn"]]
    }

# ----------------------------
# Streamlit UI
# ----------------------------

def main():
    st.set_page_config(page_title="Goods Issue Dashboard", layout="wide")
    st.title("📦 Goods Issue Dashboard")

    # File uploader
    uploaded_file = st.file_uploader("Upload Goods Issue Excel", type=["xlsx"])
    if uploaded_file is None:
        st.warning("Please upload the Goods Issue Excel file to proceed.")
        return

    # Load and process
    df = load_data(uploaded_file)
    metrics = compute_metrics(df)

    # KPIs
    st.subheader("Key Metrics (Last 6 Months)")
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Total GI Lines", metrics["total_gi_lines"])
    kpi2.metric("Outstanding Orders", metrics["outstanding_count"])
    kpi3.metric("ADHOC Urgent Orders", metrics["urgent_count"])

    # Monthly trend chart
    st.subheader("Monthly GI Lines Trend (6 months)")
    st.line_chart(metrics["monthly_trend"].set_index("CreatedOn"))

    # Priority breakdown
    st.subheader("Priority Breakdown")
    st.bar_chart(metrics["priority_breakdown"].set_index("Priority"))

    # Top 10 SKUs
    st.subheader("Top 10 SKUs (6 months)")
    st.bar_chart(metrics["top_skus"].set_index("SKU"))

    # Urgent Orders Table
    st.subheader("Current ADHOC Urgent Orders")
    st.dataframe(metrics["urgent_orders_table"])

if __name__ == "__main__":
    main()


