End-of-day reflection. The most recent US trading day in ET is: __ET_DATE__.
This routine fires the morning AFTER the trading day, so use the ET date above as the journal target.
Today's journal file: journal/__ET_DATE__.md

STEPS
1. Verify journal/__ET_DATE__.md exists. If not, fall back to the most recent journal/YYYY-MM-DD.md (excluding SUMMARY.md).

2. Read CLAUDE.md, that journal entry (already has Portfolio Status, Market Research, Trades Executed from earlier routines), and journal/lessons.md (so you don't duplicate lessons that already exist).

3. python3 scripts/research.py account; python3 scripts/research.py positions — for closing portfolio state. Note any drift since the trading-session entry.

4. **Thesis status update** — for each trade made in the past 5 sessions that is still open, append a one-line update to the journal:
   ```
   | Symbol | Entry Date | Thesis | Status | Notes |
   ```
   Status values: `confirmed` (thesis playing out, position in profit) | `pending` (thesis not yet resolved, neutral P&L) | `broken` (adverse move or catalyst reversed — flag for possible close next session).
   This creates a structured feedback trail that feeds lessons.md quality.

5. Append the ## End-of-Day Reflection section: 2-4 sentences on what worked, what didn't, what to watch next session. Always write this — even on no-trade days.

6. **Lessons step**: If today produced a NON-OBVIOUS lesson — a surprising market reaction, a thesis that broke, a signal that worked despite low conviction, a recurring pattern — append 1-3 lines to journal/lessons.md, prefixed with the date. Format:
   ```
   - 2026-05-04: <terse, actionable lesson>
   ```
   SKIP this step on days where trades just confirmed expectations. Better to write nothing than bland observations.

7. **Log unfilled orders**: Run: python3 scripts/scorecard.py
   This writes journal/unfilled.json (open orders that didn't fill) AND prints a performance summary. Review the unfilled tickers — if any were high-conviction picks, note them for priority re-evaluation tomorrow morning.

8. **Weekly scorecard (Fridays only)**: If today is a Friday, also run: python3 scripts/scorecard.py --save
   This saves journal/SCORECARD.md. Append a 2-sentence summary of the scorecard findings to today's reflection (e.g., "news+ma trades outperforming pure MA trades; high conviction win rate 74%").

9. python3 scripts/summarize.py — refreshes journal/SUMMARY.md.

10. python3 scripts/notify.py <path-to-the-journal-file-from-step-1> — verify it prints status=202.
