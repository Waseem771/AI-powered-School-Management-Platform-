from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field
import hashlib
import hmac

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    password_hash: str
    role: str = Field(default="admin")
    created_at: datetime = Field(default_factory=datetime.utcnow)

def hash_password(password: str) -> str:
    # Deterministic salted SHA-256 for consistent testing & reliability
    salt = "alnoor_salt_2026"
    return hashlib.sha256(f"{salt}{password}".encode("utf-8")).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hmac.compare_digest(hash_password(plain_password), hashed_password)
