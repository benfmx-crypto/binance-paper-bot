import streamlit as st
import pandas as pd
import numpy as np
import datetime
from binance.client import Client
from postgrest import PostgrestClient
import json

# ========== CONFIG ==========
API_KEY = "vEtqk19OhIzbXrk0pabfyxq7WknP46PeLNDbGPTQlUIeoRYcTM7Bswgu14ObvYKg"
API_SECRET = "SZTzO0qUanD1mRv3bbKLVZRogeYJuIqjC1hxdW52cX6u8MoaemyTMuuiBx4XIamP"
SUPABASE_URL = "https://kfctwbonrbtgmyqlwwzm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtmY3R3Ym9ucmJ0Z215cWx3d3ptIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ2MzE0OTQsImV4cCI6MjA2MDIwNzQ5NH0.UazxhVhhWQ0YwmB36AY_PKPO_LSVoXwXYsKxTMj7U84"
BINANCE_TESTNET_BASE_URL = "https://testnet.binance.vision/api"
TRADING_PAIRS = ["ETHUSDT", "BTCUSDT"]
DEFAULT_CAPITAL = 10000

# ======================= INIT SESSION STATE =======================
for key, default in {
    "capital": 10000,
    "positions": {},
    "trades": [],
    "pnl_log": [],
    "equity_log": []
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ========== INIT ==========
st.set_page_config(layout="wide")
client = Client(API_KEY, API_SECRET, testnet=True)
client.API_URL = BINANCE_TESTNET_BASE_URL

postgrest = PostgrestClient(f"{SUPABASE_URL}/rest/v1")
postgrest.auth(SUPABASE_KEY)

# ========== STATE FUNCTIONS ==========
def load_state():
    state = {}
    try:
        for key in ["capital", "positions", "trades", "pnl_log", "equity_log"]:
            res = postgrest.from_("bot_state").select("value").eq("key", key).execute()
            data = json.loads(res[1].json()["data"][0]["value"])
            state[key] = data
        st.success("✅ State loaded from Supabase")
    except Exception as e:
        st.error(f"❌ Failed to load state: {e}")
    return state

def save_state(state):
    try:
        for key, value in state.items():
            postgrest.from_("bot_state").upsert({"key": key, "value": json.dumps(value)}).execute()
        st.success("✅ State saved to Supabase")
    except Exception as e:
        st.error(f"❌ Failed to save state: {e}")

def reset_state():
    return {
        "capital": DEFAULT_CAPITAL,
        "positions": {},
        "trades": [],
        "pnl_log": [],
        "equity_log": [],
    }

# ========== MAIN UI ==========
if "initialized" not in st.session_state:
    st.session_state.update(reset_state())
    db_state = load_state()
    if db_state:
        st.session_state.update(db_state)
    st.session_state.initialized = True

st.title("📈 Binance Paper Trading Bot (Testnet)")

col1, col2 = st.columns(2)
col1.metric("💰 Capital", f"${st.session_state.capital:,.2f}")
col2.metric("📊 Open Positions", len(st.session_state.positions))

st.subheader("📂 Open Positions")
if st.session_state.positions:
    st.dataframe(pd.DataFrame.from_dict(st.session_state.positions, orient="index"))
else:
    st.info("No open positions.")

st.subheader("📜 Trade Log")
if st.session_state.trades:
    st.dataframe(pd.DataFrame(st.session_state.trades))
else:
    st.info("No trades yet.")

st.subheader("📈 Equity Over Time")
if st.session_state.equity_log:
    df_eq = pd.DataFrame(st.session_state.equity_log)
    df_eq["time"] = pd.to_datetime(df_eq["time"])
    st.line_chart(df_eq.set_index("time")[["equity"]])
else:
    st.info("No equity data yet.")

st.sidebar.button("💾 Save State", on_click=lambda: save_state(st.session_state))
st.sidebar.button("🔁 Reset State", on_click=lambda: st.session_state.update(reset_state()))