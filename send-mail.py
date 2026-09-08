"""Send Gmail from the GoCD Agent. Secrets come from process env, never from Git."""
import os
import smtplib
import sys
from email.mime.text import MIMEText

user = os.environ.get("GMAIL_USER", "").strip()
password = os.environ.get("GMAIL_APP_PASSWORD", "").strip().replace(" ", "")
to = os.environ.get("GMAIL_TO", user).strip() or user
subject = sys.argv[1] if len(sys.argv) > 1 else "GoCD"
body = sys.argv[2] if len(sys.argv) > 2 else ""

if not user or not password:
    print("send-mail: skip (set System vars GMAIL_USER and GMAIL_APP_PASSWORD)")
    sys.exit(0)

msg = MIMEText(body, "plain", "utf-8")
msg["Subject"] = subject
msg["From"] = user
msg["To"] = to

with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as smtp:
    smtp.ehlo()
    smtp.starttls()
    smtp.login(user, password)
    smtp.sendmail(user, [to], msg.as_string())
print("send-mail: sent to", to)
