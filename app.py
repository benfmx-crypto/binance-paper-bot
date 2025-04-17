import streamlit as st
import pandas as pd
import numpy as np
import datetime
from binance.client import Client
from postgrest import PostgrestClient

# ======================= CONFIG =======================
API_KEY = "vEtqk19OhIzbXrk0pabfyxq7WknP46PeLNDbGPTQlUIeoRYcTM7Bswgu14ObvYKg"
API_SECRET = "SZTzO0qUanD1mRv3bbKLVZRogeYJuIqjC1hxdW52cX6u8MoaemyTMuuiBx4XIamP"
SUPABASE_URL = "https://kfctwbonrbtgmyqlwwzm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtmY3R3Ym9ucmJ0Z215cWx3d3ptIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ2MzE0OTQsImV4cCI6MjA2MDIwNzQ5NH0.UazxhVhhWQ0YwmB36AY_PKPO_LSVoXwXYsKxTMj7U84"
INITIAL_CAPITAL = 10000
TRADING_PAIRS = ["ETHUSDT"]

# ======================= INIT =======================
st.set_page_config(layout="wide")
client = Client(API_KEY, API_SECRET, tld='com', testnet=True)
client.API_URL = 'https://testnet.binance.vision/api'
postgrest = PostgrestClient(f"{SUPABASE_URL}/rest/v1")
postgrest.auth(SUPABASE_KEY)

response = postgrest.from_("trades").select("*").order("timestamp", desc=True).limit(5).execute()
st.write("Supabase Trades:", response.json())


# ======================= SESSION STATE =======================
if "capital" not in st.session_state:
    st.session_state.capital = INITIAL_CAPITAL
    st.session_state.trades = []
    st.session_state.positions = {}

# ======================= LOAD STATE =======================
def load_state():
    try:
        res = postgrest.from_("bot_state").select("key,value").execute()
        data = res.json()
        for row in data:
            st.session_state[row["key"]] = float(row["value"])
        st.success("✅ State loaded from Supabase")
    except Exception as e:
        st.error(f"❌ Failed to load state: {e}")

# ======================= SAVE STATE =======================
def save_state():
    try:
        for key, value in st.session_state.items():
            if key in ["capital"]:
                postgrest.from_("bot_state").upsert({"key": key, "value": value}).execute()
        st.success("✅ State saved to Supabase")
    except Exception as e:
        st.error(f"❌ Failed to save state: {e}")

# ======================= DISPLAY UI =======================
st.title("📈 Binance Paper Trading Bot")
st.metric("💰 Capital", f"${st.session_state.capital:,.2f}")

# ======================= TRADE TABLE =======================
st.subheader("📋 Trade History")
if st.session_state.trades:
    st.dataframe(pd.DataFrame(st.session_state.trades))
else:
    st.info("No trades recorded yet.")

# ======================= P&L CHART =======================
st.subheader("📊 Profit & Loss")
if st.session_state.trades:
    pnl_df = pd.DataFrame(st.session_state.trades)
    pnl_df["time"] = pd.to_datetime(pnl_df["time"])
    st.line_chart(pnl_df.set_index("time")["pnl"])
else:
    st.info("No P&L data recorded yet.")

# ======================= CONTROLS =======================
st.subheader("⚙️ Controls")
col1, col2 = st.columns(2)
with col1:
    if st.button("💾 Save State"):
        save_state()
with col2:
    if st.button("🔁 Reload State"):
        load_state()

# ======================= LOGIC PLACEHOLDER =======================
# Add your strategy logic, signal generation, and trade execution below
# For now, we just simulate one trade
if st.button("▶️ Simulate Buy ETH"):
    entry_price = 3000
    qty = 0.1
    st.session_state.capital -= entry_price * qty
    st.session_state.trades.append({
        "pair": "ETHUSDT",
        "side": "BUY",
        "price": entry_price,
        "qty": qty,
        "pnl": np.random.uniform(-20, 50),
        "time": datetime.datetime.now()
    })
    st.success("Simulated ETH Buy Trade!")
st.write("Current Trades:", st.session_state.trades)


