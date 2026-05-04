# trading-agent

Autonomous **paper-trading** agent for a curated 27-ticker watchlist of photonics / AI-infrastructure stocks. Runs locally on macOS via `launchd`, calls Alpaca's paper API (no real money at risk), and emails a daily digest via SendGrid.

The "agent" is Claude Code (Haiku) invoked non-interactively three times per market day with prompts that load this repo, call the Python tooling here, and write a structured journal entry.

## Daily flow

| When (IST)         | When (ET)        | Routine          | What it does                                                                                                                                                              |
| ------------------ | ---------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Mon-Fri 7:15 PM    | 9:45 AM          | Morning Research | One batched scan of all 27 tickers (bars + news + computed 20d/50d MAs + signal). Picks **top 5** by MA signal × news catalyst. Creates `journal/YYYY-MM-DD.md`.          |
| Mon-Fri 7:30 PM    | 10:00 AM         | Trading Session  | Reads the morning's top 5. Decides BUY/SELL/HOLD per `CLAUDE.md` rules. Places limit orders within 0.2% of ask. Appends to today's journal.                              |
| Tue-Sat 8:00 AM    | 10:30 PM prior   | End of Day       | Pulls closing positions. Writes reflection. Refreshes `journal/SUMMARY.md`. Emails the digest via SendGrid.                                                              |

## Risk controls (enforced in `CLAUDE.md` + `validate_order()`)

- **≤5% per position** (or `max_allocation_pct` from `watchlist.json`, whichever is lower)
- **No market orders** — limit only, ≤0.2% above current ask
- **8% stop-loss** — close any position down 8% from entry
- **20% cash reserve** — total exposure capped at 80% of portfolio

## Architecture

```
launchd plist (~/Library/LaunchAgents/com.mayamit.trading.*.plist)
   └─ scripts/run-routine.sh {morning|trading|eod}
        ├─ loads .env (Alpaca + SendGrid keys)
        ├─ pins SSL_CERT_FILE via certifi
        └─ pipes scripts/prompts/<routine>.md into:
             claude --print --model haiku --max-budget-usd 1.00
                ├─ reads CLAUDE.md, watchlist.json
                ├─ calls scripts/{research,trade,summarize,notify}.py as Bash tools
                └─ writes journal/YYYY-MM-DD.md
```

## Layout

```
trading-agent/
├─ CLAUDE.md             # agent persona, rules, decision framework, journal template
├─ watchlist.json        # 27 tickers with per-symbol allocation caps + 20% cash reserve
├─ scripts/
│  ├─ research.py        # bars / news / account / positions / scan (batched)
│  ├─ trade.py           # status / order (with validate_order guardrail) / cancel
│  ├─ summarize.py       # rolls journal entries into SUMMARY.md
│  ├─ notify.py          # SendGrid email digest (self-heals SSL via certifi)
│  ├─ run-routine.sh     # wrapper invoked by launchd
│  └─ prompts/
│     ├─ morning.md
│     ├─ trading.md
│     └─ eod.md
├─ journal/
│  ├─ YYYY-MM-DD.md      # daily narrative (portfolio, research, trades, reflection)
│  ├─ SUMMARY.md         # rolled-up: latest portfolio + last 7d trades + last 3d reflections
│  ├─ trades.jsonl       # structured trade audit log (one JSON line per order event)
│  └─ lessons.md         # curated, append-only durable lessons (EOD writes, morning reads)
├─ .claude/routines.json # original (cloud) routine intent — not wired
└─ .env                  # gitignored: Alpaca + SendGrid keys
```

## Setup (macOS)

1. Clone the repo and `cd` in.
2. Create `.env` with:
   ```
   APCA_API_KEY_ID=…
   APCA_API_SECRET_KEY=…
   APCA_BASE_URL=https://paper-api.alpaca.markets
   SENDGRID_API_KEY=SG.…
   NOTIFY_FROM=verified-sender@example.com   # must be verified in SendGrid
   NOTIFY_EMAIL=where-to-send-digest@example.com
   ```
3. `pip3 install requests sendgrid certifi`
4. Smoke test: `./scripts/run-routine.sh morning` — should write a journal note (or "markets closed" on a non-trading day) and exit.
5. Activate the schedule:
   ```
   launchctl load ~/Library/LaunchAgents/com.mayamit.trading.morning.plist
   launchctl load ~/Library/LaunchAgents/com.mayamit.trading.trading.plist
   launchctl load ~/Library/LaunchAgents/com.mayamit.trading.eod.plist
   ```
6. Logs land in `~/Library/Logs/trading-agent/{morning,trading,eod}.log`.

## Limits to be aware of

- **Mac must be awake** at firing times — `launchd` does not wake from sleep
- **DST drift** twice a year — plists are in machine-local time; when NY flips EDT↔EST, the routines fire 1 hour off in NY local until you manually shift the plists
- **Per-run cost is capped at $1.00** via `--max-budget-usd`; typical Haiku runs land well under
- The `.claude/routines.json` file documents an earlier attempt to run this on Anthropic's cloud routines (`/schedule`); that path was abandoned because the source-clone integration on the freshly-provisioned environment kept failing
