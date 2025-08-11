import streamlit as st
import pandas as pd
import plotly.express as px
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


