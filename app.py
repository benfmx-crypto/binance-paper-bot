import streamlit as st
import pandas as pd
import numpy as np
from binance.client import Client
from postgrest import PostgrestClient
import json
from datetime import datetime

# ======================= CONFIG =======================
API_KEY = "vEtqk19OhIzbXrk0pabfyxq7WknP46PeLNDbGPTQlUIeoRYcTM7Bswgu14ObvYKg"
API_SECRET = "SZTzO0qUanD1mRv3bbKLVZRogeYJuIqjC1hxdW52cX6u8MoaemyTMuuiBx4XIamP"
SUPABASE_URL = "https://kfctwbonrbtgmyqlwwzm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtmY3R3Ym9ucmJ0Z215cWx3d3ptIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ2MzE0OTQsImV4cCI6MjA2MDIwNzQ5NH0.UazxhVhhWQ0YwmB36AY_PKPO_LSVoXwXYsKxTMj7U84"

TRADING_PAIRS = ["ETHUSDT"]
TRADE_PERCENT = 0.25
LEVERAGE = 2
POLL_INTERVAL = 10

# ======================= INIT =======================
st.set_page_config(layout="wide")

client = Client(API_KEY, API_SECRET, ping=False)
client.API_URL = 'https://testnet.binance.vision/api'


postgrest = PostgrestClient(f"{SUPABASE_URL}/rest/v1")
postgrest.auth(SUPABASE_KEY)

# ======================= STATE =======================
def load_state():
    try:
        state = {}
        keys = ["capital", "trades", "equity_log", "pnl_log", "positions"]
        for key in keys:
            res = postgrest.from_("bot_state").select("value").eq("key", key).execute()
            if res.data:
                state[key] = json.loads(res.data[0]["value"])
        st.success("✅ State loaded from Supabase")
        return state
    except Exception as e:
        st.error(f"❌ Failed to load state: {e}")
        return {}

if "capital" not in st.session_state:
    db_state = load_state()
    for key, value in db_state.items():
        st.session_state[key] = value

# Initialize empty state if it doesn't exist
if "capital" not in st.session_state:
    st.session_state.capital = 10000
if "trades" not in st.session_state:
    st.session_state.trades = []
if "equity_log" not in st.session_state:
    st.session_state.equity_log = []
if "pnl_log" not in st.session_state:
    st.session_state.pnl_log = []
if "positions" not in st.session_state:
    st.session_state.positions = {}

# ======================= UI =======================
st.title("📈 Binance Testnet Trading Bot")
st.sidebar.success("✅ Connected to Binance Testnet")
st.sidebar.write("Trading Pairs:", TRADING_PAIRS)

# Show capital and equity
st.metric("💰 Capital", f"${st.session_state.capital:,.2f}")

# Show trade history
st.subheader("📊 Trade History")
if st.session_state.trades:
    st.dataframe(pd.DataFrame(st.session_state.trades))
else:
    st.info("No trades recorded yet.")

# Show equity log chart
st.subheader("📉 Equity Over Time")
if st.session_state.pnl_log:
    pnl_df = pd.DataFrame(st.session_state.pnl_log)
    pnl_df["time"] = pd.to_datetime(pnl_df["time"])
    st.line_chart(pnl_df.set_index("time")["pnl"])
else:
    st.info("No P&L data recorded yet.")

# ======================= CONTROLS =======================
st.subheader("⚙️ Controls")
st.button("🔁 Refresh")
st.button("🧹 Reset State")
