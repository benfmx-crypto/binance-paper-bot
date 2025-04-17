import streamlit as st
from binance.client import Client
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from streamlit_autorefresh import st_autorefresh
import altair as alt
from postgrest import PostgrestClient
import json

# ======================= CONFIG =======================
API_KEY = "vEtqk19OhIzbXrk0pabfyxq7WknP46PeLNDbGPTQlUIeoRYcTM7Bswgu14ObvYKg"
API_SECRET = "SZTzO0qUanD1mRv3bbKLVZRogeYJuIqjC1hxdW52cX6u8MoaemyTMuuiBx4XIamP"
SUPABASE_URL = "https://kfctwbonrbtgmyqlwwzm.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtmY3R3Ym9ucmJ0Z215cWx3d3ptIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ2MzE0OTQsImV4cCI6MjA2MDIwNzQ5NH0.UazxhVhhWQ0YwmB36AY_PKPO_LSVoXwXYsKxTMj7U84"
TRADING_PAIRS = ["ETHUSDT", "BTCUSDT", "SOLUSDT", "LINKUSDT"]
TRADE_PERCENT = 0.25
LEVERAGE = 2
POLL_INTERVAL = 10

# ======================= INIT =======================
st.set_page_config(layout="wide")
client = Client(API_KEY, API_SECRET)
postgrest = PostgrestClient(f"{SUPABASE_URL}/rest/v1")
postgrest.auth(SUPABASE_KEY)

st.sidebar.success("✅ Connected to Binance Testnet")
st.sidebar.write("Pairs:", TRADING_PAIRS)

# ======================= STATE =======================
def load_state():
    state = {}
    try:
        for key in ["capital", "positions", "log", "equity_log", "pnl_log"]:
            res = postgrest.from_("bot_state").select("value").eq("key", key).execute()
            state[key] = json.loads(res.json()[0]['value']) if res.json() else None
    except Exception as e:
        st.error(f"❌ Failed to load state: {e}")
    return state

def save_state(state):
    try:
        for key, value in state.items():
            postgrest.from_("bot_state").upsert({"key": key, "value": json.dumps(value)}).execute()
    except Exception as e:
        st.error(f"❌ Failed to save state to Supabase: {e}")

def log_debug(pair, signal, rsi, macd, macd_signal):
    try:
        postgrest.from_("debug_log").insert({
            "time": datetime.now(timezone.utc).isoformat(),
            "pair": pair,
            "signal": signal,
            "rsi": rsi,
            "macd": macd,
            "macd_signal": macd_signal,
        }).execute()
    except Exception as e:
        st.warning(f"⚠️ Failed to insert debug log: {e}")

# ======================= STRATEGY =======================
def generate_signal(df):
    df['EMA12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['RSI'] = compute_rsi(df['close'], 14)
    df.dropna(inplace=True)
    return df

def compute_rsi(series, period):
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=period).mean()
    avg_loss = pd.Series(loss).rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# ======================= MAIN =======================
state = load_state()
if not state.get("capital"):
    st.session_state.capital = 10000
    st.session_state.positions = {}
    st.session_state.log = []
    st.session_state.pnl_log = []
    st.session_state.equity_log = []
else:
    st.session_state.capital = state['capital']
    st.session_state.positions = state['positions'] or {}
    st.session_state.log = state['log'] or []
    st.session_state.pnl_log = state['pnl_log'] or []
    st.session_state.equity_log = state['equity_log'] or []

col1, col2, col3 = st.columns(3)
col1.metric("💼 Capital", f"${st.session_state.capital:,.2f}")
col2.metric("📊 Open Trades", len(st.session_state.positions))
col3.metric("📈 Total Trades", len(st.session_state.log))

for pair in TRADING_PAIRS:
    klines = client.get_klines(symbol=pair, interval=Client.KLINE_INTERVAL_15MINUTE, limit=100)
    df = pd.DataFrame(klines, columns=["time", "open", "high", "low", "close", "volume", "close_time",
                                       "quote_asset_volume", "num_trades", "taker_buy_base",
                                       "taker_buy_quote", "ignore"])
    df['close'] = df['close'].astype(float)
    df = generate_signal(df)

    latest = df.iloc[-1]
    previous = df.iloc[-2]

    signal = "HOLD"
    if latest['MACD'] > latest['Signal'] and previous['MACD'] <= previous['Signal'] and latest['RSI'] > 55:
        signal = "BUY"
    elif latest['MACD'] < latest['Signal'] and previous['MACD'] >= previous['Signal'] and latest['RSI'] < 45:
        signal = "SELL"

    log_debug(pair, signal, latest['RSI'], latest['MACD'], latest['Signal'])

    price = latest['close']
    capital = st.session_state.capital

    if signal == "BUY" and pair not in st.session_state.positions:
        size = round((capital * TRADE_PERCENT * LEVERAGE) / price, 5)
        st.session_state.positions[pair] = {'entry': price, 'qty': size, 'side': 'LONG'}
    elif signal == "SELL" and pair in st.session_state.positions:
        entry = st.session_state.positions[pair]['entry']
        qty = st.session_state.positions[pair]['qty']
        pnl = (price - entry) * qty * LEVERAGE
        st.session_state.capital += pnl
        st.session_state.log.append({
            'pair': pair, 'side': 'EXIT', 'price': price, 'qty': qty, 'pnl': pnl,
            'time': datetime.now(timezone.utc).isoformat()
        })
        st.session_state.pnl_log.append({'time': datetime.now(timezone.utc).isoformat(), 'pnl': pnl})
        del st.session_state.positions[pair]

st.session_state.equity_log.append({
    'time': datetime.now(timezone.utc).isoformat(),
    'equity': st.session_state.capital + sum([
        (df.iloc[-1]['close'] - pos['entry']) * pos['qty'] * LEVERAGE
        for pair, pos in st.session_state.positions.items()
    ])
})

save_state({
    "capital": st.session_state.capital,
    "positions": st.session_state.positions,
    "log": st.session_state.log,
    "pnl_log": st.session_state.pnl_log,
    "equity_log": st.session_state.equity_log,
})

st.subheader("📜 Trade Log")
st.dataframe(pd.DataFrame(st.session_state.log))

st.subheader("📈 Equity Over Time")
if st.session_state.equity_log:
    chart_df = pd.DataFrame(st.session_state.equity_log)
    st.line_chart(chart_df.set_index("time"))

