# Streamlit Trading Bot with Supabase (Async-compatible)

import streamlit as st
import pandas as pd
import numpy as np
import asyncio
from binance.client import Client
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import altair as alt
from supabase import create_client, Client as SupabaseClient

# ======================= CONFIG =======================
API_KEY = st.secrets["BINANCE_API"]
API_SECRET = st.secrets["BINANCE_SECRET"]
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

TRADING_PAIRS = ['ETHUSDT', 'BTCUSDT', 'SOLUSDT', 'LINKUSDT']
TRADE_PERCENT = 0.25
LEVERAGE = 2
POLL_INTERVAL = 10  # in seconds

# ======================= INIT =======================
st.set_page_config(layout="wide")
st.title("📈 Binance Testnet Live Paper Trading Bot")
client = Client(API_KEY, API_SECRET, testnet=True)
supabase: SupabaseClient = create_client(SUPABASE_URL, SUPABASE_KEY)

st.sidebar.success("✅ Connected to Binance Testnet")
st.sidebar.write("Pairs:", TRADING_PAIRS)

# ======================= ASYNC HELPERS =======================
async def save_debug(pair, price, macd, signal, rsi):
    try:
        await supabase.table("debug_log").insert({
            "pair": pair,
            "price": price,
            "macd": macd,
            "signal": signal,
            "rsi": rsi,
            "time": datetime.utcnow().isoformat()
        }).execute()
    except Exception as e:
        st.warning(f"⚠️ Failed to insert debug log: {e}")

async def save_state_to_supabase(state):
    try:
        for key, value in state.items():
            await supabase.table("bot_state").upsert({"key": key, "value": value}).execute()
    except Exception as e:
        st.error(f"❌ Failed to save state to Supabase: {e}")

async def load_state():
    state = {}
    try:
        for key in ["capital", "log", "positions", "equity_log", "pnl_log"]:
            res = await supabase.table("bot_state").select("value").eq("key", key).execute()
            if res.data:
                state[key] = res.data[0]["value"]
    except Exception as e:
        st.warning(f"⚠️ Failed to load state from Supabase: {e}")
    return state

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

# ======================= MAIN =======================
async def run_bot():
    # Load previous state from Supabase
    state = await load_state()
    st.session_state.capital = state.get("capital", 5000)
    st.session_state.log = state.get("log", [])
    st.session_state.positions = state.get("positions", {})
    st.session_state.equity_log = state.get("equity_log", [])
    st.session_state.pnl_log = state.get("pnl_log", [])

    # Display UI
    st.write("### Live Trades")
    st_autorefresh(interval=POLL_INTERVAL * 1000, key="auto-refresh")

    for pair in TRADING_PAIRS:
        ticker = client.futures_klines(symbol=pair, interval=Client.KLINE_INTERVAL_1MINUTE, limit=100)
        df = pd.DataFrame(ticker, columns=["time", "open", "high", "low", "close", "volume", "ct", "qav", "trades", "tbv", "tqav", "ignore"])
        df['close'] = df['close'].astype(float)
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        df.dropna(inplace=True)

        if df.empty:
            st.warning(f"⚠️ Skipping {pair} due to insufficient data.")
            continue

        signal, df = generate_signal(df)
        price = df['close'].iloc[-1]
        capital = st.session_state.capital
        size = round((capital * TRADE_PERCENT * LEVERAGE) / price, 3)

        await save_debug(pair, price, df['MACD'].iloc[-1], df['Signal'].iloc[-1], df['RSI'].iloc[-1])

        if signal == 'BUY' and pair not in st.session_state.positions:
            st.session_state.positions[pair] = {'entry': price, 'qty': size, 'side': 'LONG'}
            st.session_state.capital -= capital * TRADE_PERCENT
            st.session_state.log.append({
                'pair': pair, 'side': 'BUY', 'price': price, 'qty': size,
                'value': capital * TRADE_PERCENT, 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

        elif signal == 'SHORT' and pair not in st.session_state.positions:
            st.session_state.positions[pair] = {'entry': price, 'qty': size, 'side': 'SHORT'}
            st.session_state.capital -= capital * TRADE_PERCENT
            st.session_state.log.append({
                'pair': pair, 'side': 'SHORT', 'price': price, 'qty': size,
                'value': capital * TRADE_PERCENT, 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })

        elif signal == 'EXIT' and pair in st.session_state.positions:
            entry = st.session_state.positions[pair]['entry']
            qty = st.session_state.positions[pair]['qty']
            side = st.session_state.positions[pair]['side']
            pnl = (price - entry) * qty * LEVERAGE if side == 'LONG' else (entry - price) * qty * LEVERAGE
            st.session_state.capital += (capital * TRADE_PERCENT) + pnl
            del st.session_state.positions[pair]
            st.session_state.log.append({
                'pair': pair, 'side': 'EXIT', 'price': price, 'qty': qty, 'pnl': pnl,
                'value': capital * TRADE_PERCENT, 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            st.session_state.pnl_log.append({'time': datetime.now(), 'pnl': pnl})

    # Log equity
    st.session_state.equity_log.append({'time': datetime.now(), 'equity': st.session_state.capital})

    # Save state
    await save_state_to_supabase({
        "capital": st.session_state.capital,
        "log": st.session_state.log,
        "positions": st.session_state.positions,
        "equity_log": st.session_state.equity_log,
        "pnl_log": st.session_state.pnl_log
    })

    # ======================= UI =======================
    col1, col2, col3 = st.columns(3)
    col1.metric("💼 Capital", f"${st.session_state.capital:,.2f}")
    col2.metric("📊 Open Trades", len(st.session_state.positions))
    col3.metric("📈 Total Trades", len(st.session_state.log))

    st.write("### Trade Log")
    log_df = pd.DataFrame(st.session_state.log)
    st.dataframe(log_df.tail(20), use_container_width=True)

    st.write("### 📈 Equity Over Time")
    equity_df = pd.DataFrame(st.session_state.equity_log)
    if not equity_df.empty:
        chart = alt.Chart(equity_df).mark_line().encode(x='time:T', y='equity:Q').properties(height=300)
        st.altair_chart(chart, use_container_width=True)

    st.write("### 📉 PnL Per Trade (USDT)")
    pnl_df = pd.DataFrame(st.session_state.pnl_log)
    if not pnl_df.empty:
        pnl_chart = alt.Chart(pnl_df).mark_bar().encode(
            x='time:T', y='pnl:Q',
            color=alt.condition("datum.pnl >= 0", alt.value("green"), alt.value("red"))
        ).properties(height=300)
        st.altair_chart(pnl_chart, use_container_width=True)

    st.caption(f"🔁 Auto-refreshing every {POLL_INTERVAL} seconds.")

# ======================= RUN APP =======================
asyncio.run(run_bot())