import hashlib
import hmac
from datetime import datetime, timezone
from typing import Optional

import bcrypt
from sqlalchemy import text as sa_text
from sqlmodel import Field, SQLModel

MIN_PASSWORD_LENGTH = 10
BCRYPT_MAX_BYTES = 72
LEGACY_SALT = "alnoor_salt_2026"
KNOWN_DEFAULT_PASSWORDS = ("admin123",)
COMMON_PASSWORDS = {"password123", "password1234", "1234567890", "qwertyuiop", "administrator", "admin12345"}


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    role: str = Field(default="admin")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Added for the Teacher Portal. The server default makes every account that already exists active,
    # so no legacy account is locked out or changed. See migrate_db.py for the upgrade of old databases.
    is_active: bool = Field(default=True, sa_column_kwargs={"server_default": sa_text("1")})
    full_name: Optional[str] = Field(default=None)
    email: Optional[str] = Field(default=None)


ROLE_TEACHER = "teacher"
ROLE_PARENT = "parent"
# Roles that have a portal of their own and no access to the staff-side routes.
PORTAL_ONLY_ROLES = frozenset({ROLE_TEACHER, ROLE_PARENT})


class RevokedToken(SQLModel, table=True):
    """Tokens ended by logout, kept only until they would have expired anyway."""

    __tablename__ = "revoked_tokens"

    jti: str = Field(primary_key=True)
    expires_at: datetime = Field(index=True)


class PasswordResetEvent(SQLModel, table=True):
    """An administrator set a new password for an account. The audit record of who did it and when.

    It never holds a password or a hash. While `completed_at` is empty the account's owner has not yet
    chosen their own password, so every route except changing it (and signing out) is closed to them.
    New table only: create_all adds it and no existing table changes.
    """

    __tablename__ = "password_reset_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    reset_by: int = Field(foreign_key="users.id")
    reset_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = Field(default=None)


class PasswordResetToken(SQLModel, table=True):
    """A self-service "forgot password" link that was emailed to a teacher or parent.

    Only a SHA-256 of the token is stored, never the token itself, so a copy of the database cannot be used
    to reset anyone's password. A token works once (`used_at`) and only until `expires_at`. Times are timezone-aware UTC.
    New table only: create_all adds it and no existing table changes.
    """

    __tablename__ = "password_reset_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    token_hash: str = Field(index=True, unique=True)
    created_at: datetime
    expires_at: datetime
    used_at: Optional[datetime] = Field(default=None)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _is_bcrypt_hash(stored_hash: str) -> bool:
    return stored_hash.startswith("$2")


def _legacy_hash(password: str) -> str:
    return hashlib.sha256(f"{LEGACY_SALT}{password}".encode("utf-8")).hexdigest()


def verify_password(plain_password: str, stored_hash: str) -> bool:
    encoded = plain_password.encode("utf-8")
    if not _is_bcrypt_hash(stored_hash):
        return hmac.compare_digest(_legacy_hash(plain_password).encode(), stored_hash.encode())
    if len(encoded) > BCRYPT_MAX_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, stored_hash.encode("utf-8"))
    except ValueError:
        return False


def needs_rehash(stored_hash: str) -> bool:
    """True for hashes from before bcrypt; they are upgraded at the next successful login."""
    return not _is_bcrypt_hash(stored_hash)


def password_problem(password: str) -> Optional[str]:
    """A message saying why this password is not acceptable, or None if it is fine."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"it must be at least {MIN_PASSWORD_LENGTH} characters"
    if len(password.encode("utf-8")) > BCRYPT_MAX_BYTES:
        return f"it must be at most {BCRYPT_MAX_BYTES} bytes"
    if password.lower() in COMMON_PASSWORDS or password in KNOWN_DEFAULT_PASSWORDS:
        return "it is too common"
    return None
