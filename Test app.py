import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

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
        # ---------- READ EXCEL ----------
        df = pd.read_excel(uploaded_file, sheet_name="Orders")  # Adjust sheet name if necessary

        # ---------- VALIDATE COLUMNS ----------
        required_columns = ["ExpDate", "Priority", "GINo", "StorageZone", "Status"]
        if not all(col in df.columns for col in required_columns):
            st.error(f"Missing required columns: {required_columns}")
        else:
            st.success("File uploaded successfully!")

            # ---------- DATA PREP ----------
            df["ExpDate"] = pd.to_datetime(df["ExpDate"], errors='coerce')
            df_full = df.copy()  # Keep all data unfiltered for global use

            # ---------- DATE OPTIONS ----------
            today = datetime.today()
            date_options = [(today + timedelta(days=i)).date() for i in range(4)]
            date_labels = [date.strftime("%Y-%m-%d") for date in date_options]

            # ---------- TOP ROW: Breakdown & Summary ----------
            col_breakdown, col_summary = st.columns([2, 1])

            with col_breakdown:
                selected_date_str = st.selectbox("Select Date", date_labels)
                selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()

                # Filter only for this part
                filtered_data = df_full[df_full['ExpDate'].dt.date == selected_date]

                st.metric("Total Entries in Breakdown", len(filtered_data))

                fig_breakdown = px.bar(
                    filtered_data,
                    x="Priority",
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

            # ---------- SECOND ROW: KPIs ----------
            kpi1, kpi2 = st.columns(2)
            with kpi1:
                st.metric("Total Entries", len(df_full))
            with kpi2:
                st.metric("Total Distinct GINo", df_full["GINo"].nunique())

            # ---------- THIRD ROW: Entry Trend & MTD Pie ----------
            col_trend, col_mtd = st.columns([2, 1])

            with col_trend:
                df_long = df_full.melt(id_vars=["ExpDate"], var_name="Category", value_name="Count")
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
                status_count = df_full["Status"].value_counts()
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

    except Exception as e:
        st.error(f"Error reading the Excel file: {e}")
else:
    st.info("Please upload an Excel file to get started.")
