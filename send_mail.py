#!/usr/bin/env python3
"""Send Gmail to GMAIL_TO. Optional 3rd arg = file to attach (PDF)."""
import os
import smtplib
import sys
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

user = (os.environ.get("GMAIL_USER") or "").strip()
password = (os.environ.get("GMAIL_APP_PASSWORD") or "").replace(" ", "")
to_raw = (os.environ.get("GMAIL_TO") or user).strip()
subject = sys.argv[1] if len(sys.argv) > 1 else "CI/CD"
body = sys.argv[2] if len(sys.argv) > 2 else subject
attach = sys.argv[3] if len(sys.argv) > 3 else ""

recipients = [p.strip() for p in to_raw.replace(";", ",").split(",") if p.strip()]

if not user or not password:
    print("send-mail: skip (set GMAIL_USER and GMAIL_APP_PASSWORD on the pipeline)")
    sys.exit(0)
if not recipients:
    print("send-mail: skip (set GMAIL_TO to one or more emails)")
    sys.exit(0)

msg = MIMEMultipart()
msg["Subject"] = subject
msg["From"] = user
msg["To"] = ", ".join(recipients)
msg.attach(MIMEText(body, "plain", "utf-8"))

path = Path(attach) if attach else None
if path and path.is_file():
    part = MIMEApplication(path.read_bytes(), Name=path.name)
    part["Content-Disposition"] = 'attachment; filename="%s"' % path.name
    msg.attach(part)
    print("send-mail: attached", path.name)

with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as smtp:
    smtp.starttls()
    smtp.login(user, password)
    smtp.sendmail(user, recipients, msg.as_string())
print("send-mail: sent to", ", ".join(recipients))
