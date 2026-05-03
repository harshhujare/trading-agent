Trading session. The trading day in ET is: $(TZ=America/New_York date +%F).
Today's journal file: journal/$(TZ=America/New_York date +%F).md

STEPS
1. Read CLAUDE.md (rules), watchlist.json (per-symbol max_allocation_pct), and today's journal file (created by morning research; has the TOP 5 candidates).
2. Run: python scripts/trade.py status. If is_open=false, append "trading session skipped: market closed" to today's journal and stop.
3. python scripts/research.py account; python scripts/research.py positions.
4. For each of the morning's TOP 5 candidates only: apply CLAUDE.md decision framework. Decide BUY / SELL / HOLD.
   - For BUY: fetch a recent quote and use a limit price within 0.2% of current ask. Place via: python scripts/trade.py order SYMBOL QTY buy LIMIT_PRICE
   - For SELL: python scripts/trade.py order SYMBOL QTY sell LIMIT_PRICE
   - Skip any position that would exceed the symbol's max_allocation_pct in watchlist.json.
5. Append trades to today's journal under ## Trades Executed (table) and ## Positions Closed. Include brief reasoning.

Hard rules from CLAUDE.md: no market orders, ≤5% per position (or symbol's max_allocation_pct, whichever is lower), close any position down 8% from entry. validate_order() in scripts/trade.py enforces some of this server-side.
