#!/usr/bin/env bash
# scripts/routine-setup.sh — first call in every remote Claude routine.
#
# Assumes the repo has already been cloned and this is invoked from the project
# root. Validates required env, prepares journal/runlog/<date>-<routine>.log,
# and writes journal/.current-routine so subsequent Bash calls in this session
# (each a fresh shell) can re-derive the RUNLOG path via scripts/runlog.py.
#
# Usage: bash scripts/routine-setup.sh <routine-name>
#   where <routine-name> is one of: morning | trading | eod | watchdog
set -u

ROUTINE="${1:?usage: $0 <routine-name>}"
ET_DATE="$(TZ=America/New_York date +%F)"

mkdir -p journal/runlog
RUNLOG="$(pwd)/journal/runlog/${ET_DATE}-${ROUTINE}.log"

log() {
    local level="$1"; local step="$2"; local msg="$3"; shift 3
    local line
    line="$(date -u +%Y-%m-%dT%H:%M:%SZ) [$level] [setup/$step] $msg"
    for kv in "$@"; do line+=" $kv"; done
    echo "$line" >> "$RUNLOG"
    echo "$line"
}

log INFO start "setup starting" routine="$ROUTINE" et_date="$ET_DATE"

# Required for every routine.
missing=()
for var in APCA_API_KEY_ID APCA_API_SECRET_KEY APCA_BASE_URL; do
    [[ -n "${!var:-}" ]] || missing+=("$var")
done
# EOD + watchdog also need SendGrid.
if [[ "$ROUTINE" == "eod" || "$ROUTINE" == "watchdog" ]]; then
    for var in SENDGRID_API_KEY NOTIFY_FROM NOTIFY_EMAIL; do
        [[ -n "${!var:-}" ]] || missing+=("$var")
    done
fi
if (( ${#missing[@]} > 0 )); then
    log ERROR env "missing required env vars" missing="${missing[*]}"
    exit 1
fi

# Self-heal TLS for SendGrid (matches what notify.py does internally).
if command -v python3 >/dev/null 2>&1; then
    export SSL_CERT_FILE="$(python3 -c 'import certifi; print(certifi.where())' 2>/dev/null || true)"
fi

# Marker file lets each subsequent Bash call (fresh shell) recover the RUNLOG
# path without us having to thread it through every python invocation. The
# runlog helper falls back to this marker when $RUNLOG is unset.
echo "$ROUTINE" > journal/.current-routine

log INFO env "env validated" alpaca_base="$APCA_BASE_URL" \
    sendgrid_present=$([[ -n "${SENDGRID_API_KEY:-}" ]] && echo true || echo false)
log INFO ready "setup complete" runlog="$RUNLOG" marker="journal/.current-routine"
