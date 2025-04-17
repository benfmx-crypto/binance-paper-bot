import streamlit as st
import pandas as pd
import numpy as np
from binance.client import Client
from postgrest import PostgrestClient
import datetime

# ======================= CONFIG =======================
API_KEY = "vEtqk19OhIzbXrk0pabfyxq7WknP46PeLNDbGPTQlUIeoRYcTM7Bswgu14ObvYKg"
API_SECRET = "SZTzO0qUanD1mRv3bbKLVZRogeYJuIqjC1hxdW52cX6u8MoaemyTMuuiBx4XIamP"
SUPABASE_URL = "https://kfctwbonrbtgmyqlwwzm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtmY3R3Ym9ucmJ0Z215cWx3d3ptIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ2MzE0OTQsImV4cCI6MjA2MDIwNzQ5NH0.UazxhVhhWQ0YwmB36AY_PKPO_LSVoXwXYsKxTMj7U84"
INITIAL_CAPITAL = 10000

# ======================= INIT =======================
st.set_page_config(layout="wide")
client = Client(API_KEY, API_SECRET, ping=False)
client.API_URL = 'https://testnet.binance.vision/api'
postgrest = PostgrestClient(f"{SUPABASE_URL}/rest/v1")
postgrest.auth(SUPABASE_KEY)

# ======================= SESSION STATE =======================
if "capital" not in st.session_state:
    st.session_state.capital = INITIAL_CAPITAL
    st.session_state.trades = []

# ======================= STATE LOAD =======================
def load_state():
    try:
        res = postgrest.from_("bot_state").select("*").execute()
        if res.status_code == 200:
            rows = res.json()
            if rows:
                state = rows[0]
                st.session_state.capital = float(state["capital"])
                st.session_state.trades = eval(state["trades"])
                st.success("✅ State loaded from Supabase")
            else:
                st.warning("⚠️ No state found in Supabase.")
        else:
            st.error(f"❌ Failed to load state: {res.text}")
    except Exception as e:
        st.error(f"❌ Failed to load state: {e}")

load_state()

# ======================= UI =======================
st.title("📈 Binance Paper Trading Bot (Testnet)")
st.metric("Capital", f"${st.session_state.capital:,.2f}")

st.subheader("📜 Trades")
if st.session_state.trades:
    df = pd.DataFrame(st.session_state.trades)
    st.dataframe(df)
else:
    st.info("No trades recorded yet.")

st.subheader("📊 Controls")
st.button("🔄 Refresh")

