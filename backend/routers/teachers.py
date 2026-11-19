"""Teacher accounts (managed by an administrator) and the teacher's own portal endpoint.

Teachers sign in through the same /auth/login as everyone else. Their accounts are ordinary rows in
`users` with role "teacher". Only an administrator can create, list, activate or deactivate them.
A teacher can reach nothing else: every school-data route refuses portal-only roles (see
`routers.auth.get_current_user`).
"""
import re
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
from sqlmodel import Session, select

from database import get_session
from models.user import ROLE_TEACHER, User, hash_password, password_problem
from routers.auth import MAX_CREDENTIAL_LENGTH, require_roles

router = APIRouter(prefix="/teachers", tags=["Teacher accounts"])
portal_router = APIRouter(prefix="/teacher", tags=["Teacher portal"])

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,49}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

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
        if value is None:
            return None
        value = value.strip().lower()
        if not value:
            return None
        if not EMAIL_PATTERN.match(value):
            raise ValueError("Enter a valid email address")
        return value


class TeacherRead(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    email: Optional[str]
    role: str
    is_active: bool
    created_at: datetime


def _read(user: User) -> TeacherRead:
    """Built field by field, so the password hash can never leak into a response."""
    return TeacherRead(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
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
    return _read(teacher)


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
    return [_read(teacher) for teacher in teachers]


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


@portal_router.get("/profile", response_model=TeacherRead)
def teacher_profile(teacher: User = Depends(require_teacher)):
    """The signed-in teacher's own account, read from the database rather than from the token."""
    return _read(teacher)
