"""Teacher accounts (managed by an administrator) and the teacher's own portal endpoint.

Teachers sign in through the same /auth/login as everyone else. Their accounts are ordinary rows in
`users` with role "teacher". Only an administrator can create, list, activate or deactivate them.
A teacher can reach nothing else: every school-data route refuses portal-only roles (see
`routers.auth.get_current_user`).
"""
import re
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
from sqlmodel import Session, select

from database import get_session
from models.user import ROLE_TEACHER, User, hash_password, password_problem, verify_password
from routers.auth import MAX_CREDENTIAL_LENGTH, _record_failure, _reject_if_throttled, _throttle_keys, require_roles
from services.email_address import optional_email
from services.password_reset import apply_admin_reset, reset_states
from services.self_service_reset import invalidate_tokens, send_email_changed_notice

router = APIRouter(prefix="/teachers", tags=["Teacher accounts"])
portal_router = APIRouter(prefix="/teacher", tags=["Teacher portal"])

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,49}$")

require_admin = require_roles("admin")
require_teacher = require_roles(ROLE_TEACHER)


class TeacherCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=2, max_length=100)
    email: Optional[str] = Field(default=None, max_length=254)
    password: str = Field(min_length=1, max_length=MAX_CREDENTIAL_LENGTH)

    @field_validator("username")
    @classmethod
    def _username(cls, value: str) -> str:
        value = value.strip()
        if not USERNAME_PATTERN.match(value):
            raise ValueError("Username must be 3-50 letters, numbers, dots, dashes or underscores")
        return value

    @field_validator("full_name")
    @classmethod
    def _full_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Enter the teacher's full name")
        return value

    @field_validator("email")
    @classmethod
    def _email(cls, value: Optional[str]) -> Optional[str]:
        return optional_email(value)


class PasswordReset(BaseModel):
    new_password: str = Field(min_length=1, max_length=MAX_CREDENTIAL_LENGTH)


class EmailChange(BaseModel):
    """An administrator changes (or clears) the email on a teacher's or parent's account. The administrator's own
    password is asked for again, because that address decides who can reset the account."""

    email: Optional[str] = Field(default=None, max_length=254)
    admin_password: str = Field(min_length=1, max_length=MAX_CREDENTIAL_LENGTH)

    @field_validator("email")
    @classmethod
    def _email(cls, value: Optional[str]) -> Optional[str]:
        return optional_email(value)


def change_account_email(
    session: Session, account: User, administrator: User, payload: EmailChange, http_request: Request,
    background: BackgroundTasks,
) -> None:
    """Shared by teachers and parents. Checks the administrator's password, refuses an address another account
    uses, ends any reset link already sent, and tells the old address. Never returns or logs a password."""
    username_key, address_key = _throttle_keys(administrator.username, http_request)
    _reject_if_throttled(username_key, address_key)
    if not verify_password(payload.admin_password, administrator.password_hash):
        _record_failure(username_key, address_key)
        raise HTTPException(status_code=400, detail="Your administrator password is incorrect.")

    if payload.email:
        taken = session.exec(
            select(User).where(func.lower(User.email) == payload.email, User.id != account.id)
        ).first()
        if taken:
            raise HTTPException(status_code=409, detail="That email address is already used by another account.")

    old_address = account.email
    if payload.email == old_address:
        return  # nothing to change
    account.email = payload.email
    session.add(account)
    invalidate_tokens(session, account.id)  # a link sent to the old address must not work any more
    session.commit()
    if old_address:
        background.add_task(send_email_changed_notice, old_address, account.full_name)


class TeacherRead(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    email: Optional[str]
    role: str
    is_active: bool
    created_at: datetime
    # After an administrator's reset: the teacher must still choose their own password, and when it was reset.
    must_change_password: bool = False
    last_password_reset: Optional[str] = None


def _read(user: User, reset_state: Optional[dict] = None) -> TeacherRead:
    """Built field by field, so the password hash can never leak into a response."""
    return TeacherRead(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        must_change_password=bool(reset_state and reset_state["pending"]),
        last_password_reset=reset_state["last"] if reset_state else None,
    )


def _get_teacher(session: Session, teacher_id: int) -> User:
    teacher = session.get(User, teacher_id)
    # Only teacher accounts can be managed here, so this can never touch an administrator.
    if teacher is None or (teacher.role or "").lower() != ROLE_TEACHER:
        raise HTTPException(status_code=404, detail="Teacher not found")
    return teacher


def _set_active(session: Session, teacher_id: int, active: bool) -> TeacherRead:
    teacher = _get_teacher(session, teacher_id)
    if teacher.is_active != active:
        teacher.is_active = active
        session.add(teacher)
        session.commit()
        session.refresh(teacher)
    return _read(teacher, reset_states(session, [teacher.id])[teacher.id])


@router.post("", response_model=TeacherRead, status_code=status.HTTP_201_CREATED)
def create_teacher(
    payload: TeacherCreate,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    problem = password_problem(payload.password)
    if problem:
        raise HTTPException(status_code=422, detail=f"Password is not acceptable: {problem}.")

    # Compared ignoring case, so "Sara" and "sara" cannot both exist.
    if session.exec(select(User).where(func.lower(User.username) == payload.username.lower())).first():
        raise HTTPException(status_code=409, detail="That username is already taken.")
    if payload.email and session.exec(select(User).where(func.lower(User.email) == payload.email)).first():
        raise HTTPException(status_code=409, detail="That email address is already used by another account.")

    teacher = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=ROLE_TEACHER,
        full_name=payload.full_name,
        email=payload.email,
        is_active=True,
    )
    session.add(teacher)
    session.commit()
    session.refresh(teacher)
    return _read(teacher)


@router.get("", response_model=List[TeacherRead])
def list_teachers(
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    teachers = session.exec(select(User).where(User.role == ROLE_TEACHER).order_by(User.full_name, User.username)).all()
    states = reset_states(session, [teacher.id for teacher in teachers])
    return [_read(teacher, states[teacher.id]) for teacher in teachers]


@router.post("/{teacher_id}/activate", response_model=TeacherRead)
def activate_teacher(
    teacher_id: int,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    return _set_active(session, teacher_id, True)


@router.post("/{teacher_id}/deactivate", response_model=TeacherRead)
def deactivate_teacher(
    teacher_id: int,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    return _set_active(session, teacher_id, False)


@router.post("/{teacher_id}/reset-password")
def reset_teacher_password(
    teacher_id: int,
    payload: PasswordReset,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin),
):
    """Sets a new password for a teacher who forgot theirs. It ends their sessions at once and makes them choose
    their own at next sign-in. Same rules as for parents: the usual password policy, stored only as a hash,
    never returned or logged, and an audit row without the password."""
    teacher = _get_teacher(session, teacher_id)
    apply_admin_reset(session, teacher, admin, payload.new_password)
    session.refresh(teacher)
    return {
        "message": "Password reset. The teacher must choose a new password at next sign-in.",
        "teacher": _read(teacher, reset_states(session, [teacher.id])[teacher.id]),
    }


@router.put("/{teacher_id}/email", response_model=TeacherRead)
def update_teacher_email(
    teacher_id: int,
    payload: EmailChange,
    http_request: Request,
    background: BackgroundTasks,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin),
):
    """Sets or clears the email a teacher can use to reset their own password. Needs the administrator's password."""
    teacher = _get_teacher(session, teacher_id)
    change_account_email(session, teacher, admin, payload, http_request, background)
    session.refresh(teacher)
    return _read(teacher, reset_states(session, [teacher.id])[teacher.id])


@portal_router.get("/profile", response_model=TeacherRead)
def teacher_profile(teacher: User = Depends(require_teacher)):
    """The signed-in teacher's own account, read from the database rather than from the token."""
    return _read(teacher)
