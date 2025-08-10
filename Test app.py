import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# ------------------------ PAGE CONFIG ------------------------
st.set_page_config(layout="wide", page_title="Operations Dashboard")

# Dark theme
st.markdown("""
    <style>
        body { background-color: #0E1117; color: white; }
        .stMetric { background-color: #1E1E1E; padding: 15px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# ------------------------ KPI ROW ------------------------
st.title("📊 Operations Dashboard")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Past 2 Weeks Orders", "12,450", "+5%")
col2.metric("Avg. Daily Orders", "890", "+2%")
col3.metric("Date", "10 Aug 2025")
col4.metric("Daily Outbound Orders", "950", "-3%")

# ------------------------ CHARTS ROW ------------------------
left_col, right_col = st.columns([2, 2])

# Left bar chart
bar_data = pd.DataFrame({
    "Date": pd.date_range("2025-07-28", periods=10),
    "Orders": [800, 850, 780, 900, 950, 1000, 870, 920, 980, 940]
})
fig_bar = px.bar(bar_data, x="Date", y="Orders", title="Orders Received (Last 2 Weeks)", color_discrete_sequence=["#00CC96"])
fig_bar.update_layout(plot_bgcolor="#0E1117", paper_bgcolor="#0E1117", font_color="white")
left_col.plotly_chart(fig_bar, use_container_width=True)

# Right stacked horizontal bar
stack_data = pd.DataFrame({
    "Category": ["Back Orders", "Scheduled", "Ad-hoc Normal", "Ad-hoc Urgent", "Ad-hoc Critical"],
    "Volume": [120, 400, 150, 80, 50]
})
fig_stack = px.bar(stack_data, x="Volume", y="Category", orientation="h", title="Order Breakdown", color="Category",
                   color_discrete_map={
                       "Back Orders": "#EF553B",
                       "Scheduled": "#636EFA",
                       "Ad-hoc Normal": "#00CC96",
                       "Ad-hoc Urgent": "#FFA15A",
                       "Ad-hoc Critical": "#AB63FA"
                   })
fig_stack.update_layout(plot_bgcolor="#0E1117", paper_bgcolor="#0E1117", font_color="white", showlegend=False)
right_col.plotly_chart(fig_stack, use_container_width=True)

# ------------------------ GAUGES ROW ------------------------
g1, g2 = st.columns(2)

# Gauge 1 - Order Accuracy
fig_g1 = go.Figure(go.Indicator(
    mode="gauge+number",
    value=96,
    title={'text': "Order Accuracy (%)"},
    gauge={'axis': {'range': [0, 100]},
           'bar': {'color': "#00CC96"},
           'bgcolor': "white",
           'steps': [{'range': [0, 80], 'color': "#FF4B4B"},
                     {'range': [80, 95], 'color': "#FFA15A"},
                     {'range': [95, 100], 'color': "#00CC96"}]}
))
fig_g1.update_layout(plot_bgcolor="#0E1117", paper_bgcolor="#0E1117", font_color="white")
g1.plotly_chart(fig_g1, use_container_width=True)

# Gauge 2 - Back Order %
fig_g2 = go.Figure(go.Indicator(
    mode="gauge+number",
    value=4,
    title={'text': "Back Order (%)"},
    gauge={'axis': {'range': [0, 20]},
           'bar': {'color': "#EF553B"},
           'steps': [{'range': [0, 5], 'color': "#00CC96"},
                     {'range': [5, 10], 'color': "#FFA15A"},
                     {'range': [10, 20], 'color': "#FF4B4B"}]}
))
fig_g2.update_layout(plot_bgcolor="#0E1117", paper_bgcolor="#0E1117", font_color="white")
g2.plotly_chart(fig_g2, use_container_width=True)

# ------------------------ TABLE ROW ------------------------
status_data = pd.DataFrame({
    "Status": ["Tpt Booked", "Packed", "Picked", "Open"],
    "Orders": [320, 450, 210, 80]
})
st.subheader("Order Status Breakdown")
st.dataframe(status_data, use_container_width=True)
