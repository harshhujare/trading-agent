End-of-day reflection — CLOUD ROUTINE variant.

This runs in an ephemeral Anthropic-hosted sandbox at 4:15 PM ET on US market
days. There is no pre-existing working directory: every run starts by cloning
the repo, and must end by committing + pushing journal/ changes back to origin.

Required env (injected by /schedule routine config):
- GH_TOKEN                                            (fine-grained PAT, contents:write on mayamit/trading-agent)
- APCA_API_KEY_ID, APCA_API_SECRET_KEY, APCA_BASE_URL (Alpaca)
- SENDGRID_API_KEY, NOTIFY_FROM, NOTIFY_EMAIL         (digest email)

STEPS

1. Bootstrap. Run ALL of these in one Bash call so the cwd is set for everything that follows:
   ```
   git clone -q https://x-access-token:${GH_TOKEN}@github.com/mayamit/trading-agent.git
   cd trading-agent
   bash scripts/routine-setup.sh eod
   ```
   setup.sh validates env, writes journal/.current-routine, and creates the
   per-run log at journal/runlog/<ET_DATE>-eod.log. Every subsequent Bash
   call you make must re-`cd trading-agent` first since each call is a fresh
   shell. The runlog helper (used by all python scripts) reads the marker
   file to know where to log.

2. Determine today's ET date and journal target. Run:
   ```
   cd trading-agent && TZ=America/New_York date +%F
   ```
   Use that date wherever the body below says <ET_DATE>. The journal file is
   `journal/<ET_DATE>.md`.

3. Verify `journal/<ET_DATE>.md` exists. If it does not (e.g. morning/trading
   routines failed earlier today), fall back to the most recent
   `journal/YYYY-MM-DD.md` excluding SUMMARY.md. Note this fallback in the
   reflection.

4. Read CLAUDE.md, that journal entry (already has Portfolio Status, Market
   Research, Trades Executed from earlier routines), and journal/lessons.md
   so you don't duplicate lessons that already exist.

5. Run for closing portfolio state. Note any drift since the trading-session entry:
   ```
   cd trading-agent && python3 scripts/research.py account
   cd trading-agent && python3 scripts/research.py positions
   ```

6. Append the `## End-of-Day Reflection` section to the journal entry: 2–4
   sentences on what worked, what didn't, what to watch next session. Always
   write this — even on no-trade days.

7. Lessons step. If today produced a NON-OBVIOUS lesson — a surprising market
   reaction, a thesis that broke, a signal that worked despite low conviction,
   a recurring pattern — append 1–3 lines to journal/lessons.md, prefixed with
   the date:
   ```
   - <ET_DATE>: <terse, actionable lesson>
   ```
   SKIP this step on days where trades just confirmed expectations (don't
   dilute the file with noise). Better nothing than bland observations.

8. Refresh the summary:
   ```
   cd trading-agent && python3 scripts/summarize.py
   ```

9. Send the digest. Verify the output prints `sendgrid status=202`:
   ```
   cd trading-agent && python3 scripts/notify.py journal/<ET_DATE>.md
   ```

10. Finalize. Always run this LAST, even if earlier steps had issues — it
    commits whatever did land and pushes to origin:
    ```
    cd trading-agent && bash scripts/routine-finalize.sh eod
    ```
