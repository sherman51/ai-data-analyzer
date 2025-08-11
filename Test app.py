import streamlit as st
import pandas as pd
import plotly.express as px

# ===================== PAGE CONFIG =====================
st.set_page_config(
    page_title="📊 GI Analysis Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===================== STYLING =====================
st.markdown("""
    <style>
        /* Background */
        .stApp {
            background-color: #f9f9f9;
        }

        /* Cards */
        .metric-card {
            padding: 20px;
            border-radius: 12px;
            background-color: white;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
            text-align: center;
        }

        /* Titles */
        h1, h2, h3 {
            font-family: 'Segoe UI', sans-serif;
        }
    </style>
""", unsafe_allow_html=True)

# ===================== SIDEBAR =====================
st.sidebar.header("⚙️ Dashboard Settings")
uploaded_file = st.sidebar.file_uploader("Upload GI Analysis Excel", type=["xls", "xlsx"])
view_option = st.sidebar.selectbox("Select View", ["Summary", "Detailed Analysis"])

# ===================== MOCK DATA =====================
# For now we just use mock data (replace later with Excel parsing)
df = pd.DataFrame({
    "GI_No": [101, 102, 103, 104, 105],
    "Volume": [230000, 180000, 310000, 275000, 199000],
    "Category": ["Nito", "Oxy", "Nito", "Oxy", "Nito"]
})

# ===================== SUMMARY METRICS =====================
st.title("📊 GI Analysis Dashboard")

col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("Total GIs", len(df))
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("Total Volume", f"{df['Volume'].sum():,}")
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric("Average Volume", f"{df['Volume'].mean():,.0f}")
    st.markdown('</div>', unsafe_allow_html=True)

# ===================== CHARTS =====================
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    fig1 = px.bar(
        df, x="GI_No", y="Volume", color="Category",
        title="Past 2 week orders",
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    st.plotly_chart(fig1, use_container_width=True)

with col_chart2:
    fig2 = px.pie(
        df, names="Category", values="Volume",
        title="Volume Share by Category",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    st.plotly_chart(fig2, use_container_width=True)

# ===================== TABLE =====================
st.subheader("📋 Detailed Data")
st.dataframe(df, use_container_width=True)

