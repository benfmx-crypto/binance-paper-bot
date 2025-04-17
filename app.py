import streamlit as st
import pandas as pd
import numpy as np
from binance.client import Client
from postgrest import PostgrestClient
import datetime
import json

# ======================= CONFIG =======================
API_KEY = "vEtqk19OhIzbXrk0pabfyxq7WknP46PeLNDbGPTQlUIeoRYcTM7Bswgu14ObvYKg"
API_SECRET = "SZTzO0qUanD1mRv3bbKLVZRogeYJuIqjC1hxdW52cX6u8MoaemyTMuuiBx4XIamP"
SUPABASE_URL = "https://kfctwbonrbtgmyqlwwzm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtmY3R3Ym9ucmJ0Z215cWx3d3ptIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ2MzE0OTQsImV4cCI6MjA2MDIwNzQ5NH0.UazxhVhhWQ0YwmB36AY_PKPO_LSVoXwXYsKxTMj7U84"
TRADING_PAIRS = ["ETHUSDT", "BTCUSDT"]
TRADE_PERCENT = 0.25
LEVERAGE = 2

# ======================= INIT =======================
st.set_page_config(layout="wide")

# Binance Testnet client (ping disabled)
client = Client(API_KEY, API_SECRET, testnet=True)
client.API_URL = 'https://testnet.binance.vision/api'

# Supabase connection
postgrest = PostgrestClient(f"{SUPABASE_URL}/rest/v1")
postgrest.auth(SUPABASE_KEY)

# ======================= STATE LOADING =======================
def load_state():
    state = {}
    try:
        res = postgrest.from_("bot_state").select("key,value").execute()
        for row in res.json():
            state[row["key"]] = json.loads(row["value"])
    except Exception as e:
        st.error(f"❌ Failed to load state: {e}")
    return state

def save_state(state):
    try:
        for key, value in state.items():
            postgrest.from_("bot_state").upsert({"key": key, "value": json.dumps(value)}).execute()
    except Exception as e:
        st.error(f"❌ Failed to save state: {e}")

# ======================= INITIALIZE SESSION STATE =======================
if "initialized" not in st.session_state:
    db_state = load_state()
    st.session_state.capital = db_state.get("capital", 10000.0)
    st.session_state.positions = db_state.get("positions", {})
    st.session_state.log = db_state.get("log", [])
    st.session_state.pnl_log = db_state.get("pnl_log", [])
    st.session_state.initialized = True

# ======================= UI =======================
st.title("📈 Binance Testnet Trading Bot")

col1, col2, col3 = st.columns(3)
col1.metric("💼 Capital", f"${st.session_state.capital:,.2f}")
col2.metric("📊 Open Trades", len(st.session_state.positions))
col3.metric("📈 Total Trades", len(st.session_state.log))

st.subheader("📋 Trade Log")
log_df = pd.DataFrame(st.session_state.log)
if not log_df.empty:
    st.dataframe(log_df[::-1])
else:
    st.info("No trades logged yet.")

st.subheader("📉 P&L Over Time")
pnl_df = pd.DataFrame(st.session_state.pnl_log)
if not pnl_df.empty:
    pnl_df["time"] = pd.to_datetime(pnl_df["time"])
    st.line_chart(pnl_df.set_index("time")["pnl"])
else:
    st.info("No P&L data recorded yet.")

# ======================= MANUAL CONTROLS =======================
st.subheader("🔧 Controls")
if st.button("💾 Save State"):
    save_state({
        "capital": st.session_state.capital,
        "positions": st.session_state.positions,
        "log": st.session_state.log,
        "pnl_log": st.session_state.pnl_log
    })
    st.success("State saved to Supabase ✅")

if st.button("♻️ Reset State"):
    st.session_state.capital = 10000.0
    st.session_state.positions = {}
    st.session_state.log = []
    st.session_state.pnl_log = []
    save_state({
        "capital": 10000.0,
        "positions": {},
        "log": [],
        "pnl_log": []
    })
    st.warning("State reset.")
