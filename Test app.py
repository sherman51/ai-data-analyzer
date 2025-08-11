import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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

# Month-to-date data for donuts
total_lines = 1000
back_orders = 1
sla_not_met = 0

back_order_pct = (back_orders / total_lines) * 100
order_accuracy_pct = ((total_lines - sla_not_met) / total_lines) * 100

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

# ---------- SECOND ROW: Order Trend (with KPIs) & MTD Donuts ----------
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
    st.subheader("Month to Date")

    # Create MTD donuts
    fig_mtd = make_subplots(rows=1, cols=2, specs=[[{'type':'domain'}, {'type':'domain'}]],
                            subplot_titles=["Back Order", "Order Accuracy"])

    # Back Order Donut
    fig_mtd.add_trace(go.Pie(
        labels=["Order Lines Fulfilled", "Back Orders Lines"],
        values=[total_lines - back_orders, back_orders],
        hole=0.7,
        marker_colors=["#1f77b4", "#ff7f0e"],
        textinfo="none",
        showlegend=True
    ), 1, 1)

    # Order Accuracy Donut
    fig_mtd.add_trace(go.Pie(
        labels=["Order Lines SLA Met", "Order Lines SLA Not Met"],
        values=[total_lines - sla_not_met, sla_not_met],
        hole=0.7,
        marker_colors=["#1f77b4", "#ff7f0e"],
        textinfo="none",
        showlegend=True
    ), 1, 2)

    # Annotations for targets, percentages, and counts
    fig_mtd.update_layout(
        annotations=[
            dict(text=f"<0.50%", x=0.18, y=1.05, font_size=14, font_color="green", showarrow=False),
            dict(text=f"{back_order_pct:.2f}%", x=0.18, y=0.5, font_size=20, font_color="green", showarrow=False),
            dict(text=str(back_orders), x=0.3, y=0.8, font_size=12, showarrow=False),
            dict(text=str(total_lines), x=0.07, y=0.2, font_size=12, showarrow=False),

            dict(text=f">99.50%", x=0.82, y=1.05, font_size=14, font_color="green", showarrow=False),
            dict(text=f"{order_accuracy_pct:.2f}%", x=0.82, y=0.5, font_size=20, font_color="green", showarrow=False),
            dict(text=str(sla_not_met), x=0.93, y=0.8, font_size=12, showarrow=False),
            dict(text=str(total_lines), x=0.7, y=0.2, font_size=12, showarrow=False)
        ],
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="#0B1D3A",
        font=dict(color="white"),
        legend=dict(orientation="h", y=-0.1)
    )

    st.plotly_chart(fig_mtd, use_container_width=True)
