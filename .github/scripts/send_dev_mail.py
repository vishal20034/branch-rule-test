#!/usr/bin/env python3
"""Send one Dev CI/CD email via Gmail SMTP. Strips spaces from app passwords."""
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage

def require(name):
    val = os.environ.get(name, "").strip()
    if not val:
        print(f"ERROR: secret {name} is empty.", file=sys.stderr)
        sys.exit(1)
    return val

to_addr = require("MAIL_TO")
username = require("MAIL_USERNAME")
password = os.environ.get("MAIL_PASSWORD", "").replace(" ", "").replace("\n", "").replace("\t", "")
if not password:
    print("ERROR: MAIL_PASSWORD is empty.", file=sys.stderr)
    sys.exit(1)
if "@" not in username:
    username = username + "@gmail.com"
from_addr = os.environ.get("MAIL_FROM", "").strip() or username
subject = os.environ.get("MAIL_SUBJECT", "[DEV] CI/CD")
body = os.environ.get("MAIL_BODY", "")
host = os.environ.get("MAIL_HOST", "smtp.gmail.com").strip() or "smtp.gmail.com"

msg = EmailMessage()
msg["Subject"] = subject
msg["From"] = from_addr
msg["To"] = to_addr
msg.set_content(body)

errors = []
# 587 STARTTLS then 465 SSL
try:
    with smtplib.SMTP(host, 587, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls(context=ssl.create_default_context())
        smtp.ehlo()
        smtp.login(username, password)
        smtp.send_message(msg)
    print("Sent via smtp 587 STARTTLS")
    sys.exit(0)
except Exception as e:
    errors.append(f"587: {e}")

try:
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, 465, timeout=30, context=context) as smtp:
        smtp.login(username, password)
        smtp.send_message(msg)
    print("Sent via smtp 465 SSL")
    sys.exit(0)
except Exception as e:
    errors.append(f"465: {e}")

print("ERROR: Gmail login failed.", file=sys.stderr)
print("Use a Gmail App Password (16 characters, no spaces), not the normal Gmail password.", file=sys.stderr)
print("MAIL_USERNAME must be the full address, e.g. bnag7309@gmail.com", file=sys.stderr)
for e in errors:
    print(e, file=sys.stderr)
sys.exit(1)
