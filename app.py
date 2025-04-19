import streamlit as st
from binance.client import Client
from postgrest import PostgrestClient
import pandas as pd
import numpy as np
import datetime
import os

# ======================= CONFIG =======================
API_KEY = os.environ["API_KEY"]
API_SECRET = os.environ["API_SECRET"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
INITIAL_CAPITAL = float(os.environ.get("INITIAL_CAPITAL", 10000))
# ======================= INIT =======================
st.set_page_config(layout="wide")
client = Client(API_KEY, API_SECRET, tld="com", testnet=True)
client.API_URL = 'https://testnet.binance.vision/api'
postgrest = PostgrestClient(f"{SUPABASE_URL}/rest/v1")
postgrest.auth(SUPABASE_KEY)

try:
    response = postgrest.from_("bot_state").insert([{"key": "test_key", "value": "test_value"}]).execute()
    st.success("✅ Test insert succeeded")
    st.json(response.data)  # ✅ Correct: use .data not .json()
except Exception as e:
    st.error(f"❌ Test insert failed: {e}")

# ======================= SESSION STATE =======================
if "capital" not in st.session_state:
    st.session_state.capital = INITIAL_CAPITAL
    st.session_state.trades = []
    st.session_state.positions = {}

# ======================= SUPABASE STATE LOAD =======================
def load_state():
    try:
        response = postgrest.from_("bot_state").select("*").execute()
        data = response.data
        if isinstance(data, list):
            for row in data:
                key = row["key"]
                value = row["value"]
                st.session_state[key] = value
            st.success("✅ State loaded from Supabase")
        else:
            st.error(f"❌ Unexpected data format: {data}")
    except Exception as e:
        st.error(f"❌ Failed to load state: {e}")

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