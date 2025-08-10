import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# ------------------------ PAGE CONFIG ------------------------
st.set_page_config(page_title="Outbound Dashboard", layout="wide")

# ------------------------ HEADER ------------------------
col_logo, col_title = st.columns([0.1, 0.9])
with col_logo:
    st.image("https://via.placeholder.com/80", use_container_width=True)
with col_title:
    st.markdown(
        "<h1 style='color:white;'>Outbound Dashboard</h1>",
        unsafe_allow_html=True
    )

st.markdown("<hr>", unsafe_allow_html=True)

# ------------------------ FILE UPLOAD ------------------------
uploaded_file = st.file_uploader("📂 Upload Outbound Data Excel", type=["xls", "xlsx"])

if uploaded_file:
    # Step 1: Load sheet
    df_raw = pd.read_excel(uploaded_file, sheet_name="Good Receive Analysis", header=None)

    # Step 2: Detect header row (first row containing 'Date' in column 0)
    header_row_idx = None
    for i, row in df_raw.iterrows():
        if str(row[0]).strip().lower() == "date":
            header_row_idx = i
            break

    if header_row_idx is None:
        st.error("Could not find header row with 'Date'. Please check file.")
        st.stop()

    # Step 3: Read clean data
    df = pd.read_excel(
        uploaded_file,
        sheet_name="Good Receive Analysis",
        skiprows=header_row_idx
    )

    # ------------------------ KPI CALCULATIONS ------------------------
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])

    last_14_days = df[df["Date"] >= (df["Date"].max() - pd.Timedelta(days=14))]

    total_orders = last_14_days["Orders Received"].sum()
    avg_daily_orders = last_14_days.groupby("Date")["Orders Received"].sum().mean()

    daily_outbound_orders = last_14_days[last_14_days["Date"] == df["Date"].max()]["Orders Received"].sum()

    # ------------------------ KPI CARDS ------------------------
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("📦 Past 2 Weeks Orders", f"{total_orders:,}")
    kpi2.metric("📊 Avg. Daily Orders", f"{avg_daily_orders:.0f}")
    kpi3.metric(
        f"📅 {df['Date'].max().strftime('%d %b %Y')}",
        f"{daily_outbound_orders:,}",
        delta_color="inverse"
    )

    # ------------------------ ORDERS TREND CHART ------------------------
    trend_data = last_14_days.groupby("Date")[["Orders Received", "Orders Cancelled"]].sum().reset_index()

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Bar(
        x=trend_data["Date"],
        y=trend_data["Orders Received"],
        name="Orders Received",
        marker_color="green"
    ))
    fig_trend.add_trace(go.Bar(
        x=trend_data["Date"],
        y=trend_data["Orders Cancelled"],
        name="Orders Cancelled",
        marker_color="orange"
    ))
    fig_trend.update_layout(
        barmode="group",
        title="📈 Orders Trend (Last 2 Weeks)",
        xaxis_title="Date",
        yaxis_title="Orders Count",
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font=dict(color="white")
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    # ------------------------ GAUGE CHARTS ------------------------
    gauge_col1, gauge_col2 = st.columns(2)

    back_order_pct = (df["Back Orders"].sum() / df["Orders Received"].sum()) * 100
    order_accuracy_pct = 100 - ((df["Orders Cancelled"].sum() / df["Orders Received"].sum()) * 100)

    with gauge_col1:
        fig_bo = go.Figure(go.Indicator(
            mode="gauge+number",
            value=back_order_pct,
            title={'text': "Back Order %"},
            gauge={'axis': {'range': [None, 100]}, 'bar': {'color': "orange"}}
        ))
        st.plotly_chart(fig_bo, use_container_width=True)

    with gauge_col2:
        fig_acc = go.Figure(go.Indicator(
            mode="gauge+number",
            value=order_accuracy_pct,
            title={'text': "Order Accuracy %"},
            gauge={'axis': {'range': [None, 100]}, 'bar': {'color': "green"}}
        ))
        st.plotly_chart(fig_acc, use_container_width=True)

    # ------------------------ ORDERS BREAKDOWN ------------------------
    breakdown_cols = [
        "Back Orders", "Scheduled Orders",
        "Adhoc Normal Orders", "Adhoc Urgent Orders", "Adhoc Critical Orders"
    ]
    breakdown_data = df[breakdown_cols].sum().reset_index()
    breakdown_data.columns = ["Order Type", "Count"]

    fig_breakdown = px.bar(
        breakdown_data,
        x="Count",
        y="Order Type",
        orientation="h",
        color="Order Type",
        color_discrete_sequence=["orange", "blue", "yellow", "red", "purple"]
    )
    fig_breakdown.update_layout(
        title="📦 Orders Breakdown",
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font=dict(color="white")
    )
    st.plotly_chart(fig_breakdown, use_container_width=True)

    # ------------------------ SUMMARY TABLE ------------------------
    summary_data = {
        "Status": ["Tpt Booked", "Packed/Partial Packed", "Picked/Partial Picked", "Open"],
        "Adhoc Critical Orders": [5, 3, 2, 1],
        "Adhoc Urgent Orders": [10, 6, 4, 2],
        "Adhoc Normal Orders": [20, 15, 10, 5],
        "Scheduled Orders": [30, 20, 15, 10],
        "Back Orders": [8, 5, 3, 2]
    }
    df_summary = pd.DataFrame(summary_data)
    st.markdown("### 📋 Summary Table")
    st.dataframe(df_summary, use_container_width=True)

else:
    st.info("Please upload an Excel file to generate the dashboard.")
