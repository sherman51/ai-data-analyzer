import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
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
        # Read the uploaded Excel file into DataFrames
        df_orders = pd.read_excel(uploaded_file, sheet_name="Orders")  # Ensure sheet name is correct
        order_breakdown = pd.read_excel(uploaded_file, sheet_name="Order Breakdown")  # Ensure this sheet exists
        
        # Validate columns in the Orders sheet
        required_columns = ["Date", "Orders Received", "Orders Cancelled"]
        if not all(col in df_orders.columns for col in required_columns):
            st.error(f"Missing required columns in the Orders sheet: {required_columns}")
        else:
            st.success("File uploaded successfully!")

            # ---------- DATA PROCESSING ----------
            # Ensure the 'Date' column is datetime format
            df_orders["Date"] = pd.to_datetime(df_orders["Date"], errors='coerce')

            # Calculate today's date and filter data based on that
            today = datetime.today()
            df_orders_filtered = df_orders[df_orders["Date"] <= today]

            # ---------- TOP ROW: Order Breakdown & Summary ----------
            col_breakdown, col_summary = st.columns([2, 1])  # Breakdown wider than summary

            with col_breakdown:
                # ---------- DATE FILTER SELECTION ----------
                date_options = [
                    "Today", 
                    "Today +1", 
                    "Today +2", 
                    "Today +3"
                ]
                selected_date_option = st.selectbox("Select Date Range", date_options)

                # Calculate the selected date offset
                if selected_date_option == "Today":
                    selected_date = today
                elif selected_date_option == "Today +1":
                    selected_date = today + timedelta(days=1)
                elif selected_date_option == "Today +2":
                    selected_date = today + timedelta(days=2)
                elif selected_date_option == "Today +3":
                    selected_date = today + timedelta(days=3)

                # Filter data based on the selected date
                filtered_data = df_orders_filtered[df_orders_filtered['Date'] == selected_date]

                # Show total orders in the selected date range
                st.metric("Total Orders in Breakdown", int(filtered_data["Orders Received"].sum()))
                
                # Order breakdown chart
                fig_breakdown = px.bar(
                    order_breakdown,
                    x="Orders",
                    y="Category",
                    orientation="h",
                    title="Order Breakdown",
                    color="Category",
                    color_discrete_map=colors
                )
                fig_breakdown.update_layout(
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    font=dict(color="#333333"),
                    yaxis=dict(categoryorder="total ascending"),
                    xaxis_title="Number of Orders"
                )
                st.plotly_chart(fig_breakdown, use_container_width=True)

            with col_summary:
                st.subheader("Summary Data")
                st.dataframe(filtered_data, use_container_width=True)

            st.markdown("---")

            # ---------- SECOND ROW: KPIs for Order Trend ----------
            kpi1, kpi2 = st.columns(2)
            with kpi1:
                st.metric("Total Orders Received", int(df_orders_filtered["Orders Received"].sum()))
            with kpi2:
                st.metric("Total Orders Cancelled", int(df_orders_filtered["Orders Cancelled"].sum()))

            # ---------- THIRD ROW: Order Trend & MTD Pie ----------
            col_trend, col_mtd = st.columns([2, 1])

            with col_trend:
                df_orders_long = df_orders_filtered.melt(id_vars=["Date"], var_name="Order Type", value_name="Count")
                fig_trend = px.bar(
                    df_orders_long,
                    x="Date",
                    y="Count",
                    color="Order Type",
                    barmode="group",
                    title="Order Trend",
                    color_discrete_map=colors
                )
                fig_trend.update_layout(
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    font=dict(color="#333333"),
                    xaxis_title="Date",
                    yaxis_title="Number of Orders"
                )
                st.plotly_chart(fig_trend, use_container_width=True)

            with col_mtd:
                # MTD Orders
                mtd_orders = {
                    "Orders Received": df_orders_filtered["Orders Received"].sum(),
                    "Orders Cancelled": df_orders_filtered["Orders Cancelled"].sum()
                }
                df_mtd = pd.DataFrame(list(mtd_orders.items()), columns=["Type", "Count"])
                fig_mtd = px.pie(
                    df_mtd,
                    names="Type",
                    values="Count",
                    title="Month-to-Date Orders",
                    color="Type",
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
