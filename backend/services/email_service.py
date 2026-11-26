"""Sending email. Used only for password reset messages.

Backends (config.EMAIL_BACKEND): "smtp" sends for real, "file" writes an .eml file to a local folder so nothing
leaves the machine, "memory" keeps messages in a list (tests only), anything else sends nothing. Production
accepts only "smtp". Nothing here logs an address, a subject or a body, because they hold reset links.
"""
import logging
import smtplib
import ssl
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import getaddresses
from typing import List

import config

logger = logging.getLogger("educore.email")


@dataclass(frozen=True)
class OutboundEmail:
    to: str
    subject: str
    body: str


# The "memory" backend appends here. Tests read and clear it.
outbox: List[OutboundEmail] = []


def _backend() -> str:
    backend = (config.EMAIL_BACKEND or "").strip().lower()
    if config.IS_PRODUCTION and backend != "smtp":
        return ""
    if config.DEMO_MODE and backend == "smtp":
        return ""  # a copy holding made-up records never sends real email, whatever its settings say
    return backend


def email_enabled() -> bool:
    backend = _backend()
    if backend == "smtp":
        return bool(config.SMTP_HOST and config.EMAIL_FROM)
    return backend in {"file", "memory"}


def _build(message: OutboundEmail) -> EmailMessage:
    built = EmailMessage()
    built["From"] = config.EMAIL_FROM
    built["To"] = message.to
    built["Subject"] = message.subject
    built["Date"] = datetime.now(timezone.utc)
    built.set_content(message.body)
    return built


def _send_smtp(built: EmailMessage) -> None:
    if config.SMTP_SECURITY == "ssl":
        with smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, timeout=15, context=ssl.create_default_context()) as server:
            _login_and_send(server, built)
        return
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=15) as server:
        if config.SMTP_SECURITY != "none":
            server.starttls(context=ssl.create_default_context())
        _login_and_send(server, built)


def _login_and_send(server: smtplib.SMTP, built: EmailMessage) -> None:
    if config.SMTP_USERNAME:
        server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
    server.send_message(built)


def send_email(to: str, subject: str, body: str) -> bool:
    """True if the message was handed to the backend. Never raises, and never logs what it was sending."""
    message = OutboundEmail(to=to, subject=subject, body=body)
    backend = _backend()
    # A link goes to exactly one mailbox: refuse anything a mail header would read as several, or as another one.
    if getaddresses([to]) != [("", to)]:
        return False
    try:
        if backend == "smtp" and email_enabled():
            _send_smtp(_build(message))
        elif backend == "file":
            config.EMAIL_OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
            (config.EMAIL_OUTBOX_DIR / f"{stamp}-{uuid.uuid4().hex[:8]}.eml").write_bytes(bytes(_build(message)))
        elif backend == "memory":
            outbox.append(message)
        else:
            return False
        return True
    except Exception as error:  # delivery problems must never break a request or reveal anything
        logger.warning("An email could not be delivered (%s).", type(error).__name__)
        return False
