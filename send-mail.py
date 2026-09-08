"""Send Gmail from the GoCD Agent. Credentials come from env, never from Git."""
import os
import smtplib
import sys
from email.mime.text import MIMEText


def main():
    user = os.environ.get("GMAIL_USER", "").strip()
    password = os.environ.get("GMAIL_APP_PASSWORD", "").strip().replace(" ", "")
    to_addr = (os.environ.get("GMAIL_TO", "") or user).strip()
    subject = sys.argv[1] if len(sys.argv) > 1 else "GoCD"
    body = sys.argv[2] if len(sys.argv) > 2 else ""

    if not user or not password or not to_addr:
        print("send-mail: skip (set GMAIL_USER and GMAIL_APP_PASSWORD)")
        return 0

    message = MIMEText(body, "plain", "utf-8")
    message["Subject"] = subject
    message["From"] = user
    message["To"] = to_addr

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(user, password)
        smtp.sendmail(user, [to_addr], message.as_string())
    print("send-mail: sent to", to_addr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
