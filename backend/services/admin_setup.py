"""Creates the admin account, and keeps production off any published default password."""
import secrets

from sqlmodel import Session, select

from models.user import (
    KNOWN_DEFAULT_PASSWORDS,
    User,
    hash_password,
    password_problem,
    verify_password,
)

ADMIN_USERNAME = "admin"


def _validated(admin_password: str) -> str:
    problem = password_problem(admin_password)
    if problem:
        raise RuntimeError(f"ADMIN_PASSWORD is not acceptable: {problem}")
    return admin_password


def _uses_known_default(admin: User) -> bool:
    return any(verify_password(password, admin.password_hash) for password in KNOWN_DEFAULT_PASSWORDS)


def _set_password(session: Session, admin: User, password: str) -> None:
    admin.password_hash = hash_password(password)
    session.add(admin)
    session.commit()


def _create_admin(session: Session, is_production: bool, admin_password: str) -> None:
    if is_production:
        if not admin_password:
            raise RuntimeError("Set ADMIN_PASSWORD to create the admin account in production.")
        password = _validated(admin_password)
    else:
        password = admin_password or secrets.token_urlsafe(12)

    session.add(User(username=ADMIN_USERNAME, password_hash=hash_password(password), role="admin"))
    session.commit()

    if not admin_password:
        print(f"[Auth] Created development admin. Username: {ADMIN_USERNAME} password: {password} (shown once)")


def ensure_admin_account(
    session: Session,
    is_production: bool,
    admin_password: str,
    force_reset: bool = False,
) -> None:
    """Called at startup and when seeding.

    ADMIN_PASSWORD sets the password when the account is created or still on a published
    default. It does not overwrite a password changed in the app, unless ADMIN_PASSWORD_RESET
    is on, which is the way back in after a forgotten password.
    """
    admin = session.exec(select(User).where(User.username == ADMIN_USERNAME)).first()

    if admin is None:
        _create_admin(session, is_production, admin_password)
        return

    if force_reset:
        if not admin_password:
            raise RuntimeError("ADMIN_PASSWORD_RESET is on, but ADMIN_PASSWORD is not set.")
        _set_password(session, admin, _validated(admin_password))
        print("[Auth] Admin password was reset. Turn ADMIN_PASSWORD_RESET off now.")
        return

    if is_production and _uses_known_default(admin):
        if not admin_password:
            raise RuntimeError(
                "The admin account still uses a published default password. "
                "Set ADMIN_PASSWORD to replace it, then restart."
            )
        _set_password(session, admin, _validated(admin_password))
        print("[Auth] Replaced the default admin password with ADMIN_PASSWORD.")
