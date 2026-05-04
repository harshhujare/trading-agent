Trading session. The trading day in ET is: $(TZ=America/New_York date +%F).
Today's journal file: journal/$(TZ=America/New_York date +%F).md

CONTEXT (read these first)
- CLAUDE.md  → rules
- watchlist.json  → per-symbol max_allocation_pct
- journal/SUMMARY.md  → recent positions + trade rationale + reflections
- journal/lessons.md  → durable lessons
- journal/$(TZ=America/New_York date +%F).md  → morning research, including the TOP 5 + per-ticker conviction

STEPS
1. Read all five context files above.
2. Run: python3 scripts/trade.py status. If is_open=false, append "trading session skipped: market closed" to today's journal and stop.
3. python3 scripts/research.py account; python3 scripts/research.py positions.
4. For each of the morning's TOP 5 candidates only: apply the CLAUDE.md decision framework AND the lessons from journal/lessons.md. Decide BUY / SELL / HOLD.
   - For BUY/SELL, fetch a recent quote and use a limit price within 0.2% of current ask.
   - Submit with structured metadata so trades.jsonl gets a real audit trail:
     ```
     python3 scripts/trade.py order SYMBOL QTY {buy|sell} LIMIT_PRICE \
       thesis_type=news_catalyst|ma_crossover|news+ma|stop_loss|target_hit|thesis_broken \
       signal_source="<short — what specifically triggered this>" \
       conviction=low|medium|high \
       rationale="<one short sentence: why now>"
     ```
   - Skip any position that would exceed the symbol's max_allocation_pct in watchlist.json.
5. Append trades to today's journal under ## Trades Executed (table with the same columns as the CLAUDE.md template) and ## Positions Closed. Include brief reasoning.

Hard rules from CLAUDE.md: no market orders, ≤5% per position (or symbol's max_allocation_pct, whichever is lower), close any position down 8% from entry. validate_order() in trade.py enforces some of this; thesis_type/signal_source/conviction/rationale fields are how you give the future scorecard real signal to learn from — fill them honestly.
