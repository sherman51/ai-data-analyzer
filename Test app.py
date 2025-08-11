import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta


#-----------Block Out codes--------

def BOC():
    # ---------- SECOND ROW: KPIs for Entry Count ----------
    kpi1, kpi2 = st.columns(2)
    with kpi1:
        st.metric("Total Entries", len(df_filtered))
    with kpi2:
        st.metric("Total Distinct GINo", df_filtered["GINo"].nunique())

    # ---------- THIRD ROW: Entry Trend & MTD Pie ----------
    col_trend, col_mtd = st.columns([2, 1])

    with col_trend:
        # Melting the data for trend chart
        df_long = df_filtered.melt(id_vars=["ExpDate"], var_name="Category", value_name="Count")
        fig_trend = px.bar(
            df_long,
            x="ExpDate",
            y="Count",
            color="Category",
            barmode="group",
            title="Entry Trend",
            color_discrete_map=colors
        )
        fig_trend.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(color="#333333"),
            xaxis_title="ExpDate",
            yaxis_title="Count"
        )
        st.plotly_chart(fig_trend, use_container_width=True)

    with col_mtd:
        # MTD Count for 'Status'
        status_count = df_filtered["Status"].value_counts()
        df_mtd = pd.DataFrame(status_count).reset_index()
        df_mtd.columns = ["Status", "Count"]
        fig_mtd = px.pie(
            df_mtd,
            names="Status",
            values="Count",
            title="Month-to-Date Status Distribution",
            color="Status",
            color_discrete_map=colors
        )
        fig_mtd.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(color="#333333")
        )
        st.plotly_chart(fig_mtd, use_container_width=True)



# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="Operations Dashboard", layout="wide")

# ---------- COLOR PALETTE ----------
colors = {
    "Orders Received": "#66bb6a",
    "Orders Cancelled": "#ef5350",
    "Scheduled": "#42a5f5",
    "Ad-hoc Normal": "#ffca28",
    "Ad-hoc Urgent": "#ff8a65",
    "Ad-hoc Critical": "#f06292"
}

# ---------- FILE UPLOAD ----------
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx"])

if uploaded_file is not None:
    try:
        # Read the uploaded Excel file into DataFrame (assuming the sheet is named "Orders")
        df = pd.read_excel(uploaded_file, sheet_name="Orders")  # Adjust sheet name if necessary
        
        # Validate required columns
        required_columns = ["ExpDate", "Priority", "GINo", "StorageZone", "Status"]
        if not all(col in df.columns for col in required_columns):
            st.error(f"Missing required columns: {required_columns}")
        else:
            st.success("File uploaded successfully!")

            # ---------- DATA PROCESSING ----------
            # Ensure 'ExpDate' column is in datetime format
            df["ExpDate"] = pd.to_datetime(df["ExpDate"], errors='coerce')

            # Filter data based on today's date and selected date range
            today = datetime.today()
            df_filtered = df[df["ExpDate"] <= today]

from datetime import datetime, timedelta

# Assuming today is defined
today = datetime.today()

# Generate date options for the next 4 days
date_options = [(today + timedelta(days=i)).date() for i in range(4)]

# Convert to string for display
date_labels = [date.strftime("%Y-%m-%d") for date in date_options]

# ---------- TOP ROW: Order Breakdown & Summary ----------
col_breakdown, col_summary = st.columns([2, 1])  # Breakdown wider than summary

with col_breakdown:
    # ---------- DATE FILTER SELECTION ----------
    selected_date_str = st.selectbox("Select Date", date_labels)

    # Convert selected string back to date
    selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()

    # Filter data based on the selected date
    filtered_data = df_filtered[df_filtered['ExpDate'].dt.date == selected_date]

    # Show total count in the selected date range
    st.metric("Total Entries in Breakdown", len(filtered_data))

    # Breakdown chart (example: count by 'Priority' or 'Status')
    fig_breakdown = px.bar(
        filtered_data,
        x="Priority",  # Example of categorizing by Priority
        title="Priority Breakdown",
        color="Priority",
        color_discrete_map=colors
    )
    fig_breakdown.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color="#333333"),
        xaxis_title="Priority",
        yaxis_title="Count"
    )
    st.plotly_chart(fig_breakdown, use_container_width=True)

with col_summary:
    st.subheader("Summary Data")
    st.dataframe(filtered_data, use_container_width=True)

st.markdown("---")



    except Exception as e:
        st.error(f"Error reading the Excel file: {e}")

else:
    st.info("Please upload an Excel file to get started.")






