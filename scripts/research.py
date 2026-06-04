# scripts/research.py

import os
import requests
from datetime import datetime, timedelta
from pathlib import Path
import json
import math

from runlog import log

ALPACA_KEY = os.getenv("APCA_API_KEY_ID")
ALPACA_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_BASE_URL")

# (connect, read) seconds — same bound used in trade.py.
HTTP_TIMEOUT = (5, 15)

# Macro tickers scanned for sector context — NOT trade candidates.
MACRO_TICKERS = ["SPY", "QQQ", "SMH"]


# ---------------------------------------------------------------------------
# Helper: technical indicator calculations (all from daily bar arrays)
# ---------------------------------------------------------------------------

def _calc_sma(closes, period):
    if len(closes) < period:
        return None
    return round(sum(closes[-period:]) / period, 2)


def _calc_ema(closes, period):
    """Exponential Moving Average using standard smoothing factor k=2/(n+1)."""
    if len(closes) < period:
        return None
    k = 2 / (period + 1)
    ema = sum(closes[:period]) / period  # seed with SMA
    for price in closes[period:]:
        ema = price * k + ema * (1 - k)
    return round(ema, 2)


def _calc_rsi(closes, period=14):
    """Wilder's RSI. Returns None if insufficient data."""
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d for d in deltas if d > 0]
    losses = [-d for d in deltas if d < 0]
    # Use only the last `period` deltas for initial avg
    recent_deltas = deltas[-(period):]
    avg_gain = sum(d for d in recent_deltas if d > 0) / period
    avg_loss = sum(-d for d in recent_deltas if d < 0) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)


def _calc_atr(bars, period=14):
    """Average True Range over `period` days. bars must have h, l, c keys."""
    if len(bars) < period + 1:
        return None
    trs = []
    for i in range(1, len(bars)):
        high = bars[i]["h"]
        low = bars[i]["l"]
        prev_close = bars[i - 1]["c"]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    if len(trs) < period:
        return None
    return round(sum(trs[-period:]) / period, 4)


def _calc_volume_ratio(bars, period=20):
    """Today's volume divided by 20-day average volume. >1.5 = above-avg interest."""
    if len(bars) < period + 1:
        return None
    volumes = [b["v"] for b in bars]
    avg_vol = sum(volumes[-period - 1:-1]) / period  # exclude today
    if avg_vol == 0:
        return None
    return round(volumes[-1] / avg_vol, 2)


def _limit_offset_from_atr(atr, last_close):
    """Return recommended limit offset pct based on ATR/price volatility ratio.

    ATR/price ratio:
      > 2.5%  → volatile day → use 0.50% offset
      1.5–2.5% → moderate → use 0.35%
      < 1.5%  → calm → use 0.20%
    """
    if atr is None or last_close is None or last_close == 0:
        return 0.20
    ratio_pct = (atr / last_close) * 100
    if ratio_pct > 2.5:
        return 0.50
    elif ratio_pct > 1.5:
        return 0.35
    else:
        return 0.20


def _ma_signal(ma_20, ma_50, last_close, rsi=None):
    """Extended MA signal that incorporates RSI overbought/oversold filter."""
    if ma_20 is None or ma_50 is None:
        return "unknown"
    if ma_20 > ma_50 and last_close > ma_20:
        if rsi is not None and rsi > 75:
            return "bullish_overbought"   # bullish but stretched — caution on new entries
        return "bullish"
    elif ma_20 < ma_50 and last_close < ma_20:
        if rsi is not None and rsi < 30:
            return "bearish_oversold"     # bearish but may bounce — watch for reversal
        return "bearish"
    else:
        return "mixed"


# ---------------------------------------------------------------------------
# API calls
# ---------------------------------------------------------------------------

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
    response = requests.get(url, headers=headers, params=params, timeout=HTTP_TIMEOUT)
    return response.json()


def get_quote(symbol):
    """Fetch the latest bid/ask quote for a symbol (live, not delayed bars).

    Returns dict with keys: ask_price, bid_price, ask_size, bid_size, timestamp.
    Use this to anchor limit prices — more accurate than previous-day close.
    """
    headers = {
        "APCA-API-KEY-ID": ALPACA_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET,
    }
    url = f"https://data.alpaca.markets/v2/stocks/{symbol}/quotes/latest"
    params = {"feed": "iex"}
    response = requests.get(url, headers=headers, params=params, timeout=HTTP_TIMEOUT)
    data = response.json()
    log("research", "quote", "fetched quote",
        level="INFO" if response.ok else "WARN",
        http_status=response.status_code,
        symbol=symbol,
        ask=data.get("quote", {}).get("ap"),
        bid=data.get("quote", {}).get("bp"))
    if not response.ok or "quote" not in data:
        return None
    q = data["quote"]
    return {
        "ask_price": q.get("ap"),
        "bid_price": q.get("bp"),
        "ask_size": q.get("as"),
        "bid_size": q.get("bs"),
        "timestamp": q.get("t"),
    }


def get_account():
    """Get current portfolio status."""
    headers = {
        "APCA-API-KEY-ID": ALPACA_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET,
    }
    url = f"{BASE_URL}/v2/account"
    response = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
    data = response.json()
    log("research", "account", "fetched account",
        level="INFO" if response.ok else "WARN",
        http_status=response.status_code,
        cash=data.get("cash"),
        portfolio_value=data.get("portfolio_value"))
    return data


def get_positions():
    """Get all open positions."""
    headers = {
        "APCA-API-KEY-ID": ALPACA_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET,
    }
    url = f"{BASE_URL}/v2/positions"
    response = requests.get(url, headers=headers, timeout=HTTP_TIMEOUT)
    data = response.json()
    log("research", "positions", "fetched positions",
        level="INFO" if response.ok else "WARN",
        http_status=response.status_code,
        n_positions=len(data) if isinstance(data, list) else None)
    return data


def get_news(symbol, limit=10):
    """Get recent news for a symbol. Returns up to `limit` articles with sentiment."""
    headers = {
        "APCA-API-KEY-ID": ALPACA_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET,
    }
    url = "https://data.alpaca.markets/v1beta1/news"
    params = {
        "symbols": symbol,
        "limit": limit,
        "sort": "desc",
    }
    response = requests.get(url, headers=headers, params=params, timeout=HTTP_TIMEOUT)
    return response.json()


def get_open_orders():
    """Fetch all currently open (unfilled) orders from Alpaca."""
    headers = {
        "APCA-API-KEY-ID": ALPACA_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET,
    }
    url = f"{BASE_URL}/v2/orders"
    params = {"status": "open", "limit": 100}
    response = requests.get(url, headers=headers, params=params, timeout=HTTP_TIMEOUT)
    data = response.json()
    log("research", "open_orders", "fetched open orders",
        level="INFO" if response.ok else "WARN",
        http_status=response.status_code,
        n_orders=len(data) if isinstance(data, list) else None)
    return data


def get_macro_context():
    """Fetch bars for SPY, QQQ, SMH and return a compact sector snapshot.

    Used by the morning routine to decide if it's a risk-on or risk-off day
    before ranking individual picks. NOT used as trade candidates.
    Returns dict with per-ticker ma_signal, rsi, last_close, daily_chg_pct.
    """
    result = {}
    for ticker in MACRO_TICKERS:
        try:
            bars_data = get_bars(ticker, limit=60)
            bars = bars_data.get("bars") if isinstance(bars_data, dict) else None
            if not bars:
                result[ticker] = {"error": "no_bars"}
                continue
            closes = [b["c"] for b in bars]
            last_close = closes[-1]
            prev_close = closes[-2] if len(closes) >= 2 else last_close
            daily_chg_pct = round(((last_close - prev_close) / prev_close) * 100, 2) if prev_close else None
            ma_20 = _calc_sma(closes, 20)
            ma_50 = _calc_sma(closes, 50)
            rsi = _calc_rsi(closes)
            signal = _ma_signal(ma_20, ma_50, last_close, rsi)
            result[ticker] = {
                "last_close": round(last_close, 2),
                "daily_chg_pct": daily_chg_pct,
                "ma_20": ma_20,
                "ma_50": ma_50,
                "rsi": rsi,
                "ma_signal": signal,
            }
        except Exception as e:
            log("research", "macro_ticker", "fetch failed", level="WARN", ticker=ticker, error=str(e))
            result[ticker] = {"error": str(e)}

    # Derive overall risk regime
    signals = [v.get("ma_signal", "unknown") for v in result.values() if "error" not in v]
    bullish_count = sum(1 for s in signals if "bullish" in s)
    bearish_count = sum(1 for s in signals if "bearish" in s)
    if bearish_count >= 2:
        regime = "risk_off"          # sector-wide down — lower conviction on all picks
    elif bullish_count >= 2:
        regime = "risk_on"           # broad market supportive — normal conviction
    else:
        regime = "mixed"             # use individual ticker signals; no blanket adjustment
    result["regime"] = regime
    log("research", "macro_context", "computed macro regime", regime=regime,
        bullish=bullish_count, bearish=bearish_count)
    return result


def _summarize_news(news_list, max_articles=5):
    """Summarize top news articles, including sentiment and hours_since."""
    if not news_list:
        return []
    now = datetime.utcnow()
    articles = []
    for item in news_list[:max_articles]:
        created_raw = item.get("created_at", "")
        hours_since = None
        try:
            created_dt = datetime.strptime(created_raw[:19], "%Y-%m-%dT%H:%M:%S")
            hours_since = round((now - created_dt).total_seconds() / 3600, 1)
        except Exception:
            pass
        articles.append({
            "title": item.get("headline"),
            "summary": (item.get("summary") or "")[:200],
            "sentiment": item.get("sentiment"),   # positive | negative | neutral
            "hours_since": hours_since,
        })
    return articles


def scan_watchlist():
    """Fetch bars + news for every symbol in watchlist.json. Returns enriched dict.

    Extended signals vs original:
      - RSI(14): overbought/oversold filter
      - ATR(14): intraday volatility → dynamic limit offset recommendation
      - volume_ratio: today's vol / 20d avg vol (confirms breakouts)
      - ema_9: short-term momentum signal
      - ma_signal: now incorporates RSI (bullish_overbought, bearish_oversold variants)
      - news: top 5 articles with sentiment + hours_since (was: 1 article, no sentiment)
      - limit_offset_pct: ATR-derived recommended offset for limit orders
    """
    watchlist_path = Path(__file__).resolve().parent.parent / "watchlist.json"
    watchlist = json.loads(watchlist_path.read_text()).get("watchlist", [])
    log("research", "scan_start", "scanning watchlist", n_tickers=len(watchlist))

    results = []
    n_err = 0
    for entry in watchlist:
        symbol = entry["symbol"]
        try:
            bars_data = get_bars(symbol)
            news_data = get_news(symbol, limit=10)
        except Exception as e:
            n_err += 1
            log("research", "scan_ticker", "fetch failed", level="WARN", symbol=symbol, error=str(e))
            results.append({"symbol": symbol, "error": str(e)})
            continue

        bars = bars_data.get("bars") if isinstance(bars_data, dict) else None

        # --- Price / MA / momentum signals ---
        ma_20 = ma_50 = ema_9 = last_close = rsi = atr = volume_ratio = None
        ma_signal = "unknown"
        limit_offset_pct = 0.20

        if bars:
            closes = [b["c"] for b in bars]
            last_close = closes[-1]
            ma_20 = _calc_sma(closes, 20)
            ma_50 = _calc_sma(closes, 50)
            ema_9 = _calc_ema(closes, 9)
            rsi = _calc_rsi(closes)
            atr = _calc_atr(bars)
            volume_ratio = _calc_volume_ratio(bars)
            ma_signal = _ma_signal(ma_20, ma_50, last_close, rsi)
            limit_offset_pct = _limit_offset_from_atr(atr, last_close)

        # --- News signals ---
        news_list = news_data.get("news") if isinstance(news_data, dict) else None
        news_articles = _summarize_news(news_list, max_articles=5)

        # Derive a simple news_score: positive sentiment & recent < 48h → higher weight
        news_score = 0
        for art in news_articles:
            if art.get("hours_since") is not None and art["hours_since"] <= 48:
                sentiment = art.get("sentiment", "neutral") or "neutral"
                news_score += {"positive": 2, "neutral": 1, "negative": -1}.get(sentiment, 0)

        results.append({
            "symbol": symbol,
            "max_allocation_pct": entry.get("max_allocation_pct"),
            "last_close": round(last_close, 2) if last_close else None,
            "ma_20": ma_20,
            "ma_50": ma_50,
            "ema_9": ema_9,
            "rsi": rsi,
            "atr": atr,
            "volume_ratio": volume_ratio,
            "ma_signal": ma_signal,
            "limit_offset_pct": limit_offset_pct,
            "news_score": news_score,
            "news": news_articles,
        })

    n_bullish = sum(1 for r in results if "bullish" in r.get("ma_signal", ""))
    n_bearish = sum(1 for r in results if "bearish" in r.get("ma_signal", ""))
    log("research", "scan_done", "scan complete",
        n_tickers=len(results), n_errors=n_err, n_bullish=n_bullish, n_bearish=n_bearish)
    return {"scanned_at": datetime.utcnow().isoformat() + "Z", "tickers": results}


if __name__ == "__main__":
    import sys
    action = sys.argv[1] if len(sys.argv) > 1 else "account"
    symbol = sys.argv[2] if len(sys.argv) > 2 else None

    if action == "bars" and symbol:
        print(json.dumps(get_bars(symbol)))
    elif action == "quote" and symbol:
        print(json.dumps(get_quote(symbol)))
    elif action == "news" and symbol:
        print(json.dumps(get_news(symbol)))
    elif action == "positions":
        print(json.dumps(get_positions()))
    elif action == "scan":
        print(json.dumps(scan_watchlist()))
    elif action == "macro":
        print(json.dumps(get_macro_context()))
    elif action == "open_orders":
        print(json.dumps(get_open_orders()))
    else:
        print(json.dumps(get_account()))
