# scripts/research.py

import os
import requests
from datetime import datetime, timedelta
from pathlib import Path
import json

ALPACA_KEY = os.getenv("APCA_API_KEY_ID")
ALPACA_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_BASE_URL")

def get_bars(symbol, timeframe="1Day", limit=60):
    """Fetch historical price bars for a symbol.

    Alpaca's v2 bars endpoint returns no data unless `start` is supplied — so we
    backfill enough calendar days to cover `limit` trading days (~1.5x for weekends).
    """
    headers = {
        "APCA-API-KEY-ID": ALPACA_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET,
    }
    start = (datetime.utcnow() - timedelta(days=int(limit * 1.6))).strftime("%Y-%m-%dT%H:%M:%SZ")
    url = f"https://data.alpaca.markets/v2/stocks/{symbol}/bars"
    params = {
        "timeframe": timeframe,
        "start": start,
        "limit": limit,
        "adjustment": "raw",
        "feed": "iex",
    }
    response = requests.get(url, headers=headers, params=params)
    return response.json()

def get_account():
    """Get current portfolio status."""
    headers = {
        "APCA-API-KEY-ID": ALPACA_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET,
    }
    url = f"{BASE_URL}/v2/account"
    response = requests.get(url, headers=headers)
    return response.json()

def get_positions():
    """Get all open positions."""
    headers = {
        "APCA-API-KEY-ID": ALPACA_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET,
    }
    url = f"{BASE_URL}/v2/positions"
    response = requests.get(url, headers=headers)
    return response.json()

def get_news(symbol):
    """Get recent news for a symbol."""
    headers = {
        "APCA-API-KEY-ID": ALPACA_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET,
    }
    url = f"https://data.alpaca.markets/v1beta1/news"
    params = {
        "symbols": symbol,
        "limit": 5,
        "sort": "desc"
    }
    response = requests.get(url, headers=headers, params=params)
    return response.json()

def scan_watchlist():
    """Fetch bars + top news for every symbol in watchlist.json. Returns one combined dict.

    Replaces 27 × 2 = 54 separate per-ticker tool calls with a single batch call.
    Each entry includes computed 20d/50d MAs and an MA signal so the agent can rank without
    additional reasoning rounds.
    """
    watchlist_path = Path(__file__).resolve().parent.parent / "watchlist.json"
    watchlist = json.loads(watchlist_path.read_text()).get("watchlist", [])

    results = []
    for entry in watchlist:
        symbol = entry["symbol"]
        try:
            bars_data = get_bars(symbol)
            news_data = get_news(symbol)
        except Exception as e:
            results.append({"symbol": symbol, "error": str(e)})
            continue

        ma_20 = ma_50 = last_close = None
        ma_signal = "unknown"
        bars = bars_data.get("bars") if isinstance(bars_data, dict) else None
        if bars:
            closes = [b["c"] for b in bars]
            last_close = closes[-1]
            if len(closes) >= 20:
                ma_20 = round(sum(closes[-20:]) / 20, 2)
            if len(closes) >= 50:
                ma_50 = round(sum(closes[-50:]) / 50, 2)
            if ma_20 is not None and ma_50 is not None:
                if ma_20 > ma_50 and last_close > ma_20:
                    ma_signal = "bullish"
                elif ma_20 < ma_50 and last_close < ma_20:
                    ma_signal = "bearish"
                else:
                    ma_signal = "mixed"

        headline = None
        news = news_data.get("news") if isinstance(news_data, dict) else None
        if news:
            top = news[0]
            headline = {
                "title": top.get("headline"),
                "summary": (top.get("summary") or "")[:240],
                "created_at": top.get("created_at"),
            }

        results.append({
            "symbol": symbol,
            "max_allocation_pct": entry.get("max_allocation_pct"),
            "last_close": last_close,
            "ma_20": ma_20,
            "ma_50": ma_50,
            "ma_signal": ma_signal,
            "top_headline": headline,
        })

    return {"scanned_at": datetime.utcnow().isoformat() + "Z", "tickers": results}


if __name__ == "__main__":
    import sys
    action = sys.argv[1] if len(sys.argv) > 1 else "account"
    symbol = sys.argv[2] if len(sys.argv) > 2 else None

    if action == "bars" and symbol:
        print(json.dumps(get_bars(symbol)))
    elif action == "news" and symbol:
        print(json.dumps(get_news(symbol)))
    elif action == "positions":
        print(json.dumps(get_positions()))
    elif action == "scan":
        print(json.dumps(scan_watchlist()))
    else:
        print(json.dumps(get_account()))
