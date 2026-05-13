#!/usr/bin/env bash
# Invoked by launchd. Loads .env and runs claude on the named routine prompt.
set -euo pipefail

ROUTINE="${1:?usage: $0 morning|trading|eod}"
PROJECT_DIR="/Users/AmitGandhi/techshot/trading-agent"
PROMPT_FILE="$PROJECT_DIR/scripts/prompts/$ROUTINE.md"
CLAUDE="/Users/AmitGandhi/.local/bin/claude"

[[ -f "$PROMPT_FILE" ]] || { echo "no prompt file: $PROMPT_FILE" >&2; exit 1; }
[[ -x "$CLAUDE" ]] || { echo "claude not executable at $CLAUDE" >&2; exit 1; }

cd "$PROJECT_DIR"

ET_DATE="$(TZ=America/New_York date +%F)"

# All logging for this run lands in a single date+routine file under
# journal/runlog/ so it commits with the rest of the journal and survives the
# routines migration. The launchd plist's StandardOutPath catches anything
# emitted before this redirect (effectively just argv-validation failures).
RUNLOG_DIR="$PROJECT_DIR/journal/runlog"
mkdir -p "$RUNLOG_DIR"
RUNLOG="$RUNLOG_DIR/$ET_DATE-$ROUTINE.log"
export RUNLOG
exec >>"$RUNLOG" 2>&1

log() {
    # log LEVEL STEP MESSAGE [k=v ...]
    local level="$1"; local step="$2"; local msg="$3"; shift 3
    printf '%s [%s] [run-routine/%s] %s' \
        "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$level" "$step" "$msg"
    for kv in "$@"; do printf ' %s' "$kv"; done
    printf '\n'
}

RUN_START_EPOCH=$SECONDS
log INFO start "routine starting" routine="$ROUTINE" et_date="$ET_DATE" pid=$$

# Load .env so the trading scripts have Alpaca + SendGrid keys
set -a
source ./.env
set +a
log INFO env "env loaded" \
    alpaca_key_present=$([[ -n "${APCA_API_KEY_ID:-}" ]] && echo true || echo false) \
    alpaca_base="${APCA_BASE_URL:-unset}" \
    sendgrid_present=$([[ -n "${SENDGRID_API_KEY:-}" ]] && echo true || echo false)

# Self-heal TLS for SendGrid (matches what notify.py does internally)
export SSL_CERT_FILE="$(/usr/local/bin/python3 -c 'import certifi; print(certifi.where())')"

# Resolve the date placeholder safely. We deliberately avoid `eval` here: an
# earlier version used `eval cat <<EOF` which was happy to interpret any shell
# metachar in the prompt (`{a|b}`, `<placeholder>`, `|`, backslashes, etc.)
# and crashed both trading + eod runs. sed substitution touches only the literal
# placeholder __ET_DATE__ and leaves all other characters in the prompt intact.
PROMPT="$(sed "s|__ET_DATE__|$ET_DATE|g" "$PROMPT_FILE")"

# Trading-only: wait for morning's top5/<ET_DATE>.json to land before invoking
# claude. The 15-min schedule gap (morning 9:45 → trading 10:00 ET) is too
# tight when the Mac wakes from sleep and both jobs fire late, or when haiku's
# morning research wanders. On 2026-05-06 trading bailed while morning was
# still running. On 2026-05-07 the file was written 90 seconds after a 12-min
# poll timed out — so cap raised to 20 min. Morning was also reordered to
# write top5.json before the long-form journal markdown, so the file should
# now land within the first few minutes of morning's run.
if [[ "$ROUTINE" == "trading" ]]; then
    TOP5_FILE="$PROJECT_DIR/journal/top5/$ET_DATE.json"
    POLL_START_EPOCH=$SECONDS
    log INFO top5_poll "waiting for morning top5.json" path="$TOP5_FILE" max_seconds=1200
    landed=false
    for i in $(seq 1 120); do  # 120 * 10s = 1200s = 20 minutes
        if [[ -f "$TOP5_FILE" ]]; then
            landed=true
            log INFO top5_poll "top5.json detected" elapsed_seconds=$((SECONDS - POLL_START_EPOCH)) iteration=$i
            break
        fi
        # Heartbeat every minute so the log shows we're alive (not stuck).
        if (( i % 6 == 0 )); then
            log INFO top5_poll "still waiting" elapsed_seconds=$((SECONDS - POLL_START_EPOCH))
        fi
        sleep 10
    done
    if [[ "$landed" != "true" ]]; then
        log WARN top5_poll "timed out waiting for top5.json — claude will see missing file and skip" \
            elapsed_seconds=$((SECONDS - POLL_START_EPOCH))
    fi
fi

log INFO claude_invoke "invoking claude" model=haiku max_budget_usd=1.00 prompt_file="$PROMPT_FILE"
CLAUDE_START_EPOCH=$SECONDS

# Prompt goes via stdin to avoid being eaten by --add-dir (which is greedy: takes
# multiple positional dir args until the next --flag). Without this we got
# silent multi-hour hangs because claude blocked on an empty stdin.
# We `set +e` so we can capture the exit code and log a clean end-of-run marker
# rather than dying silently from `set -e`.
set +e
"$CLAUDE" --print \
    --model haiku \
    --max-budget-usd 1.00 \
    --permission-mode bypassPermissions \
    --add-dir "$PROJECT_DIR" <<<"$PROMPT"
claude_exit=$?
set -e

log INFO claude_done "claude finished" exit_code=$claude_exit duration_seconds=$((SECONDS - CLAUDE_START_EPOCH))
log INFO end "routine done" total_seconds=$((SECONDS - RUN_START_EPOCH)) exit_code=$claude_exit
exit $claude_exit
