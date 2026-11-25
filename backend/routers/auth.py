import hashlib
import hmac
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional

import jwt
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field, field_validator
from sqlmodel import Session, col, delete, select

from config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, PASSWORD_RESET_TOKEN_MINUTES, SECRET_KEY
from database import get_session
from models.user import (
    PORTAL_ONLY_ROLES,
    ROLE_DEMO,
    RevokedToken,
    User,
    hash_password,
    needs_rehash,
    password_problem,
    verify_password,
)
from services.email_address import clean_email
from services.login_throttle import LoginThrottle
from services.password_reset import (
    PASSWORD_CHANGE_REQUIRED,
    complete_pending,
    invalidate_tokens,
    password_change_pending,
)
from services.self_service_reset import (
    ResetLinkUnusable,
    complete_reset,
    find_valid_token,
    normalise_email,
    request_throttle_by_address,
    request_throttle_by_email,
    run_in_background,
    send_password_changed_email,
    send_reset_link_if_eligible,
    token_failure_throttle,
)

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
    # True after an administrator reset the password: only changing it (and signing out) is allowed until then.
    must_change_password: bool = False


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


DEMO_REFUSAL = "This demo account can add and edit records, but cannot remove anything or manage accounts."
# A demo account may add and edit, but never remove (delete, archive, deactivate) or touch accounts: the login is
# shared, and an account action (reset, email change, new login, linking a child) would hand a visitor someone's access.
DEMO_ACCOUNT_PREFIXES = ("/teachers", "/parents", "/auth")
DEMO_REMOVAL_SUFFIXES = ("/archive", "/deactivate")
DEMO_ALLOWED_DELETES = frozenset({"/chatbot/history/{session_id}"})  # the visitor's own chat, not school data


def _is_demo(user: User) -> bool:
    return (user.role or "").lower() == ROLE_DEMO


def demo_may(method: str, path: str) -> bool:
    """Whether the demo role may make this request. `path` is the route's template, e.g. /students/{student_id}."""
    if method in ("GET", "HEAD"):
        return True
    if method == "DELETE":
        return path in DEMO_ALLOWED_DELETES
    return not path.startswith(DEMO_ACCOUNT_PREFIXES) and not path.endswith(DEMO_REMOVAL_SUFFIXES)


def _demo_refused() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=DEMO_REFUSAL)


def get_active_user(
    request: Request,
    user: User = Depends(get_authenticated_user),
    session: Session = Depends(get_session),
) -> User:
    """A signed-in account that is free to use the app. After an administrator reset its password it is not,
    until its owner chooses a new one. Every route refuses it except the account's own (/auth/me, change
    password, sign out), which use get_authenticated_user. Checked on every request, so a forced change cannot be skipped by editing the browser."""
    if password_change_pending(session, user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=PASSWORD_CHANGE_REQUIRED)
    # Refused here, which every staff and admin route passes through, so a new write route is closed by default.
    if _is_demo(user) and not demo_may(request.method, request.scope["route"].path):
        raise _demo_refused()
    return user


def get_current_user(user: User = Depends(get_active_user)) -> User:
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

    def check(user: User = Depends(get_active_user)) -> User:
        # A demo account passes as an administrator here; get_active_user has already refused what it may not do.
        role = "admin" if _is_demo(user) else (user.role or "").lower()
        if role not in allowed:
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
        "must_change_password": password_change_pending(session, user.id),
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
    # The login is shared, so one visitor must not be able to lock the others out.
    if _is_demo(current_user):
        raise _demo_refused()
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
    complete_pending(session, current_user.id)  # choosing their own password ends a forced change
    invalidate_tokens(session, current_user.id)  # an emailed reset link requested earlier must not undo this change
    session.commit()
    session.refresh(current_user)

    return {
        "username": current_user.username,
        "role": current_user.role,
        "access_token": create_access_token(current_user),
    }


FORGOT_PASSWORD_REPLY = (
    "If that email address belongs to a teacher or parent account, a reset link is on its way. "
    f"It works once, for {PASSWORD_RESET_TOKEN_MINUTES} minutes."
)
INVALID_RESET_LINK = "This reset link is not valid any more. Please ask for a new one."


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=1, max_length=254)

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        # The same rule as for registering an address. Anything that is not one address is a 422, which says
        # nothing about whether an address belongs to an account.
        return clean_email(value)


class ResetTokenRequest(BaseModel):
    token: str = Field(min_length=1, max_length=200)


class ResetPasswordRequest(ResetTokenRequest):
    new_password: str = Field(min_length=1, max_length=MAX_CREDENTIAL_LENGTH)


def _client_address(http_request: Request) -> str:
    return http_request.client.host if http_request.client else "unknown"


def _too_many(wait: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many attempts. Please wait a few minutes and try again.",
        headers={"Retry-After": str(wait)},
    )


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
def forgot_password(payload: ForgotPasswordRequest, http_request: Request):
    """A teacher or parent asks for a reset link. The answer is always the same, and takes the same time, whether
    or not the address belongs to an account, so this cannot be used to find out who has one. This function does
    nothing that depends on the address except queue it: the lookup, the new link and the email happen afterwards
    (see send_reset_link_if_eligible). The link is only ever emailed: it is not in the response and not in any log."""
    address = _client_address(http_request)
    wait = request_throttle_by_address.retry_after(address)
    if wait:
        raise _too_many(wait)
    request_throttle_by_address.record_failure(address)

    email = normalise_email(payload.email)
    # Over the limit for this address, nothing is queued, and the reply is still the same: a visible limit would show the address is known.
    if not request_throttle_by_email.retry_after(email):
        request_throttle_by_email.record_failure(email)
        run_in_background(send_reset_link_if_eligible, email)
    return {"message": FORGOT_PASSWORD_REPLY}


def _valid_token_or_refuse(session: Session, raw_token: str, http_request: Request):
    address = _client_address(http_request)
    wait = token_failure_throttle.retry_after(address)
    if wait:
        raise _too_many(wait)
    row = find_valid_token(session, raw_token.strip())
    if row is None:
        token_failure_throttle.record_failure(address)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_RESET_LINK)
    return row


@router.post("/reset-password/check")
def check_reset_link(payload: ResetTokenRequest, http_request: Request, session: Session = Depends(get_session)):
    """Lets the page say at once that a link is dead, before anyone types a new password."""
    _valid_token_or_refuse(session, payload.token, http_request)
    return {"valid": True}


@router.post("/reset-password")
def reset_password_with_link(
    payload: ResetPasswordRequest,
    http_request: Request,
    background: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Sets a new password from an emailed link. Same password policy as everywhere. The link is spent only
    when the password is accepted, so a too-weak choice can be corrected. Every earlier session ends."""
    row = _valid_token_or_refuse(session, payload.token, http_request)
    problem = password_problem(payload.new_password)
    if problem:
        raise HTTPException(status_code=422, detail=f"New password is not acceptable: {problem}.")
    try:
        account = complete_reset(session, row, payload.new_password)
    except ResetLinkUnusable:  # the same link was submitted twice at once, and the other submission won
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_RESET_LINK)
    if account.email:
        background.add_task(send_password_changed_email, account.email, account.full_name)
    return {"message": "Your password has been changed. Please sign in with the new password."}


@router.get("/me")
def me(current_user: User = Depends(get_authenticated_user), session: Session = Depends(get_session)):
    return {
        "username": current_user.username,
        "role": current_user.role,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "is_active": current_user.is_active,
        "must_change_password": password_change_pending(session, current_user.id),
    }
