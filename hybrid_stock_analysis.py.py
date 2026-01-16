import yfinance as yf
import requests
import time
import random
import json
import os
from datetime import date
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

# =====================================================
# CONFIG
# =====================================================
FMP_API_KEY = "o7kboYt6KwJ7ybDEvuEODBKvgiQo47kN"
CACHE_FILE = "cache.json"

INTRINSIC_MULTIPLE = 18.5
STOP_LOSS_PCT = 0.90

MAX_THREADS = 3   # safe parallelism

# =====================================================
# CACHE
# =====================================================
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

# =====================================================
# TECHNICAL INDICATORS
# =====================================================
def add_indicators(df):
    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()

    delta = df["Close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss
    df["RSI"] = 100 - (100 / (1 + rs))

    ema12 = df["Close"].ewm(span=12).mean()
    ema26 = df["Close"].ewm(span=26).mean()
    df["MACD"] = ema12 - ema26
    df["Signal"] = df["MACD"].ewm(span=9).mean()

    return df

# =====================================================
# FMP FALLBACK
# =====================================================
def fetch_from_fmp(ticker):
    url = f"https://financialmodelingprep.com/api/v3/profile/{ticker}?apikey={FMP_API_KEY}"
    r = requests.get(url, timeout=10).json()
    if not r:
        raise Exception("FMP empty response")

    d = r[0]
    return {
        "price": d.get("price", 0),
        "eps": d.get("eps", 0),
        "profit_margin": d.get("profitMargin", 0),
        "debt_to_equity": d.get("debtToEquity", 0),
        "fifty_two_week_high": float(d.get("range", "0-0").split("-")[-1]),
        "source": "FMP"
    }

# =====================================================
# YAHOO PRIMARY
# =====================================================
def fetch_from_yahoo(ticker):
    stock = yf.Ticker(ticker)
    time.sleep(random.uniform(1.5, 3))

    hist = stock.history(period="1y")
    if hist.empty:
        raise Exception("Yahoo blocked")

    hist = add_indicators(hist)

    info = stock.info or {}
    eps = info.get("trailingEps", 0)

    if eps == 0:
        raise Exception("Missing EPS")

    return {
        "price": hist["Close"][-1],
        "eps": eps,
        "profit_margin": info.get("profitMargins", 0),
        "debt_to_equity": info.get("debtToEquity", 0),
        "fifty_two_week_high": hist["High"].max(),
        "rsi": hist["RSI"][-1],
        "ma50": hist["MA50"][-1],
        "ma200": hist["MA200"][-1],
        "macd": hist["MACD"][-1],
        "source": "Yahoo"
    }

# =====================================================
# ANALYSIS ENGINE
# =====================================================
def analyze_ticker(ticker, cache):
    today = str(date.today())

    if ticker in cache and cache[ticker]["date"] == today:
        return cache[ticker]["data"]

    try:
        data = fetch_from_yahoo(ticker)
    except:
        data = fetch_from_fmp(ticker)

    price = data["price"]
    eps = data["eps"]

    intrinsic = eps * INTRINSIC_MULTIPLE
    mos = ((intrinsic - price) / intrinsic) * 100 if intrinsic > 0 else 0

    signal = "HOLD"
    if mos > 20 and data.get("rsi", 50) < 70:
        signal = "BUY"
    elif mos < 0:
        signal = "AVOID"

    result = {
        "ticker": ticker,
        "price": price,
        "intrinsic": intrinsic,
        "mos": mos,
        "signal": signal,
        "stop": price * STOP_LOSS_PCT,
        "source": data["source"]
    }

    cache[ticker] = {"date": today, "data": result}
    save_cache(cache)

    return result

# =====================================================
# DASHBOARD RUNNER
# =====================================================
def run_dashboard(tickers):
    cache = load_cache()
    results = []

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        for r in executor.map(lambda t: analyze_ticker(t, cache), tickers):
            results.append(r)

    print("\n" + "=" * 80)
    print(f"{'TICKER':<8}{'PRICE':>10}{'INTRINSIC':>12}{'MOS %':>8}{'SIGNAL':>10}{'SOURCE':>10}")
    print("-" * 80)

    for r in results:
        print(f"{r['ticker']:<8}${r['price']:>9.2f}${r['intrinsic']:>11.2f}{r['mos']:>7.1f}%{r['signal']:>10}{r['source']:>10}")

    print("=" * 80)

# =====================================================
# MAIN
# =====================================================
if __name__ == "__main__":
    while True:
        raw = input("\nEnter tickers (comma separated) or 'exit': ")
        if raw.lower() == "exit":
            break

        tickers = [t.strip().upper() for t in raw.split(",")]
        run_dashboard(tickers)
