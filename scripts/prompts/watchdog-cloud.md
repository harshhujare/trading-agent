Watchdog routine — verify today's journal landed.

Runs in an Anthropic-hosted sandbox at 5:30 PM ET on US market days, after the
EOD routine should have committed. Pulls origin/main, checks that today's
journal entry exists and has an End-of-Day Reflection, and emails an alert if
not.

Required env (injected by /schedule routine config):
- GH_TOKEN                                            (read-only PAT is fine here)
- APCA_API_KEY_ID, APCA_API_SECRET_KEY, APCA_BASE_URL (needed by setup.sh env check)
- SENDGRID_API_KEY, NOTIFY_FROM, NOTIFY_EMAIL         (alert email)

STEPS

1. Bootstrap and run the watchdog. ONE Bash call:
   ```
   git clone -q https://x-access-token:${GH_TOKEN}@github.com/mayamit/trading-agent.git
   cd trading-agent
   bash scripts/routine-setup.sh watchdog
   python3 scripts/watchdog.py
   ```
   watchdog.py exits 0 with a one-line "all good" if today's journal is
   present + has a non-empty reflection. It exits 1 after sending a SendGrid
   alert email if either is missing.

2. Finalize. The watchdog usually doesn't modify journal/, so this is a no-op
   commit — but run it anyway so the runlog gets pushed:
   ```
   cd trading-agent && bash scripts/routine-finalize.sh watchdog
   ```

No further work. Don't write to journal/<date>.md from this routine — that's
EOD's job. The watchdog only observes and alerts.
