import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from binance.client import Client
from postgrest import PostgrestClient

# ======================= CONFIG =======================
API_KEY = "vEtqk19OhIzbXrk0pabfyxq7WknP46PeLNDbGPTQlUIeoRYcTM7Bswgu14ObvYKg"
API_SECRET = "SZTzO0qUanD1mRv3bbKLVZRogeYJuIqjC1hxdW52cX6u8MoaemyTMuuiBx4XIamP"
SUPABASE_URL = "https://kfctwbonrbtgmyqlwwzm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtmY3R3Ym9ucmJ0Z215cWx3d3ptIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ2MzE0OTQsImV4cCI6MjA2MDIwNzQ5NH0.UazxhVhhWQ0YwmB36AY_PKPO_LSVoXwXYsKxTMj7U84"
TRADING_PAIRS = ["ETHUSDT", "BTCUSDT"]
INITIAL_CAPITAL = 10000

# ======================= INIT =======================
st.set_page_config(layout="wide")
client = Client(API_KEY, API_SECRET)
client.API_URL = 'https://testnet.binance.vision/api'
postgrest = PostgrestClient(f"{SUPABASE_URL}/rest/v1")
postgrest.auth(SUPABASE_KEY)

# ======================= SESSION STATE =======================
if "capital" not in st.session_state:
    st.session_state.capital = INITIAL_CAPITAL
    st.session_state.trades = []
    st.session_state.pnl_log = []
    st.session_state.positions = {}
    st.session_state.equity_log = []

# ======================= LOAD STATE =======================
def load_state():
    try:
        state = {}
        keys = ["capital", "trades", "pnl_log", "positions", "equity_log"]
        for key in keys:
            res = postgrest.from_("bot_state").select("value").eq("key", key).execute()
            state[key] = eval(res["data"][0]["value"])
        for k, v in state.items():
            st.session_state[k] = v
        st.success("✅ State loaded from Supabase")
    except Exception as e:
        st.error(f"❌ Failed to load state: {e}")

# ======================= SAVE STATE =======================
def save_state():
    try:
        for key in ["capital", "trades", "pnl_log", "positions", "equity_log"]:
            postgrest.from_("bot_state").upsert({"key": key, "value": str(st.session_state[key])}).execute()
        st.success("✅ State saved to Supabase")
    except Exception as e:
        st.error(f"❌ Failed to save state: {e}")

# ======================= UI =======================
st.title("📊 Binance Testnet Trading Bot")
load_state()

st.subheader("💼 Portfolio")
st.write(f"Capital: ${st.session_state.capital:,.2f}")

st.subheader("📈 Trades")
st.write(pd.DataFrame(st.session_state.trades))

st.subheader("📉 P&L Log")
pnl_df = pd.DataFrame(st.session_state.pnl_log)
if not pnl_df.empty:
    pnl_df["time"] = pd.to_datetime(pnl_df["time"])
    st.line_chart(pnl_df.set_index("time")["pnl"])
else:
    st.info("No P&L data recorded yet.")

if st.button("💾 Save State"):
    save_state()

if st.button("🔄 Reset State"):
    for key in ["capital", "trades", "pnl_log", "positions", "equity_log"]:
        st.session_state[key] = INITIAL_CAPITAL if key == "capital" else []
    st.success("🔁 State has been reset")