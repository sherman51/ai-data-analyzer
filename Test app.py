import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# ---------- SAMPLE DATA ----------
np.random.seed(42)
dates = pd.date_range(start="2025-07-01", periods=30, freq='D')
orders_received = np.random.randint(80, 150, size=30)
orders_cancelled = np.random.randint(5, 20, size=30)

df_orders = pd.DataFrame({
    "Date": dates,
    "Orders Received": orders_received,
    "Orders Cancelled": orders_cancelled
})

order_breakdown = pd.DataFrame({
    "Category": ["Scheduled", "Ad-hoc Normal", "Ad-hoc Urgent", "Ad-hoc Critical"],
    "Orders": [120, 90, 45, 20]
})

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

# ---------- TOP ROW: Order Breakdown & Summary ----------
col_breakdown, col_summary = st.columns([2, 1])

with col_breakdown:
    st.metric("Total Orders in Breakdown", int(order_breakdown["Orders"].sum()))
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
    st.dataframe(df_orders, use_container_width=True)

st.markdown("---")

# ---------- SECOND ROW: Order Trend (with KPIs) & MTD Pie ----------
col_trend, col_mtd = st.columns([2, 1])

with col_trend:
    # KPIs for Order Trend
    kpi1, kpi2 = st.columns(2)
    with kpi1:
        st.metric("Total Orders Received", int(df_orders["Orders Received"].sum()))
    with kpi2:
        st.metric("Total Orders Cancelled", int(df_orders["Orders Cancelled"].sum()))

    # Order Trend Chart
    df_orders_long = df_orders.melt(id_vars=["Date"], var_name="Order Type", value_name="Count")
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
    mtd_orders = {
        "Orders Received": df_orders["Orders Received"].sum(),
        "Orders Cancelled": df_orders["Orders Cancelled"].sum()
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
