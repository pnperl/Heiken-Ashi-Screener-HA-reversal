import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
import logging
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

# ─────────────────────────────────────────────
#  Load secrets from .env file
# ─────────────────────────────────────────────
load_dotenv()
TOKEN   = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ─────────────────────────────────────────────
#  ✏️  ONLY EDIT THIS — everything else adapts
# ─────────────────────────────────────────────
SYMBOL   = "BTC-USD"   # e.g. "BTC-USD" | "ETH-USD" | "^NSEI" | "^NSEBANK" | "AAPL"
INTERVAL = "5m"
# ─────────────────────────────────────────────

# ── Logging setup ────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log")
    ]
)
log = logging.getLogger(__name__)


# ══════════════════════════════════════════════
#  AUTO-DETECT SYMBOL PROFILE
# ══════════════════════════════════════════════

def detect_profile(symbol: str) -> dict:
    """
    Returns a profile dict that auto-tunes all parameters
    based on the asset type detected from the symbol string.
    """
    s = symbol.upper()

    # ── Crypto ───────────────────────────────
    CRYPTO = ["BTC", "ETH", "BNB", "SOL", "XRP", "DOGE", "ADA"]
    if any(c in s for c in CRYPTO) or s.endswith("-USD") or s.endswith("-USDT"):
        price = _quick_price(symbol)
        # Strike rounding: nearest round number meaningful for the asset
        if price and price > 10_000:
            strike_round = 500       # BTC-level
        elif price and price > 1_000:
            strike_round = 50        # ETH-level
        else:
            strike_round = 1         # small alts
        return {
            "type":          "CRYPTO",
            "timezone":      "UTC",
            "market_hours":  None,           # 24 × 7
            "doji_thresh":   0.15,           # crypto candles are chunkier
            "strike_round":  strike_round,
            "daily_loss_max": 3,
        }

    # ── Indian indices / stocks ───────────────
    if s.startswith("^NSE") or s.startswith("^BSE") or s.endswith(".NS") or s.endswith(".BO"):
        return {
            "type":          "INDIA",
            "timezone":      "Asia/Kolkata",
            "market_hours":  ("09:15", "15:30"),
            "doji_thresh":   0.20,
            "strike_round":  50,
            "daily_loss_max": 3,
        }

    # ── US indices ────────────────────────────
    if s in ["^GSPC", "^DJI", "^IXIC", "^RUT", "SPY", "QQQ", "IWM"]:
        return {
            "type":          "US_INDEX",
            "timezone":      "America/New_York",
            "market_hours":  ("09:30", "16:00"),
            "doji_thresh":   0.20,
            "strike_round":  5,
            "daily_loss_max": 3,
        }

    # ── US / international stocks (default) ──
    return {
        "type":          "STOCK",
        "timezone":      "America/New_York",
        "market_hours":  ("09:30", "16:00"),
        "doji_thresh":   0.20,
        "strike_round":  1,
        "daily_loss_max": 3,
    }


def _quick_price(symbol: str) -> float | None:
    """Fetch a single latest price to calibrate strike rounding for crypto."""
    try:
        df = yf.download(symbol, period="1d", interval="1m",
                         auto_adjust=False, progress=False)
        if not df.empty:
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] for c in df.columns]
            return float(df["Close"].iloc[-1])
    except Exception:
        pass
    return None


# ══════════════════════════════════════════════
#  MARKET HOURS GUARD
# ══════════════════════════════════════════════

def is_market_open(profile: dict) -> bool:
    """Returns True if current time is within market hours (or 24×7 asset)."""
    if profile["market_hours"] is None:
        return True                          # crypto — always open
    tz    = ZoneInfo(profile["timezone"])
    now   = datetime.now(tz).strftime("%H:%M")
    open_ = profile["market_hours"][0]
    close = profile["market_hours"][1]
    return open_ <= now <= close


# ══════════════════════════════════════════════
#  TELEGRAM
# ══════════════════════════════════════════════

def send_alert(message: str):
    if not TOKEN or not CHAT_ID:
        log.warning("Telegram credentials missing — skipping alert")
        return
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        resp = requests.post(
            url,
            data={"chat_id": CHAT_ID, "text": message},
            timeout=5
        )
        resp.raise_for_status()
    except Exception as e:
        log.error(f"Telegram alert failed: {e}")


# ══════════════════════════════════════════════
#  HEIKIN ASHI
# ══════════════════════════════════════════════

def heikin_ashi(df: pd.DataFrame) -> pd.DataFrame | None:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

    df = df[["Open", "High", "Low", "Close"]].copy()
    df = df.apply(pd.to_numeric, errors="coerce").dropna().reset_index(drop=True)

    if len(df) < 4:          # need at least 4 rows so iloc[-3] is valid
        return None

    ha_close = (df["Open"] + df["High"] + df["Low"] + df["Close"]) / 4
    ha_open  = np.zeros(len(df))
    ha_open[0] = (df["Open"].iloc[0] + df["Close"].iloc[0]) / 2
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i - 1] + ha_close.iloc[i - 1]) / 2

    ha = pd.DataFrame({
        "open":  ha_open,
        "close": ha_close.values,
        "high":  np.maximum.reduce([ha_open, ha_close.values, df["High"].values]),
        "low":   np.minimum.reduce([ha_open, ha_close.values, df["Low"].values]),
    })
    return ha


# ══════════════════════════════════════════════
#  SIGNAL
# ══════════════════════════════════════════════

def not_doji(o, c, h, l, thresh: float) -> bool:
    body  = abs(c - o)
    range_ = h - l
    return range_ > 0 and body > thresh * range_


def check_signal(ha: pd.DataFrame, thresh: float) -> str | None:
    """
    Uses the last two CONFIRMED (closed) candles — iloc[-3] and iloc[-2].
    iloc[-1] is the still-forming live candle and is intentionally ignored.
    """
    prev = ha.iloc[-3]
    curr = ha.iloc[-2]

    bull = prev["close"] < prev["open"] and curr["close"] > curr["open"]
    bear = prev["close"] > prev["open"] and curr["close"] < curr["open"]

    if bull and not_doji(*prev[["open","close","high","low"]], thresh) \
             and not_doji(*curr[["open","close","high","low"]], thresh):
        return "CALL"

    if bear and not_doji(*prev[["open","close","high","low"]], thresh) \
             and not_doji(*curr[["open","close","high","low"]], thresh):
        return "PUT"

    return None


# ══════════════════════════════════════════════
#  TIMING
# ══════════════════════════════════════════════

def seconds_until_next_5min() -> float:
    """Safe calculation — handles hour and midnight rollovers."""
    now       = datetime.now()
    delta     = timedelta(minutes=(5 - now.minute % 5))
    next_time = (now + delta).replace(second=5, microsecond=0)
    return max(5.0, (next_time - now).total_seconds())


def get_atm_strike(price: float, strike_round: int) -> int:
    return round(price / strike_round) * strike_round


# ══════════════════════════════════════════════
#  FETCH DATA  (with retry + back-off)
# ══════════════════════════════════════════════

def fetch_data(symbol: str, interval: str, retries: int = 3) -> pd.DataFrame | None:
    for attempt in range(1, retries + 1):
        try:
            df = yf.download(
                symbol,
                period="1d",
                interval=interval,
                auto_adjust=False,
                progress=False
            )
            if not df.empty:
                return df
            log.warning(f"Empty data on attempt {attempt}")
        except Exception as e:
            log.error(f"Fetch error attempt {attempt}: {e}")
        time.sleep(5 * attempt)     # exponential back-off: 5s, 10s, 15s
    return None


# ══════════════════════════════════════════════
#  MAIN LOOP
# ══════════════════════════════════════════════

def main():
    log.info(f"🚀 Bot started — Symbol: {SYMBOL}  Interval: {INTERVAL}")

    profile = detect_profile(SYMBOL)
    log.info(f"📋 Profile detected: {profile['type']} | "
             f"TZ: {profile['timezone']} | "
             f"Doji threshold: {profile['doji_thresh']} | "
             f"Strike round: {profile['strike_round']}")

    send_alert(
        f"🤖 Bot started\n"
        f"Symbol : {SYMBOL}\n"
        f"Type   : {profile['type']}\n"
        f"Interval: {INTERVAL}"
    )

    position        = None
    trailing_sl     = None
    last_candle_time = None
    daily_losses    = 0
    last_reset_day  = datetime.now().date()

    while True:

        # ── Reset daily loss counter at midnight ──
        today = datetime.now().date()
        if today != last_reset_day:
            daily_losses  = 0
            last_reset_day = today
            log.info("Daily loss counter reset")

        # ── Daily loss limit ──────────────────────
        if daily_losses >= profile["daily_loss_max"]:
            log.warning("Daily loss limit reached — pausing until midnight")
            send_alert(f"⛔ Daily loss limit ({profile['daily_loss_max']}) reached. Bot paused till midnight.")
            time.sleep(seconds_until_next_5min())
            continue

        # ── Market hours guard ────────────────────
        if not is_market_open(profile):
            log.info("Market closed — waiting 60s")
            time.sleep(60)
            continue

        # ── Fetch data ────────────────────────────
        df = fetch_data(SYMBOL, INTERVAL)
        if df is None:
            log.error("Could not fetch data after retries — skipping cycle")
            time.sleep(30)
            continue

        # ── Deduplicate candles ───────────────────
        candle_time = df.index[-1]
        if candle_time == last_candle_time:
            time.sleep(5)
            continue
        last_candle_time = candle_time

        # ── Build Heikin Ashi ─────────────────────
        ha = heikin_ashi(df)
        if ha is None:
            log.warning("Not enough candles for HA")
            continue

        latest_price = float(
            df["Close"].iloc[-1].item()
            if hasattr(df["Close"].iloc[-1], "item")
            else df["Close"].iloc[-1]
        )
        atm = get_atm_strike(latest_price, profile["strike_round"])

        signal = check_signal(ha, profile["doji_thresh"])

        # ── ENTRY ─────────────────────────────────
        if signal and position is None:
            position    = signal
            trailing_sl = ha.iloc[-3]["low"] if signal == "CALL" else ha.iloc[-3]["high"]

            msg = (
                f"📊 {SYMBOL} — {signal} ENTRY\n"
                f"Spot      : {round(latest_price, 2)}\n"
                f"ATM Strike: {atm}\n"
                f"Initial SL: {round(trailing_sl, 2)}\n"
                f"Time      : {candle_time}"
            )
            send_alert(msg)
            log.info(f"ENTRY {signal} @ {latest_price}  SL={trailing_sl}")

        # ── TRAILING + EXIT ───────────────────────
        elif position == "CALL":
            new_sl = ha.iloc[-3]["low"]        # last confirmed candle low
            if new_sl > trailing_sl:
                trailing_sl = new_sl
                send_alert(f"🔄 CALL SL trailed → {round(trailing_sl, 2)}")
                log.info(f"CALL SL trailed to {trailing_sl}")

            if latest_price < trailing_sl:
                send_alert(
                    f"❌ CALL SL HIT\n"
                    f"Exit price : {round(latest_price, 2)}\n"
                    f"SL was     : {round(trailing_sl, 2)}"
                )
                log.info("EXIT CALL — SL hit")
                position    = None
                trailing_sl = None
                daily_losses += 1

        elif position == "PUT":
            new_sl = ha.iloc[-3]["high"]
            if new_sl < trailing_sl:
                trailing_sl = new_sl
                send_alert(f"🔄 PUT SL trailed → {round(trailing_sl, 2)}")
                log.info(f"PUT SL trailed to {trailing_sl}")

            if latest_price > trailing_sl:
                send_alert(
                    f"❌ PUT SL HIT\n"
                    f"Exit price : {round(latest_price, 2)}\n"
                    f"SL was     : {round(trailing_sl, 2)}"
                )
                log.info("EXIT PUT — SL hit")
                position    = None
                trailing_sl = None
                daily_losses += 1

        # ── Sleep until next candle ───────────────
        sleep_secs = seconds_until_next_5min()
        log.info(f"Position={position}  Price={round(latest_price,2)}  "
                 f"Sleeping {round(sleep_secs)}s → next candle")
        time.sleep(sleep_secs)


if __name__ == "__main__":
    main()
