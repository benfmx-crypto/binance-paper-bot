import streamlit as st
import pandas as pd
import numpy as np
import time
from binance.client import Client
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import altair as alt
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ======================= CONFIG =======================
API_KEY = 'vEtqk19OhIzbXrk0pabfyxq7WknP46PeLNDbGPTQlUIeoRYcTM7Bswgu14ObvYKg'
API_SECRET = 'SZTzO0qUanD1mRv3bbKLVZRogeYJuIqjC1hxdW52cX6u8MoaemyTMuuiBx4XIamP'
TRADING_PAIRS = ['ETHUSDT', 'BTCUSDT', 'SOLUSDT', 'LINKUSDT']
TRADE_PERCENT = 0.25
LEVERAGE = 2
POLL_INTERVAL = 10  # in seconds
SHEET_NAME = "streamlit-trading bot"

# ======================= INIT =======================
st.set_page_config(layout="wide")
st.title("📈 Binance Testnet Live Paper Trading Bot")

# Google Sheets auth
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
import json
creds_dict = json.loads(st.secrets["GOOGLE_SHEETS_CREDS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client_sheet = gspread.authorize(creds)
SHEET_ID = "19ndpYJi6GUfMnKU0xeXoCqJqUYZgGNPct5zU3F4kqqQ"
sheet = client_sheet.open_by_url(https://docs.google.com/spreadsheets/d/19ndpYJi6GUfMnKU0xeXoCqJqUYZgGNPct5zU3F4kqqQ/edit?gid=0#gid=0)


def read_sheet(tab):
    try:
        data = sheet.worksheet(tab).get_all_records()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

def write_sheet(tab, df):
    sheet_ = sheet.worksheet(tab)
    sheet_.clear()
    sheet_.update([df.columns.values.tolist()] + df.values.tolist())

# Binance API client
client = Client(API_KEY, API_SECRET, testnet=True)

st.sidebar.success("✅ Connected to Binance Testnet")
st.sidebar.write("Pairs:", TRADING_PAIRS)

# ======================= STATE SYNC FROM SHEET =======================
capital_df = read_sheet("capital")
st.session_state.capital = float(capital_df.iloc[0]["value"]) if not capital_df.empty else 5000

log_df = read_sheet("log")
st.session_state.log = log_df.to_dict("records") if not log_df.empty else []

positions_df = read_sheet("positions")
st.session_state.positions = {row['pair']: {"entry": float(row['entry']), "qty": float(row['qty'])} for _, row in positions_df.iterrows()} if not positions_df.empty else {}

if 'equity_log' not in st.session_state:
    st.session_state.equity_log = []
if 'pnl_log' not in st.session_state:
    st.session_state.pnl_log = []

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
        return 'HOLD'

    latest = df.iloc[-1]
    previous = df.iloc[-2]

    if latest['MACD'] > latest['Signal'] and previous['MACD'] <= previous['Signal'] and latest['RSI'] > 55:
        return 'BUY'
    elif latest['RSI'] > 70:
        return 'SELL'
    return 'HOLD'

# ======================= MAIN LOOP =======================
st.write("### Live Trades")
st_autorefresh(interval=POLL_INTERVAL * 1000, key="auto-refresh")

for pair in TRADING_PAIRS:
    ticker = client.futures_klines(symbol=pair, interval=Client.KLINE_INTERVAL_1MINUTE, limit=100)
    df = pd.DataFrame(ticker, columns=["time", "open", "high", "low", "close", "volume", "ct", "qav", "trades", "tbv", "tqav", "ignore"])
    df['close'] = df['close'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['volume'] = df['volume'].astype(float)
    df['time'] = pd.to_datetime(df['time'], unit='ms')
    df.dropna(inplace=True)

    if df.empty:
        st.warning(f"⚠️ Skipping {pair} due to insufficient data.")
        continue

    signal = generate_signal(df)
    price = df['close'].iloc[-1]
    capital = st.session_state.capital
    size = round((capital * TRADE_PERCENT * LEVERAGE) / price, 3)

    if signal == 'BUY' and pair not in st.session_state.positions:
        st.session_state.positions[pair] = {'entry': price, 'qty': size}
        st.session_state.capital -= capital * TRADE_PERCENT
        st.session_state.log.append({
            'pair': pair,
            'side': 'BUY',
            'price': price,
            'qty': size,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })

    elif signal == 'SELL' and pair in st.session_state.positions:
        entry = st.session_state.positions[pair]['entry']
        qty = st.session_state.positions[pair]['qty']
        pnl = (price - entry) * qty * LEVERAGE
        st.session_state.capital += (capital * TRADE_PERCENT) + pnl
        del st.session_state.positions[pair]
        st.session_state.log.append({
            'pair': pair,
            'side': 'SELL',
            'price': price,
            'qty': qty,
            'pnl': pnl,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        st.session_state.pnl_log.append({
            'time': datetime.now(),
            'pnl': pnl
        })

# Log current equity value
st.session_state.equity_log.append({
    'time': datetime.now(),
    'equity': st.session_state.capital
})

# ======================= WRITE BACK TO SHEETS =======================
write_sheet("capital", pd.DataFrame([{"value": st.session_state.capital}]))
write_sheet("log", pd.DataFrame(st.session_state.log))
if st.session_state.positions:
    pos_df = pd.DataFrame([{"pair": k, "entry": v["entry"], "qty": v["qty"]} for k, v in st.session_state.positions.items()])
    write_sheet("positions", pos_df)
else:
    write_sheet("positions", pd.DataFrame(columns=["pair", "entry", "qty"]))

# ======================= UI =======================
col1, col2, col3 = st.columns(3)
col1.metric("💼 Capital", f"${st.session_state.capital:,.2f}")
col2.metric("📊 Open Trades", len(st.session_state.positions))
col3.metric("📈 Total Trades", len(st.session_state.log))

st.write("### Trade Log")
log_df = pd.DataFrame(st.session_state.log)
st.dataframe(log_df.tail(20), use_container_width=True)

st.write("### 📊 Equity Over Time")
equity_df = pd.DataFrame(st.session_state.equity_log)
if not equity_df.empty:
    equity_chart = alt.Chart(equity_df).mark_line().encode(
        x='time:T',
        y='equity:Q'
    ).properties(height=300)
    st.altair_chart(equity_chart, use_container_width=True)

st.write("### 📉 PnL Per Trade")
pnl_df = pd.DataFrame(st.session_state.pnl_log)
if not pnl_df.empty:
    pnl_chart = alt.Chart(pnl_df).mark_bar().encode(
        x='time:T',
        y='pnl:Q',
        color=alt.condition("datum.pnl >= 0", alt.value("green"), alt.value("red"))
    ).properties(height=300)
    st.altair_chart(pnl_chart, use_container_width=True)

st.caption(f"🔁 Auto-refreshing every {POLL_INTERVAL} seconds.")
