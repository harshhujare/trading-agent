# scripts/notify.py — sends today's journal as an email
import os, sys
import certifi
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

import sendgrid
from sendgrid.helpers.mail import Mail

from runlog import log

def send_digest(journal_path):
    with open(journal_path, 'r') as f:
        content = f.read()

    to_email = os.getenv("NOTIFY_EMAIL")
    log("notify", "send", "sending digest",
        journal=journal_path, to=to_email, content_bytes=len(content))

    sg = sendgrid.SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
    message = Mail(
        from_email=os.getenv("NOTIFY_FROM"),
        to_emails=to_email,
        subject=f"Trading Agent Report — {journal_path.split('/')[-1]}",
        plain_text_content=content
    )
    response = sg.send(message)
    msg_id = response.headers.get('X-Message-Id')
    log("notify", "send", "sendgrid response",
        level="INFO" if 200 <= response.status_code < 300 else "ERROR",
        http_status=response.status_code, msg_id=msg_id)
    print(f"sendgrid status={response.status_code} msg-id={msg_id}")
    return response

if __name__ == "__main__":
    send_digest(sys.argv[1])
