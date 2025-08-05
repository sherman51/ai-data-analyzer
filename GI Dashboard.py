import streamlit as st
import pandas as pd
from datetime import datetime

# ----------------------------
# Data Loading & Cleaning
# ----------------------------

@st.cache_data
def load_data(file_path):
    # Skip first 4 rows to get proper headers
    df = pd.read_excel(file_path, sheet_name="GIanalysis", skiprows=4)

    # Drop empty unnamed columns
    df = df.loc[:, ~df.columns.astype(str).str.contains("^Unnamed")]

    # Convert relevant date columns
    date_cols = ["ShippedOn", "CreatedOn", "ExpectedDate", "AddDate", "EditDate"]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Map Priority values (normalize)
    if "Priority" in df.columns:
        priority_map = {
            "3-ADHOC Urgent": "ADHOC Urgent",
            "1-Normal": "Normal"
        }
        df["Priority"] = df["Priority"].replace(priority_map)

    # Drop rows missing GI No
    if "GINo" in df.columns:
        df = df[df["GINo"].notna()]

    return df

# ----------------------------
# Metrics Computation
# ----------------------------

def compute_metrics(df):
    # Filter last 6 months
    today = pd.Timestamp.today()
    six_months_ago = today - pd.DateOffset(months=6)
    df_6m = df[df["CreatedOn"] >= six_months_ago]

    # KPI metrics
    total_gi_lines = len(df_6m)
    outstanding_orders = df[df["ShippedOn"].isna()]
    urgent_orders = df[df["Priority"] == "ADHOC Urgent"]

    # Top 10 SKUs
    if "SKUCode" in df_6m.columns:
        top_skus = (
            df_6m["SKUCode"]
            .value_counts()
            .head(10)
            .reset_index()
            .rename(columns={"index": "SKUCode", "SKUCode": "Count"})
        )
    else:
        top_skus = pd.DataFrame(columns=["SKUCode", "Count"])

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
        "urgent_orders_table": urgent_orders[["GINo", "Account", "SKUCode", "ShipToCode", "CreatedOn"]]
    }

# ----------------------------
# Streamlit Dashboard
# ----------------------------

def main():
    st.set_page_config(page_title="Goods Issue Dashboard", layout="wide", initial_sidebar_state="expanded")
    st.title("📦 Goods Issue Dashboard")

    # File uploader
    uploaded_file = st.file_uploader("Upload Goods Issue Excel", type=["xlsx"])
    if uploaded_file is None:
        st.warning("Please upload the Goods Issue Excel file to proceed.")
        return

    # Load & process
    df = load_data(uploaded_file)
    metrics = compute_metrics(df)

    # KPI Cards
    st.subheader("Key Metrics (Last 6 Months)")
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Total GI Lines", metrics["total_gi_lines"])
    kpi2.metric("Outstanding Orders", metrics["outstanding_count"])
    kpi3.metric("ADHOC Urgent Orders", metrics["urgent_count"])

    # Monthly Trend
    st.subheader("Monthly GI Lines Trend (Last 6 Months)")
    if not metrics["monthly_trend"].empty:
        st.line_chart(metrics["monthly_trend"].set_index("CreatedOn"))
    else:
        st.info("No data for the last 6 months.")

    # Priority Breakdown
    st.subheader("Priority Breakdown (Last 6 Months)")
    if not metrics["priority_breakdown"].empty:
        st.bar_chart(metrics["priority_breakdown"].set_index("Priority"))
    else:
        st.info("No priority data available.")

    # Top 10 SKUs
    st.subheader("Top 10 SKUs (Last 6 Months)")
    if not metrics["top_skus"].empty:
        st.bar_chart(metrics["top_skus"].set_index("SKUCode"))
    else:
        st.info("No SKU data available.")

    # Urgent Orders Table
    st.subheader("Current ADHOC Urgent Orders")
    if not metrics["urgent_orders_table"].empty:
        st.dataframe(metrics["urgent_orders_table"])
    else:
        st.success("No ADHOC Urgent orders at the moment.")

if __name__ == "__main__":
    main()
