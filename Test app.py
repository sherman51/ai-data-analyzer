import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import io

# ------------------ PAGE CONFIG ------------------
st.set_page_config(page_title="Outbound Dashboard", layout="wide")

# ------------------ HEADER ------------------
col_logo, col_title = st.columns([0.2, 0.8])
with col_logo:
    st.image("https://via.placeholder.com/80x80.png?text=Logo", use_container_width=True)
with col_title:
    st.markdown("<h1 style='color:white;'>Outbound Dashboard</h1>", unsafe_allow_html=True)

# ------------------ FILE UPLOAD ------------------
st.sidebar.header("📂 Upload Your Data")
uploaded_file = st.sidebar.file_uploader("Upload Excel or CSV", type=["xlsx", "xls", "csv"])

# ------------------ DATA LOADING ------------------
def load_sample_data():
    today = datetime.today()
    dates = [today - timedelta(days=i) for i in range(13, -1, -1)]
    data = {
        "Date": [d.strftime("%Y-%m-%d") for d in dates],
        "Orders Received": [120, 130, 125, 140, 150, 145, 135, 138, 142, 150, 148, 155, 160, 165],
        "Orders Cancelled": [5, 6, 4, 7, 8, 5, 4, 6, 5, 7, 6, 5, 8, 4],
        "Back Order": [10, 12, 15, 10, 8, 7, 9, 11, 12, 10, 8, 7, 6, 5],
        "Order Accuracy": [98, 97, 99, 98, 96, 97, 99, 98, 97, 96, 98, 99, 97, 98]
    }
    return pd.DataFrame(data)

if uploaded_file:
    if uploaded_file.name.endswith((".xlsx", ".xls")):
        df = pd.read_excel(uploaded_file)
    else:
        df = pd.read_csv(uploaded_file)
else:
    df = load_sample_data()

# ------------------ KPI SECTION ------------------
total_orders = df["Orders Received"].sum()
avg_daily_orders = df["Orders Received"].mean()
daily_orders = df["Orders Received"].iloc[-1]

col1, col2, col3 = st.columns(3)
col1.metric("📦 Past 2 Weeks Orders", f"{total_orders}")
col2.metric("📊 Avg. Daily Orders", f"{avg_daily_orders:.0f}")
col3.markdown(f"<h4 style='color:green;'>📅 {datetime.today().strftime('%Y-%m-%d')}</h4>", unsafe_allow_html=True)
col3.metric("Daily Outbound Orders", f"{daily_orders}")

# ------------------ ORDERS TREND CHART ------------------
fig_bar = go.Figure()
fig_bar.add_trace(go.Bar(x=df["Date"], y=df["Orders Received"], name="Orders Received", marker_color="green"))
fig_bar.add_trace(go.Bar(x=df["Date"], y=df["Orders Cancelled"], name="Orders Cancelled", marker_color="orange"))
fig_bar.update_layout(barmode="group", title="Orders Trend (Last 2 Weeks)", xaxis_title="Date", yaxis_title="Orders")
st.plotly_chart(fig_bar, use_container_width=True)

# ------------------ MTD GAUGES ------------------
col_g1, col_g2 = st.columns(2)

with col_g1:
    back_order_percent = (df["Back Order"].sum() / df["Orders Received"].sum()) * 100
    fig_g1 = go.Figure(go.Indicator(
        mode="gauge+number",
        value=back_order_percent,
        title={'text': "Back Order (%)"},
        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "orange"}},
        number={'suffix': "%"}
    ))
    st.plotly_chart(fig_g1, use_container_width=True)

with col_g2:
    order_accuracy_avg = df["Order Accuracy"].mean()
    fig_g2 = go.Figure(go.Indicator(
        mode="gauge+number",
        value=order_accuracy_avg,
        title={'text': "Order Accuracy (%)"},
        gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "green"}},
        number={'suffix': "%"}
    ))
    st.plotly_chart(fig_g2, use_container_width=True)

# ------------------ ORDERS BREAKDOWN ------------------
breakdown_data = pd.DataFrame({
    "Category": ["Back Orders (Accumulated)", "Scheduled Orders", "Ad-hoc Normal", "Ad-hoc Urgent", "Ad-hoc Critical"],
    "Count": [20, 40, 35, 15, 8]
})
fig_breakdown = px.bar(breakdown_data, x="Count", y="Category", orientation='h',
                       color="Category", title="Orders Breakdown",
                       color_discrete_map={
                           "Back Orders (Accumulated)": "orange",
                           "Scheduled Orders": "blue",
                           "Ad-hoc Normal": "yellow",
                           "Ad-hoc Urgent": "red",
                           "Ad-hoc Critical": "purple"
                       })
st.plotly_chart(fig_breakdown, use_container_width=True)

# ------------------ SUMMARY TABLE ------------------
summary_data = pd.DataFrame({
    "Status": ["Tpt Booked", "Packed/Partial Packed", "Picked/Partial Picked", "Open"],
    "Ad-hoc Critical Orders": [2, 1, 3, 2],
    "Ad-hoc Urgent Orders": [5, 4, 3, 2],
    "Ad-hoc Normal Orders": [8, 7, 6, 5],
    "Scheduled Orders": [10, 12, 8, 6],
    "Back Orders (Accumulated)": [3, 2, 4, 1]
})
st.dataframe(summary_data)
