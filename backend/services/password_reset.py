"""Administrator password resets and the forced change that follows them.

A reset replaces the password hash, which ends every token the account already holds (tokens carry a
fingerprint of the hash, see routers/auth.py). It also writes an audit row and leaves it open until the
account's owner chooses their own password. Nothing here ever stores, returns or logs a password.
"""
from datetime import datetime, timezone
from typing import Dict, Iterable, Optional

from fastapi import HTTPException
from sqlmodel import Session, col, select

from models.user import PasswordResetEvent, PasswordResetToken, User, hash_password, password_problem
from services.fee_ledger import utc_iso

PASSWORD_CHANGE_REQUIRED = "You must choose a new password before you can continue."


def password_change_pending(session: Session, user_id: int) -> bool:
    return session.exec(
        select(PasswordResetEvent.id).where(
            PasswordResetEvent.user_id == user_id, col(PasswordResetEvent.completed_at).is_(None)
        )
    ).first() is not None


def pending_user_ids(session: Session, user_ids: Iterable[int]) -> set:
    ids = list(user_ids)
    if not ids:
        return set()
    return set(session.exec(
        select(PasswordResetEvent.user_id).where(
            col(PasswordResetEvent.user_id).in_(ids), col(PasswordResetEvent.completed_at).is_(None)
        )
    ).all())


def last_resets(session: Session, user_ids: Iterable[int]) -> Dict[int, PasswordResetEvent]:
    """The most recent reset of each account, for the administrator's list."""
    ids = list(user_ids)
    if not ids:
        return {}
    events = session.exec(
        select(PasswordResetEvent).where(col(PasswordResetEvent.user_id).in_(ids)).order_by(PasswordResetEvent.id)
    ).all()
    return {event.user_id: event for event in events}  # later rows replace earlier ones


def invalidate_tokens(session: Session, user_id: int) -> None:
    """Ends every emailed reset link of this account that has not been used yet. Does not commit.

    Called whenever the password changes, by any route, so a link requested earlier (and perhaps still sitting in
    someone's mailbox or browser) cannot undo the change that was just made."""
    now = datetime.now(timezone.utc)
    for token in session.exec(
        select(PasswordResetToken).where(PasswordResetToken.user_id == user_id, col(PasswordResetToken.used_at).is_(None))
    ).all():
        token.used_at = now
        session.add(token)


def reset_password(session: Session, account: User, administrator: User, new_password: str) -> PasswordResetEvent:
    """Sets the password and records the reset in one commit. The caller has already checked the policy."""
    account.password_hash = hash_password(new_password)
    event = PasswordResetEvent(user_id=account.id, reset_by=administrator.id)
    session.add(account)
    session.add(event)
    invalidate_tokens(session, account.id)  # an emailed link requested before this reset must not undo it
    session.commit()
    session.refresh(event)
    return event


def reset_states(session: Session, user_ids: Iterable[int]) -> dict:
    """Per account: whether a forced change is still open, and when an administrator last reset the password."""
    ids = list(user_ids)
    pending = pending_user_ids(session, ids)
    events = last_resets(session, ids)
    return {
        user_id: {"pending": user_id in pending,
                  "last": utc_iso(events[user_id].reset_at) if user_id in events else None}
        for user_id in ids
    }


def apply_admin_reset(session: Session, account: User, administrator: User, new_password: str) -> PasswordResetEvent:
    """The one way an administrator resets a password: the same policy as every other password, then the reset.
    The caller has already checked that this kind of account may be reset here."""
    problem = password_problem(new_password)
    if problem:
        raise HTTPException(status_code=422, detail=f"Password is not acceptable: {problem}.")
    return reset_password(session, account, administrator, new_password)


def complete_pending(session: Session, user_id: int, when: Optional[datetime] = None) -> None:
    """The owner has chosen their own password, so the forced change is over. Does not commit."""
    when = when or datetime.now(timezone.utc)
    for event in session.exec(
        select(PasswordResetEvent).where(
            PasswordResetEvent.user_id == user_id, col(PasswordResetEvent.completed_at).is_(None)
        )
    ).all():
        event.completed_at = when
        session.add(event)
