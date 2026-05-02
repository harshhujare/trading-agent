# scripts/notify.py — sends today's journal as an email
import os, sys
import certifi
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

import sendgrid
from sendgrid.helpers.mail import Mail

def send_digest(journal_path):
    with open(journal_path, 'r') as f:
        content = f.read()

    sg = sendgrid.SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
    message = Mail(
        from_email=os.getenv("NOTIFY_FROM"),
        to_emails=os.getenv("NOTIFY_EMAIL"),
        subject=f"Trading Agent Report — {journal_path.split('/')[-1]}",
        plain_text_content=content
    )
    response = sg.send(message)
    print(f"sendgrid status={response.status_code} msg-id={response.headers.get('X-Message-Id')}")
    return response

if __name__ == "__main__":
    send_digest(sys.argv[1])
