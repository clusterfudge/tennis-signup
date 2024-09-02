import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
logging.basicConfig(level=logging.INFO)


def send_email(subject, body, recipient=None):
    SENDER_EMAIL = os.environ.get('SENDER_EMAIL')
    SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD')
    SMTP_SERVER = os.environ.get('SMTP_SERVER')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))  # Default to 587 for STARTTLS
    RECIPIENT_EMAIL = recipient or os.environ.get('RECIPIENT_EMAIL')

    if not all([SENDER_EMAIL, SENDER_PASSWORD, SMTP_SERVER, SMTP_PORT, RECIPIENT_EMAIL]):
        raise ValueError("Sender email, password, SMTP server, SMTP port, or recipient email not set in environment variables")

    message = MIMEMultipart()
    message['From'] = f"Cron Daemon <{SENDER_EMAIL}>"
    message['To'] = RECIPIENT_EMAIL
    message['Subject'] = subject
    message.attach(MIMEText(body, 'html'))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            if server.has_extn('STARTTLS'):
                server.starttls()
                server.ehlo()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(message)
        logging.debug("Email sent successfully using STARTTLS")
        return True
    except Exception:
        logging.exception(f"STARTTLS connection failed")
        return False


def send_plan_email(schedule_id, plan_html):
    subject = f"Weekly Tennis Plan"
    body = plan_html
    success = send_email(subject, body)
    if not success:
        logging.error(f"Failed to send email for schedule {schedule_id}")