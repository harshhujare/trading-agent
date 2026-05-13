"""Shared step-logger for trading-agent routines.

Appends one line per event to the file path in $RUNLOG (set by run-routine.sh).
Format:  YYYY-MM-DDTHH:MM:SSZ [LEVEL] [component/step] key=value key=value ...

Falls back to stderr when $RUNLOG is unset (e.g. when invoking a script manually
from a terminal) so output is never silently dropped.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


def _resolve_runlog_path():
    """Determine where to write log lines.

    Priority:
      1. $RUNLOG env var (set by local launchd wrapper run-routine.sh — that
         script and all its children share one process tree).
      2. journal/.current-routine marker (written by routine-setup.sh for
         remote Claude routines, where each Bash call is a fresh shell so
         env vars don't survive between invocations).
      3. None → fall back to stderr.
    """
    p = os.getenv("RUNLOG")
    if p:
        return p
    try:
        repo_root = Path(__file__).resolve().parent.parent
        marker = repo_root / "journal" / ".current-routine"
        if marker.exists():
            routine = marker.read_text().strip()
            et_date = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
            return str(repo_root / "journal" / "runlog" / f"{et_date}-{routine}.log")
    except Exception:
        pass
    return None


def _format(component, level, step, message, fields):
    parts = [
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        f"[{level}]",
        f"[{component}/{step}]",
        message,
    ]
    for k, v in fields.items():
        if v is None:
            continue
        s = str(v).replace("\n", " ")
        if " " in s:
            s = f'"{s}"'
        parts.append(f"{k}={s}")
    return " ".join(p for p in parts if p)


def log(component, step, message="", level="INFO", **fields):
    line = _format(component, level, step, message, fields)
    path = _resolve_runlog_path()
    if not path:
        print(line, file=sys.stderr)
        return
    try:
        with open(path, "a") as f:
            f.write(line + "\n")
    except OSError as e:
        print(f"runlog write failed ({e}); {line}", file=sys.stderr)
