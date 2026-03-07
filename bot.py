import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
import logging
from datetime import datetime, timedelta

from zoneinfo import ZoneInfo
from IPython.display import clear_output
from google.colab import userdata

# --- 1. SETTINGS & ASSETS ---
# Expanded list with popular symbols from different markets
SYMBOLS = [
    "BTC-USD", "ETH-USD", "SOL-USD",  # Crypto
    "^NSEI", "^NSEBANK", "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "LT.NS", # India (Nifty 50, Reliance, HDFC)
    "AAPL", "TSLA", "NVDA", "MSFT"      # US (Apple, Tesla, Nvidia, Microsoft)
]

INTERVAL = "5m"
MIN_PROBABILITY = 60
ATR_SL_MULTIPLIER = 1.5
TP_THRESHOLD = 0.05  # 5% Fixed Take Profit
IST = ZoneInfo("Asia/Kolkata")

TOKEN = userdata.get("TELEGRAM_TOKEN")
CHAT_ID = userdata.get("CHAT_ID")

logging.basicConfig(level=logging.WARNING)

# --- 2. CORE FUNCTIONS ---
def detect_profile(symbol: str) -> dict:
    s = symbol.upper()
    if "BTC" in s or "ETH" in s or "SOL" in s or s.endswith("-USD"): 
        return dict(type="CRYPTO", tz="UTC", hours=None, doji=0.15, strike=1)
    if "^NSE" in s or s.endswith(".NS"): 
        return dict(type="INDIA", tz="Asia/Kolkata", hours=("09:15","15:30"), doji=0.20, strike=50)
    return dict(type="US_STOCK", tz="America/New_York", hours=("09:30","16:00"), doji=0.20, strike=1)

def is_market_open(profile: dict) -> bool:
    if profile["hours"] is None: return True
    now_tz = datetime.now(ZoneInfo(profile["tz"]))
    if now_tz.weekday() >= 5: return False
    curr = now_tz.strftime("%H:%M")
    return profile["hours"][0] <= curr <= profile["hours"][1]

def send_alert(msg):
    if not TOKEN or not CHAT_ID: print(f"[LOG] {msg}"); return
    try: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg}, timeout=5)
    except: pass

def fetch_data(symbol, interval): 
    try: 
        df = yf.download(symbol, period="2d", interval=interval, auto_adjust=False, progress=False)
        if isinstance(df.columns, pd.MultiIndex): df.columns = [c[0] for c in df.columns]
        return df if not df.empty else None
    except: return None

def heikin_ashi(df):
    df = df[["Open","High","Low","Close"]].apply(pd.to_numeric).dropna().reset_index(drop=True)
    if len(df) < 10: return None
    ha_close = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4
    ha_open = np.zeros(len(df))
    ha_open[0] = (df["Open"].iloc[0] + df["Close"].iloc[0]) / 2
    for i in range(1, len(df)): ha_open[i] = (ha_open[i-1] + ha_close.iloc[i-1]) / 2
    return pd.DataFrame({"open": ha_open, "close": ha_close.values, "high": np.maximum.reduce([ha_open, ha_close.values, df["High"].values]), "low": np.minimum.reduce([ha_open, ha_close.values, df["Low"].values])})

def compute_indicators(df):
    close, high, low = df["Close"], df["High"], df["Low"]
    delta = close.diff(); gain = delta.clip(lower=0).rolling(14).mean(); loss = (-delta.clip(upper=0)).rolling(14).mean()
    rsi = float((100 - 100 / (1 + gain / loss)).iloc[-2])
    tr = pd.concat([(high - low), (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    return {"rsi": rsi, "atr": float(tr.rolling(14).mean().iloc[-2]), "ema": float(close.ewm(span=20).mean().iloc[-2])}

def print_dashboard(symbol_states):
    clear_output(wait=True)
    print(f"\n  === MULTI-SYMBOL BOT ({datetime.now(IST).strftime('%I:%M:%S %p')}) ===")
    print(f"  {'SYMBOL':<12} {'STATUS':<8} {'POS':<6} {'ENTRY':<10} {'PRICE':<10} {'UNREAL':<10}")
    print("  " + "-"*65)
    g_trades, g_pnl = 0, 0.0
    for s, st in symbol_states.items():
        m_stat = "OPEN" if is_market_open(st['profile']) else "CLOSED"
        pos, ent, cur = st['position'] or "-", round(st['entry_price'] or 0, 2), round(st['latest_price'] or 0, 2)
        unreal = 0.0
        if pos == "CALL": unreal = cur - ent
        elif pos == "PUT": unreal = ent - cur
        print(f"  {s:<12} {m_stat:<8} {pos:<6} {ent:<10} {cur:<10} {round(unreal,2):<10}")
        g_trades += st['stats']['trades']; g_pnl += st['stats']['pnl']
    print(f"\n  Global Trades: {g_trades} | Realized P&L: {round(g_pnl, 2)} pts")

# --- 3. MAIN LOOP ---
def start_bot():
    states = {s: {"position": None, "entry_price": None, "trailing_sl": None, "latest_price": 0, 
                  "profile": detect_profile(s), "stats": {"trades":0, "pnl":0.0}, "last_time": None} for s in SYMBOLS}
    
    while True:
        for s in SYMBOLS:
            st = states[s]
            if not is_market_open(st["profile"]): continue
            
            df = fetch_data(s, INTERVAL)
            if df is None: continue
            if df.index[-1] == st["last_time"]: continue
            st["last_time"] = df.index[-1]
            
            ha = heikin_ashi(df); ind = compute_indicators(df)
            price = float(df["Close"].iloc[-1]); st["latest_price"] = price

            # Exit Logic (TP & SL)
            if st["position"]:
                p_pct = (price - st["entry_price"])/st["entry_price"] if st["position"] == "CALL" else (st["entry_price"] - price)/st["entry_price"]
                if p_pct >= TP_THRESHOLD or (st["position"] == "CALL" and price < st["trailing_sl"]) or (st["position"] == "PUT" and price > st["trailing_sl"]):
                    pnl = (price - st["entry_price"]) if st["position"] == "CALL" else (st["entry_price"] - price)
                    st["stats"]["pnl"] += pnl; send_alert(f"EXIT {s} | P&L: {round(pnl,2)}")
                    st["position"] = None; st["entry_price"] = None

            # Entry Logic (Simplified Signal)
            elif ha.iloc[-2]["close"] > ha.iloc[-2]["open"] and ha.iloc[-3]["close"] < ha.iloc[-3]["open"]:
                st["position"], st["entry_price"] = "CALL", price
                st["trailing_sl"] = price - (ind["atr"] * ATR_SL_MULTIPLIER); st["stats"]["trades"] += 1
                send_alert(f"ENTRY CALL {s} at {price}")

        print_dashboard(states)
        time.sleep(30)

start_bot()
