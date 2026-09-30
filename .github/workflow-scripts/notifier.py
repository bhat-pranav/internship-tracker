import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email(
    subject: str,
    html_body: str,
    plain_body: str,
    from_name: str = "Internship Watcher",
) -> bool:
    """Send an HTML/plaintext email alert via Gmail SMTP SSL."""
    username = os.environ.get("MAIL_USERNAME")
    password = os.environ.get("MAIL_PASSWORD")
    to_email = os.environ.get("MAIL_TO")

    if not (username and password and to_email):
        print(
            "WARN: Email secrets (MAIL_USERNAME, MAIL_PASSWORD, MAIL_TO) "
            "not configured; skipping email dispatch.",
            file=sys.stderr,
        )
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{username}>"
    msg["To"] = to_email

    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(username, password)
            server.sendmail(username, [to_email], msg.as_string())
        print(f"Successfully sent email alert: '{subject}' to {to_email}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to send email via SMTP: {e}", file=sys.stderr)
        return False
