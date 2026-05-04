End-of-day reflection. The most recent US trading day in ET is: $(TZ=America/New_York date +%F).
This routine fires the morning AFTER the trading day, so use the ET date above as the journal target.
Today's journal file: journal/$(TZ=America/New_York date +%F).md

STEPS
1. Verify journal/$(TZ=America/New_York date +%F).md exists. If not, fall back to the most recent journal/YYYY-MM-DD.md (excluding SUMMARY.md).
2. Read CLAUDE.md, that journal entry (already has Portfolio Status, Market Research, Trades Executed from earlier routines), and journal/lessons.md (so you don't duplicate lessons that already exist).
3. python3 scripts/research.py account; python3 scripts/research.py positions for closing portfolio state. Note any drift since the trading-session entry.
4. Append the ## End-of-Day Reflection section: 2-4 sentences on what worked, what didn't, what to watch next session. Always write this — even on no-trade days.
5. Lessons step. If today produced a NON-OBVIOUS lesson — a surprising market reaction, a thesis that broke, a signal that worked despite low conviction, a recurring pattern — append 1-3 lines to journal/lessons.md, prefixed with the date. Format:
   ```
   - 2026-05-04: <terse, actionable lesson>
   ```
   SKIP this step on days where trades just confirmed expectations (don't dilute the file with noise). Better to write nothing than to write bland observations.
6. python3 scripts/summarize.py — refreshes journal/SUMMARY.md.
7. python3 scripts/notify.py <path-to-the-journal-file-from-step-1>  — verify it prints status=202.
