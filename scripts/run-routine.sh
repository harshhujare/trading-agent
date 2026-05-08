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

# Load .env so the trading scripts have Alpaca + SendGrid keys
set -a
source ./.env
set +a

# Self-heal TLS for SendGrid (matches what notify.py does internally)
export SSL_CERT_FILE="$(/usr/local/bin/python3 -c 'import certifi; print(certifi.where())')"

# Resolve the date placeholder safely. We deliberately avoid `eval` here: an
# earlier version used `eval cat <<EOF` which was happy to interpret any shell
# metachar in the prompt (`{a|b}`, `<placeholder>`, `|`, backslashes, etc.)
# and crashed both trading + eod runs. sed substitution touches only the literal
# placeholder __ET_DATE__ and leaves all other characters in the prompt intact.
ET_DATE="$(TZ=America/New_York date +%F)"
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
    for _ in $(seq 1 120); do  # 120 * 10s = 1200s = 20 minutes
        [[ -f "$TOP5_FILE" ]] && break
        sleep 10
    done
fi

echo "=== $(date) | starting $ROUTINE ===" >&2
# Prompt goes via stdin to avoid being eaten by --add-dir (which is greedy: takes
# multiple positional dir args until the next --flag). Without this we got
# silent multi-hour hangs because claude blocked on an empty stdin.
exec "$CLAUDE" --print \
    --model haiku \
    --max-budget-usd 1.00 \
    --permission-mode bypassPermissions \
    --add-dir "$PROJECT_DIR" <<<"$PROMPT"
