import hashlib
import hmac
from datetime import datetime, timezone
from typing import Optional

import bcrypt
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


class RevokedToken(SQLModel, table=True):
    """Tokens ended by logout, kept only until they would have expired anyway."""

    __tablename__ = "revoked_tokens"

    jti: str = Field(primary_key=True)
    expires_at: datetime = Field(index=True)


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
