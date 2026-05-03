End-of-day reflection. The most recent US trading day in ET is: $(TZ=America/New_York date +%F).
This routine fires the morning AFTER the trading day, so use the ET date above as the journal target.
Today's journal file: journal/$(TZ=America/New_York date +%F).md

STEPS
1. Verify journal/$(TZ=America/New_York date +%F).md exists. If not, fall back to the most recent journal/YYYY-MM-DD.md (excluding SUMMARY.md).
2. Read CLAUDE.md and that journal entry (already has Portfolio Status, Market Research, Trades Executed from earlier routines).
3. python scripts/research.py account; python scripts/research.py positions for closing portfolio state. Note any drift since the trading-session entry.
4. Append the ## End-of-Day Reflection section: 2-4 sentences on what worked, what didn't, what to watch next session. Always write this — even on no-trade days.
5. python scripts/summarize.py — refreshes journal/SUMMARY.md.
6. python scripts/notify.py <path-to-the-journal-file-from-step-1>  — verify it prints status=202.
