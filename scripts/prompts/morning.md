Morning research routine. The trading day in ET is: __ET_DATE__.
Today's journal file: journal/__ET_DATE__.md

CONTEXT (read these first — they give you durable memory across sessions)
- CLAUDE.md  → rules, decision framework, journal template
- journal/SUMMARY.md  → latest portfolio status, last 7 days of trades, last 3 reflections
- journal/lessons.md  → curated lessons from past trades (durable strategy memory)
- journal/SCORECARD.md  → win rate + avg return by thesis_type and conviction (if it exists)
- journal/unfilled.json  → orders that expired unfilled last session (re-evaluate these)

STEPS
1. Read the five context files above. Note:
   - Open positions, recent winning/losing theses, and lessons that apply today.
   - Any entries in `unfilled.json` — these are high-conviction picks that couldn't fill last session. Flag them for priority re-evaluation below.
   - Scorecard data: if SCORECARD.md exists, bias toward thesis types and conviction levels with the highest historical win rate.

2. Run: python3 scripts/trade.py status. If is_open=false, write a one-line "markets closed" note to today's journal file and stop.

3. **Macro context first**: Run: python3 scripts/research.py macro
   This returns SPY/QQQ/SMH signals + a `regime` field (risk_on | risk_off | mixed).
   - regime=risk_off (≥2 macro tickers bearish): lower all individual convictions by ONE level (high→medium, medium→low, low→skip). Note this in the journal.
   - regime=risk_on: no adjustment needed.
   - regime=mixed: use individual ticker signals normally.

4. Run: python3 scripts/research.py scan
   Returns ONE JSON with all watchlist tickers. Each ticker now includes:
   - `ma_signal`: bullish | bearish | mixed | bullish_overbought | bearish_oversold
   - `rsi`: 0–100 (>70 = overbought, <30 = oversold)
   - `volume_ratio`: today's vol / 20-day avg vol (>1.5 = confirming volume)
   - `ema_9`: short-term momentum (price > ema_9 = bullish near-term)
   - `atr`: 14-day average true range
   - `limit_offset_pct`: ATR-derived recommended limit offset for today (0.20–0.50%)
   - `news_score`: composite score from sentiment + recency of top 5 articles
   - `news`: array of up to 5 articles with `title`, `sentiment`, `hours_since`
   Use this — do NOT call bars/news per ticker.

5. Rank the watchlist tickers and pick the TOP 5 candidates. Weighting:
   - **Must-have for high conviction**: bullish ma_signal (not bullish_overbought) + news_score ≥ 2 + volume_ratio ≥ 1.0
   - **bullish_overbought** (RSI > 75): downgrade conviction; existing holders may trim, not add
   - **bearish_oversold** (RSI < 30): only consider if news_score ≥ 3 (catalyst must justify bottom-fishing)
   - **News quality checks**: prefer articles with hours_since < 48; discount articles with sentiment=negative even if headline sounds positive
   - **Unfilled picks from yesterday**: if a ticker in unfilled.json still has a valid thesis, rank it higher — avoid re-missing the same setup
   - Apply all relevant lessons from journal/lessons.md

6. **Write `journal/top5/__ET_DATE__.json` IMMEDIATELY (before any other writes).** Schema:
   ```json
   {
     "trading_day": "__ET_DATE__",
     "macro_regime": "risk_on|risk_off|mixed",
     "picks": [
       {
         "symbol": "...",
         "thesis": "<one short sentence>",
         "conviction": "low|medium|high",
         "thesis_type": "news_catalyst|ma_crossover|news+ma|earnings|other",
         "signal_source": "<who/what specifically — e.g. 'Rothschild upgrade'>",
         "limit_offset_pct": 0.20,
         "rsi": 62.4,
         "volume_ratio": 1.8
       }
     ]
   }
   ```
   Exactly 5 entries. `limit_offset_pct` comes from the scan output for that ticker.
   Picks here MUST match the TOP 5 you write into the markdown journal in step 8.

7. Run: python3 scripts/research.py account; python3 scripts/research.py positions.

8. Create today's journal file using the CLAUDE.md template. Fill in:
   - ## Macro Context (one line: regime + SMH/QQQ/SPY signals)
   - ## Portfolio Status (cash, positions, total value)
   - ## Market Research — for each TOP 5: 2-3 short bullets (MA read, RSI, volume_ratio, news, conviction, limit_offset_pct recommended). For the other tickers: ONE combined line "Other watchlist (no action signal): TICK1, TICK2, ..."
   Leave Trades Executed, Positions Closed, End-of-Day Reflection sections present but empty.

Be concise — bullets, not paragraphs. Only the TOP 5 get deep treatment. Total tool calls expected: ~7 (status, macro, scan, write top5.json, account, positions, write journal).
