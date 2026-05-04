# scripts/trade.py

import os
import requests
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ALPACA_KEY = os.getenv("APCA_API_KEY_ID")
ALPACA_SECRET = os.getenv("APCA_API_SECRET_KEY")
BASE_URL = os.getenv("APCA_BASE_URL")

AUTH_HEADERS = {
    "APCA-API-KEY-ID": ALPACA_KEY,
    "APCA-API-SECRET-KEY": ALPACA_SECRET,
}

TRADES_LOG = Path(__file__).resolve().parent.parent / "journal" / "trades.jsonl"


def _log_trade_event(symbol, qty, side, price, order_response, agent_meta):
    """Append one structured trade event to journal/trades.jsonl.

    The markdown journal stays human-readable; this jsonl is the machine-readable
    audit log that scorecard.py / postmortem.py / weekly review will aggregate.
    Only logs successfully-submitted orders (skips validation failures).
    """
    if not isinstance(order_response, dict) or not order_response.get("id"):
        return
    now_utc = datetime.now(timezone.utc)
    et_date = now_utc.astimezone(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    event = {
        "timestamp": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "trading_day": et_date,
        "symbol": symbol,
        "action": side,
        "qty": float(qty),
        "price": float(price) if price is not None else None,
        "order_id": order_response.get("id"),
        "order_status": order_response.get("status"),
    }
    # Agent-supplied context: thesis_type, signal_source, conviction, rationale, etc.
    event.update({k: v for k, v in agent_meta.items() if v is not None})
    TRADES_LOG.parent.mkdir(parents=True, exist_ok=True)
    with TRADES_LOG.open("a") as f:
        f.write(json.dumps(event) + "\n")

def _account_value():
    r = requests.get(f"{BASE_URL}/v2/account", headers=AUTH_HEADERS)
    return float(r.json()["portfolio_value"])

def _open_positions():
    r = requests.get(f"{BASE_URL}/v2/positions", headers=AUTH_HEADERS)
    return [{"market_value": float(p["market_value"])} for p in r.json()]

def validate_order(symbol, qty, side, current_price, account_value, current_positions):
    """Pre-flight checks before placing any order."""
    order_value = qty * current_price
    allocation_pct = (order_value / account_value) * 100

    # Check max position size
    if allocation_pct > 5:
        return False, f"Order exceeds 5% allocation limit: {allocation_pct:.1f}%"

    # Check total exposure (positions + this order < 80%)
    total_invested = sum(p['market_value'] for p in current_positions)
    if (total_invested + order_value) / account_value > 0.80:
        return False, "Order would violate 20% cash reserve requirement"

    return True, "Order validated"

def place_order(symbol, qty, side, limit_price=None, **agent_meta):
    """Place a buy or sell order. Agent-supplied **agent_meta (thesis_type,
    signal_source, conviction, rationale, ...) is recorded with the trade event
    in journal/trades.jsonl when the order submits successfully.
    """
    headers = {**AUTH_HEADERS, "Content-Type": "application/json"}

    # Pre-flight validation for buys (sells reduce exposure, no need to gate)
    if side == "buy":
        if limit_price is None:
            return {"error": "validation_failed", "reason": "limit_price required (CLAUDE.md: no market orders)"}
        ok, reason = validate_order(
            symbol,
            float(qty),
            side,
            float(limit_price),
            _account_value(),
            _open_positions(),
        )
        if not ok:
            return {"error": "validation_failed", "reason": reason}

    order_data = {
        "symbol": symbol,
        "qty": qty,
        "side": side,  # "buy" or "sell"
        "type": "limit" if limit_price else "market",
        "time_in_force": "day",
    }

    if limit_price:
        order_data["limit_price"] = str(limit_price)

    url = f"{BASE_URL}/v2/orders"
    response = requests.post(url, headers=headers, json=order_data)
    result = response.json()
    _log_trade_event(symbol, qty, side, limit_price, result, agent_meta)
    return result

def cancel_all_orders():
    """Cancel all open orders."""
    headers = {
        "APCA-API-KEY-ID": ALPACA_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET,
    }
    url = f"{BASE_URL}/v2/orders"
    response = requests.delete(url, headers=headers)
    return response.status_code

def get_market_status():
    """Check if the market is open."""
    headers = {
        "APCA-API-KEY-ID": ALPACA_KEY,
        "APCA-API-SECRET-KEY": ALPACA_SECRET,
    }
    url = f"{BASE_URL}/v2/clock"
    response = requests.get(url, headers=headers)
    return response.json()

if __name__ == "__main__":
    action = sys.argv[1]

    if action == "status":
        print(json.dumps(get_market_status()))
    elif action == "order":
        symbol = sys.argv[2]
        qty = sys.argv[3]
        side = sys.argv[4]
        limit_price = sys.argv[5] if len(sys.argv) > 5 and "=" not in sys.argv[5] else None
        # Anything after the positional args in key=value form becomes agent_meta.
        # e.g. thesis_type=news+ma signal_source="Rothschild upgrade" conviction=high
        meta_start = 6 if limit_price is not None else 5
        agent_meta = {}
        for arg in sys.argv[meta_start:]:
            if "=" in arg:
                k, v = arg.split("=", 1)
                agent_meta[k.strip()] = v.strip()
        print(json.dumps(place_order(symbol, qty, side, limit_price, **agent_meta)))
    elif action == "cancel":
        print(cancel_all_orders())
