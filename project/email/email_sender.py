"""Email delivery module for OH MCD report notifications."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path

LOGGER = logging.getLogger(__name__)


class EmailSender:
    """Send summary email with workbook attachment."""

    def __init__(self, smtp_server: str, smtp_port: int, sender: str, recipients: list[str], subject: str) -> None:
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender = sender
        self.recipients = recipients
        self.subject = subject

    def send(self, body: str, attachment_path: str) -> None:
        """Send plain-text email with Excel attachment."""
        attachment = Path(attachment_path)

        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = ", ".join(self.recipients)
        message["Subject"] = self.subject
        message.set_content(body)

        with attachment.open("rb") as file:
            payload = file.read()
            message.add_attachment(
                payload,
                maintype="application",
                subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=attachment.name,
            )

        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as smtp:
                smtp.send_message(message)
            LOGGER.info("Email sent to %s", self.recipients)
        except Exception:
            LOGGER.exception("Failed to send report email")
            raise
