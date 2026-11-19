import hashlib
import hmac
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
from sqlmodel import Session, col, delete, select

from config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from database import get_session
from models.user import (
    PORTAL_ONLY_ROLES,
    RevokedToken,
    User,
    hash_password,
    needs_rehash,
    password_problem,
    verify_password,
)
from services.login_throttle import LoginThrottle

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

THROTTLE_WINDOW_SECONDS = 15 * 60
MAX_FAILURES_PER_USERNAME = 10
MAX_FAILURES_PER_ADDRESS = 30
MAX_CREDENTIAL_LENGTH = 128

login_throttle = LoginThrottle(MAX_FAILURES_PER_USERNAME, THROTTLE_WINDOW_SECONDS)
address_throttle = LoginThrottle(MAX_FAILURES_PER_ADDRESS, THROTTLE_WINDOW_SECONDS)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=MAX_CREDENTIAL_LENGTH)
    password: str = Field(min_length=1, max_length=MAX_CREDENTIAL_LENGTH)


class LoginResponse(BaseModel):
    username: str
    role: str
    access_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=MAX_CREDENTIAL_LENGTH)
    new_password: str = Field(min_length=1, max_length=MAX_CREDENTIAL_LENGTH)


def _password_fingerprint(password_hash: str) -> str:
    """Ties a token to the current password, so changing it ends every older session."""
    return hmac.new(SECRET_KEY.encode(), password_hash.encode(), hashlib.sha256).hexdigest()[:32]


def create_access_token(user: User) -> str:
    claims = {
        "sub": user.username,
        "role": user.role,
        "jti": uuid.uuid4().hex,
        "pwf": _password_fingerprint(user.password_hash),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(claims, SECRET_KEY, algorithm=ALGORITHM)


def _unauthorized(detail: str = "Authentication required") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_authenticated_user(
    token: Optional[str] = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    """Any signed-in, active account, whatever its role. Only for routes every role may use
    (the account's own profile, password change). School data routes use get_current_user."""
    if not token:
        raise _unauthorized()

    try:
        claims = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub", "jti", "pwf"]},
        )
    except jwt.PyJWTError:
        raise _unauthorized("Your session has expired. Please sign in again.")

    user = session.exec(select(User).where(User.username == claims["sub"])).first()
    if user is None or not hmac.compare_digest(claims["pwf"], _password_fingerprint(user.password_hash)):
        raise _unauthorized("Your session has expired. Please sign in again.")
    if session.get(RevokedToken, claims["jti"]) is not None:
        raise _unauthorized("Your session has expired. Please sign in again.")
    # Checked on every request, so deactivating an account ends its tokens at once.
    if not user.is_active:
        raise _unauthorized("This account has been deactivated.")
    return user


def get_current_user(user: User = Depends(get_authenticated_user)) -> User:
    """A signed-in member of staff. Every school-data route depends on this, so accounts that only
    have a portal of their own (teachers) are refused everywhere else by default."""
    if (user.role or "").lower() in PORTAL_ONLY_ROLES:
        raise _forbidden()
    return user


def _forbidden() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to do this.")


def require_roles(*roles: str):
    """A dependency allowing only the named roles, e.g. Depends(require_roles("admin"))."""
    allowed = frozenset(role.lower() for role in roles)

    def check(user: User = Depends(get_authenticated_user)) -> User:
        if (user.role or "").lower() not in allowed:
            raise _forbidden()
        return user

    return check


@lru_cache
def _decoy_hash() -> str:
    return hash_password("decoy-used-only-to-even-out-login-timing")


def _throttle_keys(username: str, http_request: Request) -> tuple[str, str]:
    address = http_request.client.host if http_request.client else "unknown"
    return username.strip().lower(), address


def _reject_if_throttled(username_key: str, address_key: str) -> None:
    wait = max(login_throttle.retry_after(username_key), address_throttle.retry_after(address_key))
    if wait:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Please wait a few minutes and try again.",
            headers={"Retry-After": str(wait)},
        )


def _record_failure(username_key: str, address_key: str) -> None:
    login_throttle.record_failure(username_key)
    address_throttle.record_failure(address_key)


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, http_request: Request, session: Session = Depends(get_session)):
    username_key, address_key = _throttle_keys(payload.username, http_request)
    _reject_if_throttled(username_key, address_key)

    user = session.exec(select(User).where(User.username == payload.username)).first()
    stored_hash = user.password_hash if user else _decoy_hash()
    if not verify_password(payload.password, stored_hash) or user is None:
        _record_failure(username_key, address_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    login_throttle.reset(username_key)

    # Said only after the password was right, so it does not reveal which usernames exist.
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Please contact the school office.",
        )

    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(payload.password)
        session.add(user)
        session.commit()
        session.refresh(user)

    return {
        "username": user.username,
        "role": user.role,
        "access_token": create_access_token(user),
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    token: Optional[str] = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> None:
    if not token:
        return
    try:
        claims = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"require": ["exp", "jti"]})
    except jwt.PyJWTError:
        return  # Already unusable, so there is nothing to revoke.

    now = datetime.now(timezone.utc)
    session.exec(delete(RevokedToken).where(col(RevokedToken.expires_at) < now))
    session.merge(
        RevokedToken(jti=claims["jti"], expires_at=datetime.fromtimestamp(claims["exp"], tz=timezone.utc))
    )
    session.commit()


@router.post("/change-password", response_model=LoginResponse)
def change_password(
    payload: ChangePasswordRequest,
    http_request: Request,
    current_user: User = Depends(get_authenticated_user),
    session: Session = Depends(get_session),
):
    username_key, address_key = _throttle_keys(current_user.username, http_request)
    _reject_if_throttled(username_key, address_key)

    if not verify_password(payload.current_password, current_user.password_hash):
        _record_failure(username_key, address_key)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Your current password is incorrect.")

    problem = password_problem(payload.new_password)
    if problem:
        raise HTTPException(status_code=422, detail=f"New password is not acceptable: {problem}.")
    if payload.new_password == payload.current_password:
        raise HTTPException(status_code=422, detail="New password must be different from the current one.")

    current_user.password_hash = hash_password(payload.new_password)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)

    return {
        "username": current_user.username,
        "role": current_user.role,
        "access_token": create_access_token(current_user),
    }


@router.get("/me")
def me(current_user: User = Depends(get_authenticated_user)):
    return {
        "username": current_user.username,
        "role": current_user.role,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "is_active": current_user.is_active,
    }
