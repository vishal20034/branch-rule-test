#!/usr/bin/env python3
"""Send a short Gmail. Skip if GMAIL_USER / GMAIL_APP_PASSWORD are unset."""
import os
import smtplib
import sys
from email.mime.text import MIMEText

user = (os.environ.get("GMAIL_USER") or "").strip()
password = (os.environ.get("GMAIL_APP_PASSWORD") or "").replace(" ", "")
to = (os.environ.get("GMAIL_TO") or user).strip()
subject = sys.argv[1] if len(sys.argv) > 1 else "CI/CD"
body = sys.argv[2] if len(sys.argv) > 2 else subject

if not user or not password:
    print("send-mail: skip (set GMAIL_USER and GMAIL_APP_PASSWORD on the pipeline)")
    sys.exit(0)

msg = MIMEText(body)
msg["Subject"] = subject
msg["From"] = user
msg["To"] = to
with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as smtp:
    smtp.starttls()
    smtp.login(user, password)
    smtp.sendmail(user, [to], msg.as_string())
print("send-mail: sent to", to)
