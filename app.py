import streamlit as st
from binance.client import Client
from postgrest import PostgrestClient
import pandas as pd
import numpy as np
import datetime

# ======================= CONFIG =======================
API_KEY = "vEtqk19OhIzbXrk0pabfyxq7WknP46PeLNDbGPTQlUIeoRYcTM7Bswgu14ObvYKg"
API_SECRET = "SZTzO0qUanD1mRv3bbKLVZRogeYJuIqjC1hxdW52cX6u8MoaemyTMuuiBx4XIamP"
SUPABASE_URL = "https://kfctwbonrbtgmyqlwwzm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtmY3R3Ym9ucmJ0Z215cWx3d3ptIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ2MzE0OTQsImV4cCI6MjA2MDIwNzQ5NH0.UazxhVhhWQ0YwmB36AY_PKPO_LSVoXwXYsKxTMj7U84"
INITIAL_CAPITAL = float(st.secrets.get("INITIAL_CAPITAL", 10000))

# ======================= INIT =======================
st.set_page_config(layout="wide")
client = Client(API_KEY, API_SECRET, tld="com", testnet=True)
client.API_URL = 'https://testnet.binance.vision/api'
postgrest = PostgrestClient(f"{SUPABASE_URL}/rest/v1")
postgrest.auth(SUPABASE_KEY)

# ======================= SESSION STATE =======================
if "capital" not in st.session_state:
    st.session_state.capital = INITIAL_CAPITAL
    st.session_state.trades = []
    st.session_state.positions = {}

# ======================= SUPABASE STATE LOAD =======================
def load_state():
    try:
        response = postgrest.from_("bot_state").select("*").execute()
        result = response.json()
        for row in result:
            key = row["key"]
            value = row["value"]
            st.session_state[key] = value
        st.success("✅ State loaded from Supabase")
    except Exception as e:
        st.error(f"❌ Failed to load state: {e}")

load_state()

# ======================= UI =======================
st.title("🧠 ETH/AUD Trading Bot")
col1, col2 = st.columns(2)
col1.metric("Capital", f"${st.session_state.capital:,.2f}")
col2.metric("Open Trades", len(st.session_state.positions))

# P&L Table
if st.session_state.trades:
    pnl_df = pd.DataFrame(st.session_state.trades)
    pnl_df["time"] = pd.to_datetime(pnl_df["time"])
    st.line_chart(pnl_df.set_index("time")["pnl"])
else:
    st.info("No P&L data recorded yet.")

# ======================= MANUAL CONTROLS =======================
st.subheader("🔧 Controls")
col1, col2 = st.columns(2)

if col1.button("Simulate BUY ETH"):
    now = datetime.datetime.now(datetime.UTC).isoformat()
    price = 3000
    qty = 1
    st.session_state.positions["ETH"] = {"entry": price, "qty": qty, "side": "LONG"}
    st.session_state.capital -= price * qty
    st.session_state.trades.append({"time": now, "pair": "ETH", "side": "BUY", "price": price, "qty": qty, "pnl": 0})

if col2.button("Simulate SELL ETH"):
    if "ETH" in st.session_state.positions:
        now = datetime.datetime.now(datetime.UTC).isoformat()
        entry = st.session_state.positions["ETH"]["entry"]
        qty = st.session_state.positions["ETH"]["qty"]
        price = 3100
        pnl = (price - entry) * qty
        st.session_state.capital += price * qty
        st.session_state.trades.append({"time": now, "pair": "ETH", "side": "SELL", "price": price, "qty": qty, "pnl": pnl})
        del st.session_state.positions["ETH"]
