# streamlit_app.py
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Page config
st.set_page_config(page_title="Outbound Dashboard", layout="wide")
st.markdown(
    """
    <style>
        body {background-color: #0e2a47;}
        .block-container {padding-top: 1rem; padding-bottom: 0rem;}
        h2, h3, h4, h5, h6 {color: white;}
    </style>
    """,
    unsafe_allow_html=True
)

# Sample Data
dates = pd.date_range(start="2023-07-03", periods=14, freq="D")
orders_received = [40, 48, 30, 20, 42, 35, 45, 55, 60, 55, 58, 62, 70, 65]
orders_cancelled = [0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

# KPI values
past_2_weeks_orders = sum(orders_received)
avg_daily_orders = past_2_weeks_orders / len(dates)
daily_orders = 84
current_date = "17 Jul 2023"

# Header & KPIs
col1, col2, col3, col4 = st.columns([2,1,1,1])
with col1:
    st.markdown("## 🏥 SSW Healthcare - **Outbound Dashboard**")
with col2:
    st.metric("Past 2 Weeks Orders", f"{past_2_weeks_orders}")
with col3:
    st.metric("Avg. Daily Orders", f"{avg_daily_orders:.1f}")
with col4:
    st.metric("Daily Outbound Orders", f"{daily_orders}", help=current_date)

# Orders Trend Chart
df_orders = pd.DataFrame({
    "Date": dates,
    "Orders Received": orders_received,
    "Orders Cancelled": orders_cancelled
})

fig_orders = go.Figure()
fig_orders.add_trace(go.Bar(x=df_orders["Date"], y=df_orders["Orders Received"],
                            name="Orders Received", marker_color="#4CAF50"))
fig_orders.add_trace(go.Bar(x=df_orders["Date"], y=df_orders["Orders Cancelled"],
                            name="Orders Cancelled", marker_color="#FF6F61"))
fig_orders.update_layout(
    barmode="group",
    plot_bgcolor="#0e2a47",
    paper_bgcolor="#0e2a47",
    font=dict(color="white"),
    title="Orders in Past 2 Weeks"
)
st.plotly_chart(fig_orders, use_container_width=True)

# Month to Date Gauges
col1, col2 = st.columns(2)
with col1:
    fig_back = go.Figure(go.Indicator(
        mode="gauge+number",
        value=0.10,
        gauge={
            'axis': {'range': [0, 1]},
            'bar': {'color': "#4CAF50"},
            'bgcolor': "white"
        },
        number={'valueformat': ".2%"},
        title={'text': "Back Order %", 'font': {'size': 24, 'color': 'white'}}
    ))
    fig_back.update_layout(paper_bgcolor="#0e2a47", font=dict(color="white"))
    st.plotly_chart(fig_back, use_container_width=True)

with col2:
    fig_accuracy = go.Figure(go.Indicator(
        mode="gauge+number",
        value=1.00,
        gauge={
            'axis': {'range': [0, 1]},
            'bar': {'color': "#4CAF50"},
            'bgcolor': "white"
        },
        number={'valueformat': ".2%"},
        title={'text': "Order Accuracy %", 'font': {'size': 24, 'color': 'white'}}
    ))
    fig_accuracy.update_layout(paper_bgcolor="#0e2a47", font=dict(color="white"))
    st.plotly_chart(fig_accuracy, use_container_width=True)

# Horizontal Stacked Bar for Order Breakdown
breakdown = pd.DataFrame({
    "Category": ["Back Orders", "Scheduled Orders", "Ad-hoc Normal Orders", "Ad-hoc Urgent Orders", "Ad-hoc Critical Orders"],
    "Tpt Booked": [2, 5, 10, 4, 3],
    "Packed/Partial Packed": [4, 6, 7, 2, 0],
    "Picked/Partial Picked": [3, 13, 3, 0, 3],
    "Open": [2, 17, 0, 0, 0]
})

colors = {
    "Tpt Booked": "#4CAF50",
    "Packed/Partial Packed": "#42A5F5",
    "Picked/Partial Picked": "#FFB300",
    "Open": "#E57373"
}

fig_breakdown = go.Figure()
for col in ["Tpt Booked", "Packed/Partial Packed", "Picked/Partial Picked", "Open"]:
    fig_breakdown.add_trace(go.Bar(
        y=breakdown["Category"],
        x=breakdown[col],
        name=col,
        orientation='h',
        marker_color=colors[col],
        text=breakdown[col],
        textposition='inside'
    ))

fig_breakdown.update_layout(
    barmode="stack",
    plot_bgcolor="#0e2a47",
    paper_bgcolor="#0e2a47",
    font=dict(color="white"),
    title="Order Breakdown"
)
st.plotly_chart(fig_breakdown, use_container_width=True)

# Summary Table
st.markdown("### Summary Table")
styled_table = breakdown.style.set_properties(**{
    'background-color': '#0e2a47',
    'color': 'white',
    'border-color': 'white'
})
st.dataframe(styled_table)
