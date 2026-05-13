#!/usr/bin/env bash
# scripts/routine-finalize.sh — last call in every remote Claude routine.
#
# Commits journal/ changes and pushes to origin. Every step is best-effort:
# we log failures but never abort, since partial commit beats no commit when
# the sandbox is about to die.
#
# Usage: bash scripts/routine-finalize.sh <routine-name>
set -u

ROUTINE="${1:?usage: $0 <routine-name>}"
ET_DATE="$(TZ=America/New_York date +%F)"

# Re-derive RUNLOG from the marker setup.sh wrote, so finalize lands in the
# same per-run log file.
RUNLOG_DERIVED="$(pwd)/journal/runlog/${ET_DATE}-${ROUTINE}.log"
RUNLOG="${RUNLOG:-$RUNLOG_DERIVED}"

log() {
    local level="$1"; local step="$2"; local msg="$3"; shift 3
    local line
    line="$(date -u +%Y-%m-%dT%H:%M:%SZ) [$level] [finalize/$step] $msg"
    for kv in "$@"; do line+=" $kv"; done
    if [[ -w "$(dirname "$RUNLOG")" ]] 2>/dev/null; then
        echo "$line" >> "$RUNLOG"
    fi
    echo "$line"
}

log INFO start "finalizing" routine="$ROUTINE" et_date="$ET_DATE"

# Only ever stage journal/ — never the whole repo. Keeps scripts/, .env, and
# any accidentally-written secrets out of the commit.
if git add journal/; then
    log INFO add "staged journal/"
else
    log ERROR add "git add failed"
fi

if git diff --cached --quiet; then
    log INFO commit "no journal changes — skipping commit + push"
    log INFO end "finalize done (no-op)"
    exit 0
fi

commit_msg="${ROUTINE} auto-run ${ET_DATE}"
if git -c user.email="trading-agent@routines.local" \
       -c user.name="trading-agent" \
       commit -m "$commit_msg" >/dev/null; then
    log INFO commit "committed" msg="$commit_msg"
else
    log ERROR commit "git commit failed"
    exit 0  # nothing more to do; staged but unable to commit
fi

# Push with one rebase-retry. Three routines/day means another routine could
# have landed a commit between our pull-at-start and push-at-end (rare but
# possible on slow days), and we don't want to lose the commit we just made.
if git push >>"$RUNLOG" 2>&1; then
    log INFO push "pushed"
else
    log WARN push "push failed — attempting pull --rebase + retry"
    if git pull --rebase >>"$RUNLOG" 2>&1 && git push >>"$RUNLOG" 2>&1; then
        log INFO push "pushed after rebase"
    else
        log ERROR push "push retry failed — commit is local-only; will need manual recovery"
    fi
fi

log INFO end "finalize done"
