Morning research routine. The trading day in ET is: __ET_DATE__.
Today's journal file: journal/__ET_DATE__.md

CONTEXT (read these first — they give you durable memory across sessions)
- CLAUDE.md  → rules, decision framework, journal template
- journal/SUMMARY.md  → latest portfolio status, last 7 days of trades, last 3 reflections
- journal/lessons.md  → curated lessons from past trades (durable strategy memory)

STEPS
1. Read the three context files above. Note any open positions, recent winning/losing theses, and lessons that apply to today.
2. Run: python3 scripts/trade.py status. If is_open=false, write a one-line "markets closed" note to today's journal file and stop.
3. Run: python3 scripts/research.py scan. Returns ONE JSON with 27 tickers (symbol, last_close, ma_20, ma_50, ma_signal, top_headline). Use this — do NOT call bars/news per ticker.
4. Rank the 27 tickers and pick the TOP 5 candidates. Weighting:
   - bullish ma_signal + fresh news catalyst (analyst action, earnings, contract win) → high
   - bearish or mixed ma_signal → low (consider only if news is exceptionally strong)
   - news older than 7 days → discount
   - apply lessons from journal/lessons.md (e.g., if a lesson says "discount Cramer mentions" or "X sector underperformed", weight accordingly)
5. Run: python3 scripts/research.py account; python3 scripts/research.py positions.
6. Create today's journal file using the CLAUDE.md template. Fill in:
   - ## Portfolio Status (cash, positions, total value)
   - ## Market Research — for each TOP 5: 2-3 short bullets (MA read, news, BUY/HOLD/SELL lean, conviction low|medium|high). Reference any relevant lessons. For the other 22: ONE combined line "Other watchlist (no action signal): TICK1, TICK2, ..."
   Leave Trades Executed, Positions Closed, End-of-Day Reflection sections present but empty for the later routines to fill in.
7. **Write journal/top5/__ET_DATE__.json** — this is the structured handoff to the trading routine. The 5 symbols here are the ONLY tickers trading is allowed to act on, so keep them consistent with what you wrote in the markdown's TOP 5 section. Schema:
   ```json
   {
     "trading_day": "__ET_DATE__",
     "picks": [
       {"symbol": "...", "thesis": "<one short sentence>", "conviction": "low|medium|high", "thesis_type": "news_catalyst|ma_crossover|news+ma|earnings|other", "signal_source": "<who/what specifically — e.g. 'Rothschild upgrade'>"}
     ]
   }
   ```
   Exactly 5 entries.

Be concise — bullets, not paragraphs. Only the TOP 5 get the deep treatment. Total tool calls expected: ~6 (status, scan, account, positions, write journal, write top5.json).
