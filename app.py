import streamlit as st
from postgrest import PostgrestClient
from datetime import datetime
import pandas as pd
import numpy as np
import altair as alt

# ========== CONFIG ==========
API_KEY = "vEtqk19OhIzbXrk0pabfyxq7WknP46PeLNDbGPTQlUIeoRYcTM7Bswgu14ObvYKg"
API_SECRET = "SZTzO0qUanD1mRv3bbKLVZRogeYJuIqjC1hxdW52cX6u8MoaemyTMuuiBx4XIamP"
SUPABASE_URL = "https://kfctwbonrbtgmyqlwwzm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtmY3R3Ym9ucmJ0Z215cWx3d3ptIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ2MzE0OTQsImV4cCI6MjA2MDIwNzQ5NH0.UazxhVhhWQ0YwmB36AY_PKPO_LSVoXwXYsKxTMj7U84"

TRADING_PAIRS = ["ETHUSDT", "BTCUSDT", "SOLUSDT", "LINKUSDT"]
TRADE_PERCENT = 0.25
LEVERAGE = 2
POLL_INTERVAL = 10

# ========== INIT ==========
st.set_page_config(layout="wide")
postgrest = PostgrestClient(f"{SUPABASE_URL}/rest/v1")
postgrest.auth(SUPABASE_KEY)

# ========== STATE MANAGEMENT ==========
def load_state():
    state = {}
    try:
        for key in ["capital", "positions", "log"]:
            res = postgrest.from_("bot_state").select("value").eq("key", key).execute()
            if res[1]:
                state[key] = res[1][0]["value"]
    except Exception as e:
        st.error(f"❌ Failed to load state: {e}")
    return state

def save_state(state):
    try:
        for key, value in state.items():
            postgrest.from_("bot_state").upsert({"key": key, "value": value}).execute()
    except Exception as e:
        st.error(f"❌ Failed to save state: {e}")

# ========== DEBUG LOGGING ==========
def log_debug(pair, signal, rsi, macd, macd_signal):
    try:
        postgrest.from_("debug_log").insert({
            "timestamp": datetime.utcnow().isoformat(),
            "pair": pair,
            "signal": signal,
            "rsi": rsi,
            "macd": macd,
            "macd_signal": macd_signal,
        }).execute()
    except Exception as e:
        st.warning(f"⚠️ Failed to insert debug log: {e}")

# ========== MAIN APP ==========
st.title("📊 Binance Paper Trading Bot")
st.sidebar.success("✅ Connected to Binance Testnet")
st.sidebar.write("Pairs:", TRADING_PAIRS)

# Initialize state if missing
if "capital" not in st.session_state:
    st.session_state.capital = 20000
    st.session_state.positions = {}
    st.session_state.log = []

# Load persisted state
loaded = load_state()
if loaded:
    st.session_state.capital = loaded.get("capital", st.session_state.capital)
    st.session_state.positions = loaded.get("positions", st.session_state.positions)
    st.session_state.log = loaded.get("log", st.session_state.log)

# Example signal evaluation (mock)
data = pd.DataFrame({
    "MACD": np.random.randn(30).cumsum(),
    "Signal": np.random.randn(30).cumsum(),
    "RSI": np.random.randint(40, 80, size=30)
})
latest = data.iloc[-1]
previous = data.iloc[-2]

if latest['MACD'] > latest['Signal'] and previous['MACD'] <= previous['Signal'] and latest['RSI'] > 55:
    st.success("📈 BUY signal")
    log_debug("ETHUSDT", "BUY", latest['RSI'], latest['MACD'], latest['Signal'])
elif latest['MACD'] < latest['Signal'] and previous['MACD'] >= previous['Signal'] and latest['RSI'] < 45:
    st.error("📉 SELL signal")
    log_debug("ETHUSDT", "SELL", latest['RSI'], latest['MACD'], latest['Signal'])
else:
    st.info("🤝 HOLD signal")
    log_debug("ETHUSDT", "HOLD", latest['RSI'], latest['MACD'], latest['Signal'])

# Show data
st.line_chart(data[["MACD", "Signal"]])
st.line_chart(data[["RSI"]])

# Save updated state
save_state({
    "capital": st.session_state.capital,
    "positions": st.session_state.positions,
    "log": st.session_state.log
})
