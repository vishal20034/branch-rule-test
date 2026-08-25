#!/usr/bin/env python3
"""Send one Dev CI/CD email via Gmail SMTP. Used by Email 1, 2 and 3."""

# Read environment variables (GitHub fills these from Secrets).
import os
# Talk to Gmail's mail server.
import smtplib
# Encrypt the login (TLS/SSL).
import ssl
# Exit 1 so the GitHub job turns red if send fails.
import sys
# Build a simple email (From, To, Subject, body).
from email.message import EmailMessage


def require(name):
    # Read one required secret. Fail clearly if it is missing.
    val = os.environ.get(name, "").strip()
    if not val:
        print(f"ERROR: secret {name} is empty.", file=sys.stderr)
        sys.exit(1)
    return val


# Who receives the mail.
to_addr = require("MAIL_TO")
# Gmail login user (must be a full address).
username = require("MAIL_USERNAME")
# App Password: remove spaces/newlines in case it was pasted as "xxxx xxxx ...".
password = os.environ.get("MAIL_PASSWORD", "").replace(" ", "").replace("\n", "").replace("\t", "")
if not password:
    print("ERROR: MAIL_PASSWORD is empty.", file=sys.stderr)
    sys.exit(1)
# If someone saved MAIL_USERNAME as "bnag7309" without @gmail.com, add it.
if "@" not in username:
    username = username + "@gmail.com"
# From address. If empty, use the login user.
from_addr = os.environ.get("MAIL_FROM", "").strip() or username
# Subject and body come from the workflow job.
subject = os.environ.get("MAIL_SUBJECT", "[DEV] CI/CD")
body = os.environ.get("MAIL_BODY", "")
# Mail server. Empty secret → Gmail.
host = os.environ.get("MAIL_HOST", "smtp.gmail.com").strip() or "smtp.gmail.com"

# Build the message.
msg = EmailMessage()
msg["Subject"] = subject
msg["From"] = from_addr
msg["To"] = to_addr
msg.set_content(body)

errors = []

# Try Gmail port 587 with STARTTLS first (normal way).
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

# If 587 failed, try port 465 SSL.
try:
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(host, 465, timeout=30, context=context) as smtp:
        smtp.login(username, password)
        smtp.send_message(msg)
    print("Sent via smtp 465 SSL")
    sys.exit(0)
except Exception as e:
    errors.append(f"465: {e}")

# Both ports failed — almost always a wrong App Password (Gmail 535).
print("ERROR: Gmail login failed.", file=sys.stderr)
print("Use a Gmail App Password (16 characters, no spaces), not the normal Gmail password.", file=sys.stderr)
print("MAIL_USERNAME must be the full address, e.g. bnag7309@gmail.com", file=sys.stderr)
for e in errors:
    print(e, file=sys.stderr)
sys.exit(1)
