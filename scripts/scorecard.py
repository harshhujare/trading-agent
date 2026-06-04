"""scripts/scorecard.py — Performance feedback loop for the trading agent.

Reads journal/trades.jsonl and open Alpaca positions to compute:
  - Win rate + avg return grouped by thesis_type and conviction
  - Best and worst individual trades
  - Unfilled order log (written to journal/unfilled.json)

Run via EOD routine on Fridays, or manually:
  python3 scripts/scorecard.py              → prints markdown summary
  python3 scripts/scorecard.py --save       → also appends to journal/SCORECARD.md
"""

import json
import os
import sys
import requests
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from runlog import log

ALPACA_KEY = os.getenv("APCA_API_KEY_ID")
ALPACA_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_BASE_URL")
HTTP_TIMEOUT = (5, 15)

TRADES_LOG = Path(__file__).resolve().parent.parent / "journal" / "trades.jsonl"
SCORECARD_PATH = Path(__file__).resolve().parent.parent / "journal" / "SCORECARD.md"
UNFILLED_PATH = Path(__file__).resolve().parent.parent / "journal" / "unfilled.json"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_trades():
    """Load all events from trades.jsonl. Returns list of dicts."""
    if not TRADES_LOG.exists():
        return []
    trades = []
    with TRADES_LOG.open() as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    trades.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return trades


def _get_current_positions():
    """Return {symbol: current_price} for all open positions."""
    headers = {
        "APCA-API-KEY-ID": ALPACA_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET,
    }
    try:
        r = requests.get(f"{BASE_URL}/v2/positions", headers=headers, timeout=HTTP_TIMEOUT)
        positions = r.json() if r.ok else []
        return {p["symbol"]: float(p["current_price"]) for p in positions if isinstance(p, dict)}
    except Exception as e:
        log("scorecard", "positions", "fetch failed", level="WARN", error=str(e))
        return {}


def _get_open_orders():
    """Return list of open (unfilled) orders from Alpaca."""
    headers = {
        "APCA-API-KEY-ID": ALPACA_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET,
    }
    try:
        r = requests.get(f"{BASE_URL}/v2/orders", headers=headers,
                         params={"status": "open", "limit": 100}, timeout=HTTP_TIMEOUT)
        return r.json() if r.ok else []
    except Exception as e:
        log("scorecard", "open_orders", "fetch failed", level="WARN", error=str(e))
        return []


# ---------------------------------------------------------------------------
# P&L pairing: match buys to sells per symbol (FIFO)
# ---------------------------------------------------------------------------

def _pair_trades(trades):
    """FIFO match of buy→sell events. Returns (closed_trades, open_trades).

    closed_trades: list of {symbol, buy_price, sell_price, qty, return_pct,
                             thesis_type, conviction, signal_source, trading_day}
    open_trades:   list of {symbol, buy_price, qty, thesis_type, conviction,
                             signal_source, trading_day}  — needs current price to close
    """
    # Group buy/sell events per symbol in chronological order
    by_symbol = defaultdict(list)
    for t in trades:
        by_symbol[t["symbol"]].append(t)

    closed = []
    open_buys = []

    for symbol, events in by_symbol.items():
        buy_queue = []  # FIFO stack of (qty_remaining, event)
        for event in events:
            side = event.get("action", "").lower()
            qty = float(event.get("qty", 0))
            price = float(event.get("price") or 0)

            if side == "buy":
                buy_queue.append({"qty": qty, "price": price, "event": event})
            elif side == "sell":
                remaining_sell = qty
                while remaining_sell > 0 and buy_queue:
                    buy = buy_queue[0]
                    matched = min(buy["qty"], remaining_sell)
                    ret_pct = ((price - buy["price"]) / buy["price"]) * 100 if buy["price"] else None
                    closed.append({
                        "symbol": symbol,
                        "buy_price": buy["price"],
                        "sell_price": price,
                        "qty": matched,
                        "return_pct": round(ret_pct, 2) if ret_pct is not None else None,
                        "thesis_type": buy["event"].get("thesis_type", "unknown"),
                        "conviction": buy["event"].get("conviction", "unknown"),
                        "signal_source": buy["event"].get("signal_source"),
                        "trading_day": buy["event"].get("trading_day"),
                    })
                    buy["qty"] -= matched
                    remaining_sell -= matched
                    if buy["qty"] <= 0:
                        buy_queue.pop(0)

        # Remaining buys are open positions
        for buy in buy_queue:
            if buy["qty"] > 0:
                open_buys.append({
                    "symbol": symbol,
                    "buy_price": buy["price"],
                    "qty": buy["qty"],
                    "thesis_type": buy["event"].get("thesis_type", "unknown"),
                    "conviction": buy["event"].get("conviction", "unknown"),
                    "signal_source": buy["event"].get("signal_source"),
                    "trading_day": buy["event"].get("trading_day"),
                })

    return closed, open_buys


def _enrich_open_with_current_prices(open_buys, current_prices):
    """Add return_pct to open positions using current market price."""
    enriched = []
    for b in open_buys:
        current = current_prices.get(b["symbol"])
        if current and b["buy_price"]:
            ret_pct = ((current - b["buy_price"]) / b["buy_price"]) * 100
            b = dict(b, return_pct=round(ret_pct, 2), current_price=current, status="open")
        else:
            b = dict(b, return_pct=None, status="open_no_price")
        enriched.append(b)
    return enriched


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def _aggregate(all_trades, group_key):
    """Group trades by a key and compute win rate + avg return."""
    groups = defaultdict(list)
    for t in all_trades:
        key = t.get(group_key, "unknown") or "unknown"
        if t.get("return_pct") is not None:
            groups[key].append(t["return_pct"])

    rows = []
    for key, returns in sorted(groups.items()):
        wins = sum(1 for r in returns if r > 0)
        n = len(returns)
        rows.append({
            "key": key,
            "n": n,
            "win_rate_pct": round((wins / n) * 100, 1) if n else 0,
            "avg_return_pct": round(sum(returns) / n, 2) if n else 0,
            "best_pct": round(max(returns), 2) if returns else None,
            "worst_pct": round(min(returns), 2) if returns else None,
        })
    # Sort by avg_return desc
    rows.sort(key=lambda r: r["avg_return_pct"], reverse=True)
    return rows


def _top_bottom_trades(all_trades, n=5):
    """Return the n best and n worst individual trades by return_pct."""
    ranked = sorted(
        [t for t in all_trades if t.get("return_pct") is not None],
        key=lambda t: t["return_pct"],
        reverse=True,
    )
    return ranked[:n], ranked[-n:][::-1]


# ---------------------------------------------------------------------------
# Unfilled order logging
# ---------------------------------------------------------------------------

def save_unfilled_orders():
    """Fetch open orders from Alpaca and write to journal/unfilled.json.

    This is called by the EOD routine so the morning routine can pick up
    high-conviction picks that failed to fill and flag them for re-evaluation.
    """
    orders = _get_open_orders()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "as_of": now,
        "unfilled": [
            {
                "symbol": o.get("symbol"),
                "side": o.get("side"),
                "qty": o.get("qty"),
                "limit_price": o.get("limit_price"),
                "submitted_at": o.get("submitted_at"),
                "order_id": o.get("id"),
            }
            for o in orders
            if isinstance(o, dict)
        ],
    }
    UNFILLED_PATH.parent.mkdir(parents=True, exist_ok=True)
    UNFILLED_PATH.write_text(json.dumps(payload, indent=2))
    log("scorecard", "unfilled", "wrote unfilled.json",
        path=str(UNFILLED_PATH), n_orders=len(payload["unfilled"]))
    return payload


# ---------------------------------------------------------------------------
# Markdown report generation
# ---------------------------------------------------------------------------

def _md_table(headers, rows, key_order):
    lines = ["| " + " | ".join(headers) + " |",
             "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(k, "—")) for k in key_order) + " |")
    return "\n".join(lines)


def build_report(all_trades):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    total = len(all_trades)
    with_returns = [t for t in all_trades if t.get("return_pct") is not None]
    n_closed = sum(1 for t in all_trades if t.get("status") != "open")

    by_thesis = _aggregate(all_trades, "thesis_type")
    by_conviction = _aggregate(all_trades, "conviction")
    best, worst = _top_bottom_trades(all_trades)

    overall_win_rate = round(
        (sum(1 for t in with_returns if t["return_pct"] > 0) / len(with_returns)) * 100, 1
    ) if with_returns else 0
    overall_avg = round(
        sum(t["return_pct"] for t in with_returns) / len(with_returns), 2
    ) if with_returns else 0

    lines = [
        f"# Trading Agent Scorecard",
        f"",
        f"_Generated {now_str} | {total} total trades | {n_closed} closed_",
        f"",
        f"## Overall Performance",
        f"- **Win rate**: {overall_win_rate}%",
        f"- **Avg return per trade**: {overall_avg:+.2f}%",
        f"",
        f"## By Thesis Type",
        f"",
        _md_table(
            ["Thesis Type", "N", "Win Rate", "Avg Return", "Best", "Worst"],
            by_thesis,
            ["key", "n", "win_rate_pct", "avg_return_pct", "best_pct", "worst_pct"],
        ),
        f"",
        f"## By Conviction",
        f"",
        _md_table(
            ["Conviction", "N", "Win Rate", "Avg Return", "Best", "Worst"],
            by_conviction,
            ["key", "n", "win_rate_pct", "avg_return_pct", "best_pct", "worst_pct"],
        ),
        f"",
        f"## Top 5 Trades",
        f"",
        _md_table(
            ["Symbol", "Day", "Thesis", "Conviction", "Return %"],
            best,
            ["symbol", "trading_day", "thesis_type", "conviction", "return_pct"],
        ),
        f"",
        f"## Worst 5 Trades",
        f"",
        _md_table(
            ["Symbol", "Day", "Thesis", "Conviction", "Return %"],
            worst,
            ["symbol", "trading_day", "thesis_type", "conviction", "return_pct"],
        ),
        f"",
        f"---",
        f"_Use this data to adjust conviction weights and thesis type preferences in morning.md_",
        f"",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(save=False):
    trades_raw = _load_trades()
    if not trades_raw:
        print("No trades found in trades.jsonl.")
        return

    current_prices = _get_current_positions()
    closed, open_buys = _pair_trades(trades_raw)
    open_enriched = _enrich_open_with_current_prices(open_buys, current_prices)
    all_trades = closed + open_enriched

    log("scorecard", "run", "computed scorecard",
        n_raw=len(trades_raw), n_closed=len(closed), n_open=len(open_buys))

    report = build_report(all_trades)
    print(report)

    if save:
        SCORECARD_PATH.parent.mkdir(parents=True, exist_ok=True)
        SCORECARD_PATH.write_text(report)
        print(f"\nSaved to {SCORECARD_PATH}")
        log("scorecard", "save", "wrote scorecard", path=str(SCORECARD_PATH))

    # Always refresh unfilled.json
    save_unfilled_orders()


if __name__ == "__main__":
    save_flag = "--save" in sys.argv
    run(save=save_flag)
