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

4. For each pick in `top5.json` (and ONLY those 5): use the morning's `thesis`, `conviction`, `thesis_type`, `signal_source`, `rsi`, and `volume_ratio` as your starting point. Apply the CLAUDE.md decision framework AND any relevant lessons.

   **RSI guard (from morning data)**:
   - rsi > 75 ("bullish_overbought"): do NOT open new positions; existing holders may consider trim
   - rsi < 30 ("bearish_oversold"): only buy if news_score was high AND macro regime is risk_on
   - 30–70: normal range, proceed on thesis

   **Conviction → position size**:
   | Conviction | Starting allocation target |
   |------------|---------------------------|
   | high       | 70–100% of watchlist max_allocation_pct |
   | medium     | 40–65% of watchlist max_allocation_pct |
   | low        | 20–35% of watchlist max_allocation_pct |
   Scale-in strategy: open medium/low at partial size; add on confirmation next session.

   Decide BUY / SELL / HOLD. If a pick's morning data isn't compelling enough to act on right now, mark it HOLD — do NOT substitute a different ticker.

5. For BUY/SELL orders:
   a. Fetch a live quote: python3 scripts/research.py quote SYMBOL
      This returns the current ask_price and bid_price — use these, not the bars close.
   b. Use the `limit_offset_pct` from top5.json for this pick (NOT a flat 0.2%):
      - BUY limit  = ask_price  × (1 + limit_offset_pct / 100)
      - SELL limit = bid_price  × (1 - limit_offset_pct / 100)
   c. Submit each order as ONE Bash call running ONE python3 invocation. NEVER chain multiple `trade.py` calls with `&&`, `;`, `\n`, or backgrounding — one order per Bash call, in sequence. Pass the morning's metadata; use snake_case with no spaces or shell metacharacters:
      `python3 scripts/trade.py order TSM 12 buy 403.14 thesis_type=momentum_technical signal_source=bullish_ma_analyst_upgrade conviction=high rationale=ai_capex_demand_uptrend`
   d. Skip any position that would exceed the symbol's max_allocation_pct.

6. ALSO consider current open positions (from step 3) for SELL signals — even if a current holding isn't in today's top5.json:
   - Any position down 8% from entry MUST be closed (CLAUDE.md hard rule)
   - Any position above 1.5× its watchlist max_allocation_pct MUST be trimmed to max_allocation_pct
   - Any position whose thesis has explicitly reversed (downgrade after upgrade, earnings miss >10%) → close
   - **SELLs need a limit price too.** No market orders, ever. Fetch live quote and use bid_price × (1 - limit_offset_pct / 100).

7. Append trades to today's journal under ## Trades Executed (table with Time, Symbol, Action, Qty, Limit, Order ID, Thesis Type, Signal, Conviction, Rationale) and ## Positions Closed. Include brief reasoning. For each HOLD decision, note WHY in ## Skipped Picks.

Hard rules from CLAUDE.md: no market orders, ≤5% per position (or symbol's max_allocation_pct, whichever is lower), close any position down 8% from entry, trim any position above 1.5× max_allocation_pct.
