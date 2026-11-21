"""Self-service "forgot password" for teachers and parents.

The account's owner asks for a reset link by email. The link carries a random token that works once and for
60 minutes. Only a SHA-256 of the token is stored. Nothing here logs a token, a link or an address.

Choosing a new password replaces the password hash, which ends every session the account holds (tokens carry
a fingerprint of the hash, see routers/auth.py). Administrators keep their own recovery path and cannot be reset
here, and the administrator's reset of a teacher or parent (services/password_reset.py) is unchanged.
"""
import hashlib
import logging
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from sqlalchemy import func, update
from sqlmodel import Session, col, select

import config
from database import engine
from models.user import ROLE_PARENT, ROLE_TEACHER, PasswordResetToken, User, hash_password
from services import email_service
from services.login_throttle import LoginThrottle
from services.password_reset import complete_pending, invalidate_tokens

logger = logging.getLogger("educore.password_reset")

SELF_SERVICE_ROLES = frozenset({ROLE_TEACHER, ROLE_PARENT})
HOUR = 60 * 60

# Every request counts, whether or not the address belongs to an account, so the limits reveal nothing.
request_throttle_by_email = LoginThrottle(3, HOUR)
request_throttle_by_address = LoginThrottle(10, HOUR)
# Wrong or expired tokens, per address.
token_failure_throttle = LoginThrottle(10, 15 * 60)


def clear_throttles() -> None:
    request_throttle_by_email.clear()
    request_throttle_by_address.clear()
    token_failure_throttle.clear()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalise_email(value: str) -> str:
    return (value or "").strip().lower()


def eligible_account_for_email(session: Session, email: str) -> Optional[User]:
    """The one active teacher or parent account with this email. None when there is none, or when more than one
    account shares it, because a link must never go to an address that cannot say whose account it is."""
    email = normalise_email(email)
    if not email:
        return None
    matches = session.exec(select(User).where(func.lower(User.email) == email)).all()
    if len(matches) != 1:
        return None
    account = matches[0]
    if not account.is_active or (account.role or "").lower() not in SELF_SERVICE_ROLES:
        return None
    return account


def issue_token(session: Session, user: User) -> str:
    """A new link replaces any earlier one. Returns the raw token, which exists nowhere else."""
    invalidate_tokens(session, user.id)
    raw = secrets.token_urlsafe(32)
    now = _now()
    session.add(PasswordResetToken(
        user_id=user.id,
        token_hash=_digest(raw),
        created_at=now,
        expires_at=now + timedelta(minutes=config.PASSWORD_RESET_TOKEN_MINUTES),
    ))
    session.commit()
    return raw


def find_valid_token(session: Session, raw_token: str) -> Optional[PasswordResetToken]:
    """The token row if it is unused and not expired and its account may still use self-service."""
    if not raw_token:
        return None
    row = session.exec(select(PasswordResetToken).where(PasswordResetToken.token_hash == _digest(raw_token))).first()
    if row is None or row.used_at is not None or row.expires_at <= _now():
        return None
    account = session.get(User, row.user_id)
    if account is None or not account.is_active or (account.role or "").lower() not in SELF_SERVICE_ROLES:
        return None
    return row


class ResetLinkUnusable(Exception):
    """The link was spent, replaced or cancelled before this submission could use it."""


def complete_reset(session: Session, row: PasswordResetToken, new_password: str) -> User:
    """Sets the password the owner chose. The caller has checked the token and the password policy.

    The link is claimed first, with one conditional UPDATE, so when two submissions of the same link arrive at the
    same moment only one can win. The other changes nothing and gets ResetLinkUnusable."""
    new_hash = hash_password(new_password)  # slow, so it is done before the database's write lock is taken
    claimed = session.exec(
        update(PasswordResetToken)
        .where(PasswordResetToken.id == row.id, col(PasswordResetToken.used_at).is_(None))
        .values(used_at=_now())
        .execution_options(synchronize_session=False)
    )
    if claimed.rowcount != 1:
        session.rollback()
        raise ResetLinkUnusable()
    account = session.get(User, row.user_id)
    account.password_hash = new_hash
    session.add(account)
    invalidate_tokens(session, account.id)  # any other link still open
    complete_pending(session, account.id)  # they chose their own password, so an administrator's forced change is over
    session.commit()
    session.refresh(account)
    return account


# ── Work done after the reply ───────────────────────────────────────────────

# Asking for a link only queues work here and returns. Whether the address belongs to an account decides how long
# the lookup, the new link and the email take (a link is a database write, several times slower than a miss),
# so doing them before replying would tell anyone with a stopwatch which addresses are registered. A thread of our
# own, not the web framework's background tasks, keeps the reply independent of when the host ends a response.
# One worker keeps requests in order and lets tests wait for everything queued so far.
_background_work = ThreadPoolExecutor(max_workers=1, thread_name_prefix="password-reset")


def run_in_background(function: Callable[..., None], *args) -> None:
    _background_work.submit(function, *args)


def drain_background_work() -> None:
    """Waits until everything queued so far has finished. Used by tests."""
    _background_work.submit(lambda: None).result(timeout=60)


def send_reset_link_if_eligible(email: str) -> None:
    """Looks the address up and, if it belongs to an active teacher or parent, issues a link and emails it.

    Runs after the reply has gone. Never raises, and never logs the address, the link or anything the database says."""
    try:
        if not email_service.email_enabled():
            return
        with Session(engine) as session:
            account = eligible_account_for_email(session, email)
            if account is None:
                return
            recipient, name = account.email, account.full_name
            raw_token = issue_token(session, account)
        send_reset_email(recipient, name, raw_token)
    except Exception as error:
        logger.warning("A password reset request could not be completed (%s).", type(error).__name__)


# ── Messages ────────────────────────────────────────────────────────────────

def reset_link(raw_token: str) -> str:
    # The token sits after "#", which browsers never send to a server or put in a Referer header.
    return f"{config.PASSWORD_RESET_URL_BASE}/reset-password#token={raw_token}"


def send_reset_email(to: str, full_name: Optional[str], raw_token: str) -> None:
    greeting = f"Hello {full_name}," if full_name else "Hello,"
    email_service.send_email(
        to,
        f"Reset your {config.SCHOOL_NAME} password",
        f"{greeting}\n\n"
        f"Someone asked to reset the password for your {config.SCHOOL_NAME} account. To choose a new password, "
        f"open this link within {config.PASSWORD_RESET_TOKEN_MINUTES} minutes. It works once.\n\n"
        f"{reset_link(raw_token)}\n\n"
        "If you did not ask for this, you can ignore this message. Your password will not change.\n",
    )


def send_password_changed_email(to: str, full_name: Optional[str]) -> None:
    greeting = f"Hello {full_name}," if full_name else "Hello,"
    email_service.send_email(
        to,
        f"Your {config.SCHOOL_NAME} password was changed",
        f"{greeting}\n\nThe password for your {config.SCHOOL_NAME} account was just changed, and you were signed "
        f"out everywhere. If this was not you, contact the school office at once.\n",
    )


def send_email_changed_notice(old_address: str, full_name: Optional[str]) -> None:
    """Goes to the address that was replaced, so a quiet change of email cannot hide an account takeover."""
    greeting = f"Hello {full_name}," if full_name else "Hello,"
    email_service.send_email(
        old_address,
        f"The email address on your {config.SCHOOL_NAME} account was changed",
        f"{greeting}\n\nThe school office changed the email address on your {config.SCHOOL_NAME} account. "
        "Password reset links will no longer be sent to this address. If this is a surprise, contact the school office.\n",
    )
