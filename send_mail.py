#!/usr/bin/env python3
"""Send Gmail to every address in GMAIL_TO (comma or semicolon separated)."""
import os
import smtplib
import sys
from email.mime.text import MIMEText

user = (os.environ.get("GMAIL_USER") or "").strip()
password = (os.environ.get("GMAIL_APP_PASSWORD") or "").replace(" ", "")
to_raw = (os.environ.get("GMAIL_TO") or user).strip()
subject = sys.argv[1] if len(sys.argv) > 1 else "CI/CD"
body = sys.argv[2] if len(sys.argv) > 2 else subject

recipients = [p.strip() for p in to_raw.replace(";", ",").split(",") if p.strip()]

if not user or not password:
    print("send-mail: skip (set GMAIL_USER and GMAIL_APP_PASSWORD on the pipeline)")
    sys.exit(0)
if not recipients:
    print("send-mail: skip (set GMAIL_TO to one or more emails)")
    sys.exit(0)

msg = MIMEText(body, "plain", "utf-8")
msg["Subject"] = subject
msg["From"] = user
msg["To"] = ", ".join(recipients)
with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as smtp:
    smtp.starttls()
    smtp.login(user, password)
    smtp.sendmail(user, recipients, msg.as_string())
print("send-mail: sent to", ", ".join(recipients))
