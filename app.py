import streamlit as st
from binance.client import Client
from postgrest import PostgrestClient
import pandas as pd
import datetime

# ======================= CONFIG =======================
API_KEY = st.secrets["API_KEY"]
API_SECRET = st.secrets["API_SECRET"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
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
    st.session_state.positions = {}

# ======================= LOAD STATE FROM SUPABASE =======================
def load_state():
    try:
        response = postgrest.from_("bot_state").select("*").execute()
        for item in response:
            st.session_state[item["key"]] = item["value"]
        st.success("✅ State loaded from Supabase")
    except Exception as e:
        st.error(f"❌ Failed to load state: {e}")

load_state()

# ======================= UI =======================
st.title("📈 Binance Paper Trading Bot Dashboard")
st.write("Capital:", st.session_state.capital)

st.subheader("📋 Trade History")
if st.session_state.trades:
    df = pd.DataFrame(st.session_state.trades)
    st.dataframe(df)
else:
    st.info("No trades yet.")

# ======================= CONTROLS =======================
st.subheader("🛠 Simulate Trades")
if st.button("Simulate Buy ETH"):
    now = datetime.datetime.now().isoformat()
    st.session_state.trades.append({
        "pair": "ETHUSDT",
        "side": "BUY",
        "price": 3500,
        "qty": 0.5,
        "timestamp": now
    })
    st.success(f"Simulated BUY of ETH at 3500 on {now}")

# ======================= SAVE STATE TO SUPABASE =======================
def save_state():
    try:
        for key in ["capital", "trades", "positions"]:
            postgrest.from_("bot_state").upsert({"key": key, "value": st.session_state[key]}).execute()
        st.success("✅ State saved to Supabase")
    except Exception as e:
        st.error(f"❌ Failed to save state: {e}")

if st.button("💾 Save State"):
    save_state()

# ======================= Supabase Debug =======================
try:
    response = postgrest.from_("trades").select("*").execute()
    st.write("Supabase Trades:", response)
except Exception as e:
    st.warning(f"⚠️ Could not fetch trades from Supabase: {e}")
