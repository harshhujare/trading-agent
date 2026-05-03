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

# Note: the prompt file uses $(TZ=America/New_York date +%F) shell substitutions
# so the agent reads literal dates, not unsubstituted shell expressions.
PROMPT="$(eval "cat <<__PROMPT_EOF__
$(cat "$PROMPT_FILE")
__PROMPT_EOF__")"

echo "=== $(date) | starting $ROUTINE ===" >&2
# Prompt goes via stdin to avoid being eaten by --add-dir (which is greedy: takes
# multiple positional dir args until the next --flag). Without this we got
# silent multi-hour hangs because claude blocked on an empty stdin.
exec "$CLAUDE" --print \
    --model haiku \
    --max-budget-usd 1.00 \
    --permission-mode bypassPermissions \
    --add-dir "$PROJECT_DIR" <<<"$PROMPT"
