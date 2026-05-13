"""Watchdog: verify today's journal entry landed and has an EOD reflection.

Runs at 5:30 PM ET, after the EOD routine should have committed. Sends a
SendGrid alert if today's journal is missing or its End-of-Day Reflection
section is empty. Otherwise prints a one-line "all good" and exits 0.
"""

import os
import re
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import certifi
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

import sendgrid
from sendgrid.helpers.mail import Mail

from runlog import log

REPO_ROOT = Path(__file__).resolve().parent.parent
JOURNAL_DIR = REPO_ROOT / "journal"


def _et_today():
    return datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")


def _extract_section(text, heading):
    pattern = rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)"
    m = re.search(pattern, text, flags=re.MULTILINE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _alert(subject, body):
    log("watchdog", "alert", "sending alert email", level="WARN", subject=subject)
    sg = sendgrid.SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
    message = Mail(
        from_email=os.getenv("NOTIFY_FROM"),
        to_emails=os.getenv("NOTIFY_EMAIL"),
        subject=f"[trading-agent watchdog] {subject}",
        plain_text_content=body,
    )
    resp = sg.send(message)
    log("watchdog", "alert", "sendgrid response",
        level="INFO" if 200 <= resp.status_code < 300 else "ERROR",
        http_status=resp.status_code)


def check():
    et_date = _et_today()
    journal_file = JOURNAL_DIR / f"{et_date}.md"
    log("watchdog", "check", "checking journal", path=str(journal_file))

    if not journal_file.exists():
        _alert(
            f"missing journal entry for {et_date}",
            f"No journal/{et_date}.md was committed by 5:30 PM ET. "
            f"This usually means morning, trading, or EOD routine crashed mid-run. "
            f"Check the /schedule run history and journal/runlog/ for the failed routine.",
        )
        log("watchdog", "check", "journal missing — alerted", level="WARN", path=str(journal_file))
        return 1

    text = journal_file.read_text()
    reflection = _extract_section(text, "End-of-Day Reflection")
    if not reflection:
        _alert(
            f"journal {et_date} has no EOD reflection",
            f"journal/{et_date}.md exists but its '## End-of-Day Reflection' section "
            f"is missing or empty. The EOD routine likely failed between writing the "
            f"journal skeleton and the reflection step. Check journal/runlog/{et_date}-eod.log.",
        )
        log("watchdog", "check", "reflection empty — alerted", level="WARN")
        return 1

    log("watchdog", "check", "journal ok",
        path=str(journal_file), reflection_chars=len(reflection))
    print(f"watchdog ok: journal/{et_date}.md present, reflection has {len(reflection)} chars")
    return 0


if __name__ == "__main__":
    sys.exit(check())
