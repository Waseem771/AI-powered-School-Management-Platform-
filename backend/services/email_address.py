"""The one place that decides what a registered email address may look like.

An account has exactly one address: plain ASCII, one mailbox, no display name, no comments, no list. That keeps a
reset link from ever being delivered to a second recipient, and keeps anything that looks like a mail header
(a newline, a comma, angle brackets) out of the "To" line. Used for creating accounts, changing an address and the
"forgot password" request, so all three agree.
"""
import re
from typing import Optional

MAX_LENGTH = 254
MAX_LOCAL_LENGTH = 64
_ATEXT = r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+"
_LOCAL = re.compile(rf"{_ATEXT}(?:\.{_ATEXT})*")
_LABEL = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?")
_TLD = re.compile(r"[A-Za-z]{2,63}")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
MESSAGE = "Enter one valid email address, such as name@example.com"


def email_problem(value: str) -> Optional[str]:
    """Why this is not one valid address, or None. Expects the text as typed; surrounding spaces are not a problem."""
    if not isinstance(value, str) or _CONTROL.search(value):
        return "it contains a line break or control character"
    address = value.strip()
    if not address or len(address) > MAX_LENGTH:
        return "it is empty or too long"
    if address.count("@") != 1:
        return "it must have exactly one @"
    local, domain = address.split("@")
    if len(local) > MAX_LOCAL_LENGTH or not _LOCAL.fullmatch(local):
        return "the part before @ has characters an address cannot have (spaces, commas, quotes and brackets are not allowed)"
    labels = domain.split(".")
    if len(labels) < 2 or not all(_LABEL.fullmatch(label) for label in labels) or not _TLD.fullmatch(labels[-1]):
        return "the part after @ is not a valid domain"
    return None


def clean_email(value: str) -> str:
    """The address trimmed and in lower case. Raises ValueError, with a message for the user, if it is not valid."""
    if email_problem(value):
        raise ValueError(MESSAGE)
    return value.strip().lower()


def optional_email(value: Optional[str]) -> Optional[str]:
    """For an optional field: None or blank means no address; anything else must be one valid address."""
    if value is None or (isinstance(value, str) and not value.strip() and not _CONTROL.search(value)):
        return None
    return clean_email(value)
