import time
import pandas as pd
from binance.client import Client
from postgrest import PostgrestClient
import datetime

# =================== CONFIG ===================
API_KEY = "YOUR_API_KEY"
API_SECRET = "YOUR_API_SECRET"
SUPABASE_URL = "https://your.supabase.url"
SUPABASE_KEY = "YOUR_SUPABASE_SERVICE_ROLE"

TRADING_PAIR = "ETHUSDT"
INTERVAL = Client.KLINE_INTERVAL_15MINUTE
TRADE_PERCENT = 0.25
POLL_INTERVAL = 60  # seconds

# Binance Client - Testnet
client = Client(API_KEY, API_SECRET)
client.API_URL = 'https://testnet.binance.vision/api'

# Supabase Client
postgrest = PostgrestClient(f"{SUPABASE_URL}/rest/v1")
postgrest.auth(SUPABASE_KEY)

# =================== HELPERS ===================
def fetch_candles(symbol, interval, limit=100):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines, columns=[
        "time", "open", "high", "low", "close", "volume", "close_time",
        "quote_asset_volume", "num_trades", "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    df["close"] = df["close"].astype(float)
    return df

def calculate_indicators(df):
    df["EMA20"] = df["close"].ewm(span=20).mean()
    df["RSI"] = compute_rsi(df["close"])
    return df

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# =================== MAIN LOOP ===================
def run_bot():
    while True:
        df = fetch_candles(TRADING_PAIR, INTERVAL)
        df = calculate_indicators(df)

        latest = df.iloc[-1]
        signal = None

        if latest["RSI"] > 70:
            signal = "SELL"
        elif latest["RSI"] < 30:
            signal = "BUY"

        if signal:
            log_trade(signal, latest["close"])

        print(f"[{datetime.datetime.now()}] Checked. Signal: {signal}")
        time.sleep(POLL_INTERVAL)

def log_trade(signal, price):
    now = datetime.datetime.utcnow().isoformat()
    postgrest.table("trades").insert([{
        "pair": TRADING_PAIR,
        "price": price,
        "side": signal,
        "time": now,
        "qty": 0.1,
        "pnl": 0
    }]).execute()

if __name__ == "__main__":
    run_bot()
