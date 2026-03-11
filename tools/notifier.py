"""tools/notifier.py — Email delivery (stub: swap in SMTP or SendGrid)"""
import smtplib, os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(to, subject, html_body):
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    from_addr = os.getenv("FROM_EMAIL", smtp_user)

    if not smtp_user or not smtp_pass:
        print(f"[NOTIFIER] SMTP not configured — would send '{subject}' to {to}")
        return False

    if isinstance(to, str): to = [to]
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = from_addr
    msg["To"]      = ", ".join(to)
    msg.attach(MIMEText(html_body, "html"))
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as s:
            s.starttls()
            s.login(smtp_user, smtp_pass)
            s.sendmail(from_addr, to, msg.as_string())
        return True
    except Exception as e:
        print(f"[NOTIFIER] Send failed: {e}")
        return False
