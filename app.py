import streamlit as st
from binance.client import Client
from postgrest import PostgrestClient
import pandas as pd
from datetime import datetime

# ======================= CONFIG =======================
API_KEY = "vEtqk19OhIzbXrk0pabfyxq7WknP46PeLNDbGPTQlUIeoRYcTM7Bswgu14ObvYKg"
API_SECRET = "SZTzO0qUanD1mRv3bbKLVZRogeYJuIqjC1hxdW52cX6u8MoaemyTMuuiBx4XIamP"
SUPABASE_URL = "https://kfctwbonrbtgmyqlwwzm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtmY3R3Ym9ucmJ0Z215cWx3d3ptIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ2MzE0OTQsImV4cCI6MjA2MDIwNzQ5NH0.UazxhVhhWQ0YwmB36AY_PKPO_LSVoXwXYsKxTMj7U84"

# ======================= INIT =======================
st.set_page_config(layout="wide")
client = Client(API_KEY, API_SECRET)
postgrest = PostgrestClient(f"{SUPABASE_URL}/rest/v1")
postgrest.auth(SUPABASE_KEY)

# ======================= Load State =======================
def load_state():
    state = {}
    try:
        keys = ["capital", "positions", "log", "pnl_log", "equity_log"]
        for key in keys:
            res = postgrest.from_("bot_state").select("value").eq("key", key).execute()
            if res.status_code == 200 and res.json():
                state[key] = res.json()[0]["value"]
            else:
                state[key] = {} if key != "capital" else 10000.0
    except Exception as e:
        st.error(f"❌ Failed to load state: {e}")
    return state

state = load_state()

# ======================= Init Session State =======================
if "capital" not in st.session_state:
    st.session_state.capital = float(state.get("capital", 10000.0))
    st.session_state.positions = state.get("positions", {})
    st.session_state.log = state.get("log", [])
    st.session_state.pnl_log = state.get("pnl_log", [])
    st.session_state.equity_log = state.get("equity_log", [])

# ======================= UI =======================
st.title("📊 Binance Paper Trading Bot")
col1, col2, col3 = st.columns(3)
col1.metric("💼 Capital", f"${st.session_state.capital:,.2f}")
col2.metric("📂 Open Trades", len(st.session_state.positions))
col3.metric("📈 Total Trades", len(st.session_state.log))

st.subheader("🔄 Open Positions")
if st.session_state.positions:
    open_trades_df = pd.DataFrame.from_dict(st.session_state.positions, orient="index")
    st.dataframe(open_trades_df)
else:
    st.write("No open trades.")

st.subheader("📋 Trade Log")
if st.session_state.log:
    st.dataframe(pd.DataFrame(st.session_state.log))
else:
    st.write("No trades logged yet.")

st.subheader("📊 PnL History")
if st.session_state.pnl_log:
    pnl_df = pd.DataFrame(st.session_state.pnl_log)
    pnl_df["time"] = pd.to_datetime(pnl_df["time"])
    st.line_chart(pnl_df.set_index("time")["pnl"])
else:
    st.write("No PnL history.")
