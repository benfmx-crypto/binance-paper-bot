# Streamlit Trading Bot with Supabase (sync PostgrestClient)

import streamlit as st
import pandas as pd
import numpy as np
from binance.client import Client
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import altair as alt
from postgrest import PostgrestClient
import json

# ======================= CONFIG =======================
API_KEY = 'vEtqk19OhIzbXrk0pabfyxq7WknP46PeLNDbGPTQlUIeoRYcTM7Bswgu14ObvYKg'
API_SECRET = 'SZTzO0qUanD1mRv3bbKLVZRogeYJuIqjC1hxdW52cX6u8MoaemyTMuuiBx4XIamP'
SUPABASE_URL = 'https://kfctwbonrbtgmyqlwwzm.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtmY3R3Ym9ucmJ0Z215cWx3d3ptIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NDYzMTQ5NCwiZXhwIjoyMDYwMjA3NDk0fQ.teYEmFIPp1hT7lxwWZ1jDwNxR5fA4ErfM2nBvHONrA0'

TRADING_PAIRS = ["ETHUSDT", "BTCUSDT", "SOLUSDT", "LINKUSDT"]
TRADE_PERCENT = 0.25
LEVERAGE = 2
POLL_INTERVAL = 10  # seconds

# ======================= INIT =======================
st.set_page_config(layout="wide")
st.title("📈 Binance Testnet Live Paper Trading Bot")
client = Client(API_KEY, API_SECRET, testnet=True)

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}
postgrest = PostgrestClient(f"{SUPABASE_URL}/rest/v1", headers=headers)

st.sidebar.success("✅ Connected to Binance Testnet")
st.sidebar.write("Pairs:", TRADING_PAIRS)

# ======================= SUPABASE =======================
def load_state():
    state = {}
    try:
        for key in ["capital", "log", "positions", "equity_log", "pnl_log"]:
            res = postgrest.from_("bot_state").select("value").eq("key", key).execute()
            if res and res.data:
                state[key] = json.loads(res.data[0]["value"])
    except Exception as e:
        st.error(f"❌ Failed to load state: {e}")
    return state

def save_state(state):
    try:
        for key, value in state.items():
            postgrest.from_("bot_state").upsert({"key": key, "value": json.dumps(value)}).execute()
    except Exception as e:
        st.error(f"❌ Failed to save state: {e}")

def log_debug(pair, signal, rsi, macd, macd_signal):
    try:
        postgrest.from_("debug_log").insert({
            "timestamp": datetime.utcnow().isoformat(),
            "pair": pair,
            "signal": signal,
            "rsi": rsi,
            "macd": macd,
            "macd_signal": macd_signal
        }).execute()
    except Exception as e:
        st.warning(f"⚠️ Debug log insert failed: {e}")

# ======================= LOAD SESSION =======================
state = load_state()
st.session_state.capital = state.get("capital", 5000)
st.session_state.log = state.get("log", [])
st.session_state.positions = state.get("positions", {})
st.session_state.equity_log = state.get("equity_log", [])
st.session_state.pnl_log = state.get("pnl_log", [])

# ======================= STRATEGY =======================
def generate_signal(df):
    df['EMA12'] = df['close'].ewm(span=12).mean()
    df['EMA26'] = df['close'].ewm(span=26).mean()
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal'] = df['MACD'].ewm(span=9).mean()
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df.dropna(inplace=True)

    if len(df) < 2:
        return 'HOLD', df

    latest = df.iloc[-1]
    previous = df.iloc[-2]

    if latest['MACD'] > latest['Signal'] and previous['MACD'] <= previous['Signal'] and latest['RSI'] > 55:
        return 'BUY', df
    elif latest['MACD'] < latest['Signal'] and previous['MACD'] >= previous['Signal'] and latest['RSI'] < 45:
        return 'SHORT', df
    elif latest['RSI'] > 70 or latest['RSI'] < 30:
        return 'EXIT', df
    return 'HOLD', df

# ======================= MAIN LOOP =======================
st.write("### Live Trades")
st_autorefresh(interval=POLL_INTERVAL * 1000, key="refresh")

for pair in TRADING_PAIRS:
    ticker = client.futures_klines(symbol=pair, interval=Client.KLINE_INTERVAL_1MINUTE, limit=100)
    df = pd.DataFrame(ticker, columns=["time", "open", "high", "low", "close", "volume", "ct", "qav", "trades", "tbv", "tqav", "ignore"])
    df['close'] = df['close'].astype(float)
    df['time'] = pd.to_datetime(df['time'], unit='ms')

    signal, df = generate_signal(df)
    price = df['close'].iloc[-1]
    macd, macd_signal, rsi = df['MACD'].iloc[-1], df['Signal'].iloc[-1], df['RSI'].iloc[-1]
    log_debug(pair, signal, rsi, macd, macd_signal)

    capital = st.session_state.capital
    size = round((capital * TRADE_PERCENT * LEVERAGE) / price, 3)

    if signal == 'BUY' and pair not in st.session_state.positions:
        st.session_state.positions[pair] = {'entry': price, 'qty': size, 'side': 'LONG'}
        st.session_state.capital -= capital * TRADE_PERCENT
        st.session_state.log.append({"pair": pair, "side": "BUY", "price": price, "qty": size, "time": datetime.utcnow().isoformat()})

    elif signal == 'SHORT' and pair not in st.session_state.positions:
        st.session_state.positions[pair] = {'entry': price, 'qty': size, 'side': 'SHORT'}
        st.session_state.capital -= capital * TRADE_PERCENT
        st.session_state.log.append({"pair": pair, "side": "SHORT", "price": price, "qty": size, "time": datetime.utcnow().isoformat()})

    elif signal == 'EXIT' and pair in st.session_state.positions:
        entry = st.session_state.positions[pair]['entry']
        qty = st.session_state.positions[pair]['qty']
        side = st.session_state.positions[pair]['side']
        pnl = (price - entry) * qty * LEVERAGE if side == 'LONG' else (entry - price) * qty * LEVERAGE
        st.session_state.capital += capital * TRADE_PERCENT + pnl
        del st.session_state.positions[pair]
        st.session_state.log.append({"pair": pair, "side": "EXIT", "price": price, "qty": qty, "pnl": pnl, "time": datetime.utcnow().isoformat()})
        st.session_state.pnl_log.append({"time": datetime.utcnow().isoformat(), "pnl": pnl})

st.session_state.equity_log.append({"time": datetime.utcnow().isoformat(), "equity": st.session_state.capital})
save_state({
    "capital": st.session_state.capital,
    "log": st.session_state.log,
    "positions": st.session_state.positions,
    "equity_log": st.session_state.equity_log,
    "pnl_log": st.session_state.pnl_log
})

# ======================= UI =======================
col1, col2, col3 = st.columns(3)
col1.metric("Capital", f"${st.session_state.capital:,.2f}")
col2.metric("Open Trades", len(st.session_state.positions))
col3.metric("Total Trades", len(st.session_state.log))

st.write("### Trade Log")
if st.session_state.log:
    st.dataframe(pd.DataFrame(st.session_state.log).tail(20), use_container_width=True)

st.write("### Equity Over Time")
if st.session_state.equity_log:
    equity_df = pd.DataFrame(st.session_state.equity_log)
    st.altair_chart(alt.Chart(equity_df).mark_line().encode(x='time:T', y='equity:Q'), use_container_width=True)

st.write("### PnL Per Trade")
if st.session_state.pnl_log:
    pnl_df = pd.DataFrame(st.session_state.pnl_log)
    st.altair_chart(
        alt.Chart(pnl_df).mark_bar().encode(
            x='time:T',
            y='pnl:Q',
            color=alt.condition("datum.pnl >= 0", alt.value("green"), alt.value("red"))
        ),
        use_container_width=True
    )

st.caption(f"🔁 Auto-refreshing every {POLL_INTERVAL} seconds")
