Trading session. The trading day in ET is: __ET_DATE__.
Today's journal file: journal/__ET_DATE__.md

CONTEXT (read these first)
- CLAUDE.md  → rules
- watchlist.json  → per-symbol max_allocation_pct
- journal/SUMMARY.md  → recent positions + trade rationale + reflections
- journal/lessons.md  → durable lessons
- **journal/top5/__ET_DATE__.json**  → AUTHORITATIVE top 5 picks from morning. This is your literal universe today.

STEPS
1. Read the context files above. Then load `journal/top5/__ET_DATE__.json`. The 5 symbols in `picks[].symbol` are the ONLY tickers you are permitted to submit orders for today. Do NOT scan the watchlist. Do NOT consider any other symbol. If `top5/__ET_DATE__.json` is missing, append "trading session skipped: morning top5.json missing" to today's journal and stop.
2. Run: python3 scripts/trade.py status. If is_open=false, append "trading session skipped: market closed" to today's journal and stop.
3. python3 scripts/research.py account; python3 scripts/research.py positions.
4. For each pick in `top5.json` (and ONLY those 5): use the morning's `thesis`, `conviction`, `thesis_type`, and `signal_source` as your starting point. Apply the CLAUDE.md decision framework AND any relevant lessons. Decide BUY / SELL / HOLD. If a pick's morning data isn't compelling enough to act on right now, mark it HOLD — do NOT substitute a different ticker.
   - For BUY/SELL, fetch a recent quote and use a limit price within 0.2% of current ask.
   - Submit each order as ONE Bash call running ONE python3 invocation. NEVER chain multiple `trade.py` calls with `&&`, `;`, `\n`, or backgrounding — one order per Bash call, in sequence, so a single network blip can't strand a chained sub-process. Pass the morning's metadata; choose values with NO spaces or shell metacharacters (`{}<>|&;()` etc.) so quoting can't break:
     - thesis_type, signal_source, conviction: snake_case identifiers, no spaces
     - rationale: one short phrase, words joined with underscores (e.g. `rationale=earnings_beat_strong_momentum`). If you need a real sentence, wrap the whole arg in single quotes: `'rationale=Strong Q1 beat, MA bullish'`.
     Concrete shape (real values, single line, no backslashes):
     `python3 scripts/trade.py order TSM 12 buy 403.14 thesis_type=momentum_technical signal_source=bullish_ma_analyst_upgrade conviction=high rationale=ai_capex_demand_uptrend`
   - Skip any position that would exceed the symbol's max_allocation_pct in watchlist.json.
5. ALSO consider current open positions (from step 3) for SELL signals — even if a current holding isn't in today's top5.json. Specifically: any position down 8% from entry MUST be closed (CLAUDE.md hard rule), and any position whose morning thesis has broken should be reviewed. SELLs of existing positions are always allowed regardless of top5.json.
6. Append trades to today's journal under ## Trades Executed (table with the same columns as the CLAUDE.md template) and ## Positions Closed. Include brief reasoning.

Hard rules from CLAUDE.md: no market orders, ≤5% per position (or symbol's max_allocation_pct, whichever is lower), close any position down 8% from entry. validate_order() in trade.py enforces some of this; thesis_type/signal_source/conviction/rationale fields are how you give the future scorecard real signal to learn from — fill them honestly.
