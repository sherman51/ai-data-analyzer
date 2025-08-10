# streamlit_app.py
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px

# -------------------- Page config --------------------
st.set_page_config(page_title="Outbound Dashboard", layout="wide", initial_sidebar_state="auto")

# -------------------- Theme / Colors --------------------
BG_COLOR = "#0f2b46"          # dark blue background (dashboard)
PANEL_BG = "#0f2540"          # slightly different panel
TEXT_COLOR = "#ffffff"
GREEN = "#2ecc71"             # completed / received
ORANGE = "#ff9800"            # cancelled / orange
LIGHT_BLUE = "#9ad0f5"        # packed / partial
YELLOW = "#ffd400"            # picked
PEACH = "#f7c5b0"             # open / peach
ACCENT_GREEN = "#07b85f"      # date / KPI green text

# Apply basic CSS to give dark background to the page
st.markdown(
    f"""
    <style>
    .stApp {{ background-color: {BG_COLOR}; color: {TEXT_COLOR}; }}
    .kpi-card {{ background-color: rgba(255,255,255,0.03); padding: 14px; border-radius: 6px; }}
    .small-muted {{ color: #8fb0b6; }}
    .logo-placeholder {{
        width:72px; height:72px; border-radius: 12px; background: linear-gradient(135deg,#0ea5a3,#2563eb);
        display:inline-block; vertical-align: middle;
    }}
    .kpi-number {{ font-size: 28px; font-weight:700; color: {TEXT_COLOR}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------- Sample Data Creation --------------------
def create_sample_data():
    # Last 14 days (past 2 weeks)
    today = datetime.today().date()
    dates = [today - timedelta(days=i) for i in range(13, -1, -1)]  # oldest -> newest (14 days)
    np.random.seed(42)
    orders_received = np.random.randint(20, 70, size=len(dates))
    orders_cancelled = np.random.binomial(n=orders_received, p=0.02)  # mostly small
    df_trend = pd.DataFrame({
        "date": dates,
        "orders_received": orders_received,
        "orders_cancelled": orders_cancelled
    })
    # Month-to-date totals for gauges (sample values)
    total_order_lines = 1000
    back_order_lines = int(total_order_lines * 0.001)  # example small backorders
    order_accuracy_lines = total_order_lines - back_order_lines
    # Orders breakdown by category with status segments
    # For each order type we provide counts for: Tpt Booked, Packed/Partial, Picked/Partial, Open
    breakdown = {
        "Back Orders (Accumulated)": {"Tpt Booked": 2, "Packed/Partial Packed": 4, "Picked/Partial Picked": 3, "Open": 2},
        "Scheduled Orders": {"Tpt Booked": 5, "Packed/Partial Packed": 6, "Picked/Partial Picked": 13, "Open": 17},
        "Ad-hoc Normal Orders": {"Tpt Booked": 10, "Packed/Partial Packed": 7, "Picked/Partial Picked": 3, "Open": 0},
        "Ad-hoc Urgent Orders": {"Tpt Booked": 4, "Packed/Partial Packed": 2, "Picked/Partial Picked": 0, "Open": 2},
        "Ad-hoc Critical Orders": {"Tpt Booked": 3, "Packed/Partial Packed": 0, "Picked/Partial Picked": 3, "Open": 0},
    }
    # Summary table (rows x columns)
    summary_table = pd.DataFrame.from_dict(breakdown, orient='index').T
    return df_trend, total_order_lines, back_order_lines, order_accuracy_lines, breakdown, summary_table

df_trend, total_order_lines, back_order_lines, order_accuracy_lines, breakdown, summary_table = create_sample_data()

# -------------------- Header --------------------
col1, col2, col3 = st.columns([1.2, 3, 1])
with col1:
    # Logo placeholder + company text
    st.markdown('<div style="display:flex; align-items:center;"><div class="logo-placeholder"></div>'
                '<div style="margin-left:10px;"><h2 style="margin:0; color:white;">SSW<br><small style="color:#9fb8c4;">HEALTHCARE</small></h2></div></div>',
                unsafe_allow_html=True)

with col2:
    st.markdown("<h1 style='margin:0; color:white;'>Outbound Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<div class='small-muted'>Overview of outbound orders & operational status</div>", unsafe_allow_html=True)

with col3:
    # Show current date (green) and "Daily Outbound Orders"
    today = datetime.today().strftime("%d %b %Y")
    st.markdown(f"<div style='text-align:right; color:{ACCENT_GREEN}; font-weight:700;'>{today}</div>", unsafe_allow_html=True)
    # daily count: use last day's orders_received as sample
    daily_outbound = int(df_trend['orders_received'].iloc[-1])
    st.markdown(f"<div style='text-align:right; font-size:20px; color:{ACCENT_GREEN};'>Daily Outbound Orders:</div>", unsafe_allow_html=True)
    st.markdown(f"<div style='text-align:right; font-size:28px; font-weight:700; color:{ACCENT_GREEN};'>{daily_outbound}</div>", unsafe_allow_html=True)

st.markdown("---")

# -------------------- KPI Cards (Past 2 weeks & Avg Daily) --------------------
k1, k2, k3 = st.columns([1.5, 1.5, 6])
with k1:
    with st.container():
        st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
        st.markdown("<div style='font-size:14px; color:#bfe8c8;'>Past 2 weeks orders</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kpi-number'>{df_trend['orders_received'].sum()}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

with k2:
    with st.container():
        st.markdown('<div class="kpi-card">', unsafe_allow_html=True)
        st.markdown("<div style='font-size:14px; color:#bfe8c8;'>Avg. Daily Orders</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='kpi-number'>{int(df_trend['orders_received'].mean()):,}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# -------------------- Orders Trend Chart --------------------
st.markdown("### Orders Trend (Last 2 weeks)")
fig_trend = go.Figure()
fig_trend.add_trace(go.Bar(
    x=df_trend['date'],
    y=df_trend['orders_received'],
    name="Orders Received",
    marker_color=GREEN,
    hovertemplate="%{x|%d %b %Y}<br>Received: %{y}<extra></extra>"
))
fig_trend.add_trace(go.Bar(
    x=df_trend['date'],
    y=df_trend['orders_cancelled'],
    name="Orders Cancelled",
    marker_color=ORANGE,
    hovertemplate="%{x|%d %b %Y}<br>Cancelled: %{y}<extra></extra>"
))
fig_trend.update_layout(
    barmode='group',
    template='plotly_dark',
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    xaxis_tickformat="%d %b",
    margin=dict(t=10, b=20, l=30, r=10),
    height=350
)
st.plotly_chart(fig_trend, use_container_width=True)

# -------------------- Month to Date Gauges --------------------
st.markdown("### Month to Date")
g1, g2, spacer = st.columns([1,1,6])
# Back Order gauge
back_pct = (back_order_lines / total_order_lines) * 100 if total_order_lines else 0
with g1:
    fig_g1 = go.Figure(go.Indicator(
        mode="gauge+number",
        value=back_pct,
        number={'suffix': "%", 'font': {'size': 18, 'color': TEXT_COLOR}},
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Back Order", 'font': {'size': 16, 'color': TEXT_COLOR}},
        gauge={
            'axis': {'range': [None, 5], 'tickwidth': 1, 'tickcolor': TEXT_COLOR},
            'bar': {'color': GREEN},
            'bgcolor': "rgba(0,0,0,0)",
            'steps': [
                {'range': [0, 1], 'color': "rgba(0,0,0,0)"},
            ],
            'threshold': {
                'line': {'color': "red", 'width': 2},
                'thickness': 0.75,
                'value': 1
            }
        }
    ))
    fig_g1.update_layout(template='plotly_dark', paper_bgcolor="rgba(0,0,0,0)", height=250, margin=dict(t=0,b=0,l=0,r=0))
    st.plotly_chart(fig_g1, use_container_width=True)
    st.markdown(f"<div style='color:#bfe8c8; margin-top:-8px;'>Back Order Lines: <strong style='color:{TEXT_COLOR}'>{back_order_lines}</strong></div>", unsafe_allow_html=True)

# Order Accuracy gauge
accuracy_pct = (order_accuracy_lines / total_order_lines) * 100 if total_order_lines else 100
with g2:
    fig_g2 = go.Figure(go.Indicator(
        mode="gauge+number",
        value=accuracy_pct,
        number={'suffix': "%", 'font': {'size': 18, 'color': TEXT_COLOR}},
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Order Accuracy", 'font': {'size': 16, 'color': TEXT_COLOR}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': TEXT_COLOR},
            'bar': {'color': ACCENT_GREEN},
            'bgcolor': "rgba(0,0,0,0)",
            'steps': [
                {'range': [0, 90], 'color': "rgba(255,0,0,0.05)"},
                {'range': [90, 99], 'color': "rgba(255,255,0,0.05)"},
                {'range': [99, 100], 'color': "rgba(0,255,0,0.05)"},
            ]
        }
    ))
    fig_g2.update_layout(template='plotly_dark', paper_bgcolor="rgba(0,0,0,0)", height=250, margin=dict(t=0,b=0,l=0,r=0))
    st.plotly_chart(fig_g2, use_container_width=True)
    st.markdown(f"<div style='color:#bfe8c8; margin-top:-8px;'>Order Lines SLA Met: <strong style='color:{TEXT_COLOR}'>{order_accuracy_lines}</strong></div>", unsafe_allow_html=True)

st.markdown("---")

# -------------------- Orders Breakdown - Stacked Horizontal Bar --------------------
st.markdown("### Orders Breakdown (by status)")
order_types = list(breakdown.keys())
statuses = ["Tpt Booked", "Packed/Partial Packed", "Picked/Partial Picked", "Open"]
status_colors = {
    "Tpt Booked": GREEN,
    "Packed/Partial Packed": LIGHT_BLUE,
    "Picked/Partial Picked": YELLOW,
    "Open": PEACH
}

# Build traces in reverse order to stack nicely left-to-right
fig_break = go.Figure()
for status in statuses:
    fig_break.add_trace(go.Bar(
        y=order_types,
        x=[breakdown[ot][status] for ot in order_types],
        name=status,
        orientation='h',
        marker=dict(color=status_colors[status]),
        text=[str(breakdown[ot][status]) if breakdown[ot][status] > 0 else "" for ot in order_types],
        textposition='inside',
        insidetextanchor='middle',
        hovertemplate='%{y}<br>' + status + ': %{x}<extra></extra>'
    ))

fig_break.update_layout(
    barmode='stack',
    template='plotly_dark',
    xaxis_title='Count',
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=10, b=20, l=120, r=10),
    height=380,
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
)
st.plotly_chart(fig_break, use_container_width=True)

# -------------------- Summary Table --------------------
st.markdown("### Summary Table")
# Create a visually similar DataFrame and show
# We want rows: Tpt Booked, Packed/Partial Packed, Picked/Partial Picked, Open
# columns: Ad-hoc Critical Orders, Ad-hoc Urgent Orders, Ad-hoc Normal Orders, Scheduled Orders, Back Orders (Accumulated)
col_order_types = ["Ad-hoc Critical Orders", "Ad-hoc Urgent Orders", "Ad-hoc Normal Orders", "Scheduled Orders", "Back Orders (Accumulated)"]
# Make mapping from our breakdown keys to the display order
map_keys = {
    "Ad-hoc Critical Orders": "Ad-hoc Critical Orders",
    "Ad-hoc Urgent Orders": "Ad-hoc Urgent Orders",
    "Ad-hoc Normal Orders": "Ad-hoc Normal Orders",
    "Scheduled Orders": "Scheduled Orders",
    "Back Orders (Accumulated)": "Back Orders (Accumulated)"
}
# Build summary table consistent with earlier breakdown (some keys share same naming)
summary_rows = {
    "Tpt Booked": [breakdown[k.replace(" Orders"," (Accumulated)")] if False else None]  # placeholder
}
# We'll construct rows directly
summary_df = pd.DataFrame({
    "Ad-hoc Critical Orders": [
        breakdown["Ad-hoc Critical Orders"]["Tpt Booked"],
        breakdown["Ad-hoc Critical Orders"]["Packed/Partial Packed"],
        breakdown["Ad-hoc Critical Orders"]["Picked/Partial Picked"],
        breakdown["Ad-hoc Critical Orders"]["Open"],
    ],
    "Ad-hoc Urgent Orders": [
        breakdown["Ad-hoc Urgent Orders"]["Tpt Booked"],
        breakdown["Ad-hoc Urgent Orders"]["Packed/Partial Packed"],
        breakdown["Ad-hoc Urgent Orders"]["Picked/Partial Picked"],
        breakdown["Ad-hoc Urgent Orders"]["Open"],
    ],
    "Ad-hoc Normal Orders": [
        breakdown["Ad-hoc Normal Orders"]["Tpt Booked"],
        breakdown["Ad-hoc Normal Orders"]["Packed/Partial Packed"],
        breakdown["Ad-hoc Normal Orders"]["Picked/Partial Picked"],
        breakdown["Ad-hoc Normal Orders"]["Open"],
    ],
    "Scheduled Orders": [
        breakdown["Scheduled Orders"]["Tpt Booked"],
        breakdown["Scheduled Orders"]["Packed/Partial Packed"],
        breakdown["Scheduled Orders"]["Picked/Partial Picked"],
        breakdown["Scheduled Orders"]["Open"],
    ],
    "Back Orders (Accumulated)": [
        breakdown["Back Orders (Accumulated)"]["Tpt Booked"],
        breakdown["Back Orders (Accumulated)"]["Packed/Partial Packed"],
        breakdown["Back Orders (Accumulated)"]["Picked/Partial Picked"],
        breakdown["Back Orders (Accumulated)"]["Open"],
    ],
}, index=["Tpt Booked", "Packed/Partial Packed", "Picked/Partial Picked", "Open"])

# Display the table with some styling for dark theme
st.dataframe(summary_df.style.set_table_styles([{'selector': 'th', 'props': [('color', TEXT_COLOR)]},
                                               {'selector': 'td', 'props': [('color', TEXT_COLOR)]}]), height=220)

# -------------------- Footer note --------------------
st.markdown("<div style='text-align:right; color:#bfbfbf; margin-top:10px;'>Stay Safe & Well</div>", unsafe_allow_html=True)
