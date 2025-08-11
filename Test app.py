import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Outbound Dashboard",
    layout="wide"
)

# =========================
# SAMPLE DATA
# =========================
np.random.seed(42)
dates = pd.date_range(datetime.today() - timedelta(days=13), periods=14)

orders_received = np.random.randint(80, 150, size=14)
orders_cancelled = np.random.randint(0, 20, size=14)

# Month to date metrics
back_order_pct = 12
back_order_count = 45
order_accuracy_pct = 96
order_accuracy_count = 560

# Orders breakdown
breakdown_data = pd.DataFrame({
    "Category": ["Tpt Booked", "Packed/Partial Packed", "Picked/Partial Picked", "Open"],
    "Back Orders": np.random.randint(5, 20, size=4),
    "Scheduled Orders": np.random.randint(10, 30, size=4),
    "Ad-hoc Normal Orders": np.random.randint(15, 40, size=4),
    "Ad-hoc Urgent Orders": np.random.randint(5, 15, size=4),
    "Ad-hoc Critical Orders": np.random.randint(2, 10, size=4)
})

# =========================
# COLOR PALETTE (SOFT & MUTED)
# =========================
colors = {
    "orders_received": "#66bb6a",
    "orders_cancelled": "#ef5350",
    "back_orders": "#9575cd",
    "scheduled_orders": "#42a5f5",
    "normal_orders": "#ffca28",
    "urgent_orders": "#ff8a65",
    "critical_orders": "#f06292"
}

# =========================
# HEADER
# =========================
st.markdown(
    "<h1 style='color:#333333; font-weight:700;'>📦 Outbound Dashboard</h1>",
    unsafe_allow_html=True
)

# KPIs
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Past 2 Weeks Orders", f"{orders_received.sum():,}")
with col2:
    st.metric("Avg. Daily Orders", f"{orders_received.mean():.0f}")
with col3:
    st.metric(f"Daily Outbound Orders ({datetime.today().strftime('%d %b %Y')})", f"{orders_received[-1]}")

# =========================
# ORDERS TREND CHART
# =========================
trend_df = pd.DataFrame({
    "Date": dates,
    "Orders Received": orders_received,
    "Orders Cancelled": orders_cancelled
})

fig_trend = go.Figure()
fig_trend.add_trace(go.Bar(
    x=trend_df["Date"],
    y=trend_df["Orders Received"],
    name="Orders Received",
    marker_color=colors["orders_received"]
))
fig_trend.add_trace(go.Bar(
    x=trend_df["Date"],
    y=trend_df["Orders Cancelled"],
    name="Orders Cancelled",
    marker_color=colors["orders_cancelled"]
))
fig_trend.update_layout(
    barmode="group",
    title="Orders Trend (Past 2 Weeks)",
    xaxis_title="Date",
    yaxis_title="Orders",
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(color="#333333")
)
st.plotly_chart(fig_trend, use_container_width=True)

# =========================
# MTD GAUGES
# =========================
col4, col5 = st.columns(2)

with col4:
    fig_backorder = go.Figure(go.Indicator(
        mode="gauge+number",
        value=back_order_pct,
        title={'text': "Back Order %", 'font': {'size': 20}},
        number={'suffix': "%"},
        gauge={'axis': {'range': [0, 100]},
               'bar': {'color': colors["back_orders"]},
               'bgcolor': "white"}
    ))
    st.plotly_chart(fig_backorder, use_container_width=True)

with col5:
    fig_accuracy = go.Figure(go.Indicator(
        mode="gauge+number",
        value=order_accuracy_pct,
        title={'text': "Order Accuracy %", 'font': {'size': 20}},
        number={'suffix': "%"},
        gauge={'axis': {'range': [0, 100]},
               'bar': {'color': colors["scheduled_orders"]},
               'bgcolor': "white"}
    ))
    st.plotly_chart(fig_accuracy, use_container_width=True)

# =========================
# ORDERS BREAKDOWN STACKED BAR
# =========================
breakdown_melt = breakdown_data.melt(id_vars="Category", var_name="Order Type", value_name="Count")

fig_breakdown = px.bar(
    breakdown_melt,
    x="Count",
    y="Category",
    color="Order Type",
    orientation="h",
    color_discrete_map={
        "Back Orders": colors["back_orders"],
        "Scheduled Orders": colors["scheduled_orders"],
        "Ad-hoc Normal Orders": colors["normal_orders"],
        "Ad-hoc Urgent Orders": colors["urgent_orders"],
        "Ad-hoc Critical Orders": colors["critical_orders"]
    },
    title="Orders Breakdown"
)
fig_breakdown.update_layout(
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(color="#333333")
)
st.plotly_chart(fig_breakdown, use_container_width=True)

# =========================
# SUMMARY TABLE
# =========================
st.markdown("### 📊 Orders Summary Table")
st.dataframe(breakdown_data.set_index("Category"))
