import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from calculations.calculations import app
from helpers.prisma import prisma

LOG = logging.getLogger(__name__)


def _resolve_recipients(ticket_id: int) -> list[str]:
    recipients = []
    connected_here = False
    try:
        if not prisma.is_connected():
            prisma.connect()
            connected_here = True
        rows = prisma.supportrecipient.find_many(where={"ticketId": ticket_id})
        recipients = [row.email.strip().lower() for row in rows if row.email]
    except Exception as exc:
        LOG.warning("Could not load support recipients from DB: %s", exc)
    finally:
        if connected_here:
            try:
                prisma.disconnect()
            except Exception:
                pass

    if len(recipients) > 0:
        return recipients

    env_recipients = os.getenv("SUPPORT_EMAIL_RECIPIENTS", "")
    return [email.strip().lower() for email in env_recipients.split(",") if email.strip()]


def _send_mail(subject: str, body: str, recipients: list[str]) -> bool:
    smtp_host = os.getenv("SUPPORT_SMTP_HOST", os.getenv("SMTP_HOST"))
    smtp_port = int(os.getenv("SUPPORT_SMTP_PORT", os.getenv("SMTP_PORT", "587")))
    smtp_user = os.getenv("SUPPORT_SMTP_USER", os.getenv("SMTP_USER"))
    smtp_password = os.getenv("SUPPORT_SMTP_PASSWORD", os.getenv("SMTP_PASSWORD"))
    smtp_from = os.getenv("SUPPORT_SMTP_FROM", os.getenv("SMTP_FROM"))

    if not smtp_host or not smtp_from or len(recipients) == 0:
        LOG.warning("Support email skipped: missing SMTP config or recipients")
        return False

    msg = MIMEMultipart()
    msg["From"] = smtp_from
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as smtp:
            if smtp_port == 587:
                smtp.starttls()
            if smtp_user and smtp_password:
                smtp.login(smtp_user, smtp_password)
            smtp.send_message(msg)
        return True
    except Exception as exc:
        LOG.error("Support email could not be sent: %s", exc)
        return False


@app.task(bind=True, name="send_support_notification")
def send_support_notification(
    self,
    event_type: str,
    ticket_id: int,
    actor_email: str | None = None,
    actor_name: str | None = None,
    new_status: str | None = None,
):
    recipients = _resolve_recipients(ticket_id)
    if len(recipients) == 0:
        LOG.info("No recipients for support notification on ticket %s", ticket_id)
        return {"sent": False, "reason": "no-recipients"}

    actor = actor_name or actor_email or "unknown actor"
    subject = f"[AUGUR Support] Ticket #{ticket_id} update"
    body = f"Ticket #{ticket_id} has a new update.\n\nEvent: {event_type}\nActor: {actor}\n"
    if new_status:
        body += f"Status: {new_status}\n"

    was_sent = _send_mail(subject=subject, body=body, recipients=recipients)
    return {"sent": was_sent, "recipients": recipients, "eventType": event_type}
