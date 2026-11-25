"""Adds one more administrator account to a database. Reports only unless --apply.

    python add_admin_account.py path/to/school.db admin1           # report
    python add_admin_account.py path/to/school.db admin1 --apply   # ask for a password, back up, then add

    modal run modal_app.py::add_admin_account --username admin1 [--apply]   # the live database
    modal run modal_app.py::add_admin_account --username demo --demo --apply   # demo account: adds and edits, never removes

--demo adds an account that sees the administrator's screens and can add and edit, but cannot remove
anything or manage accounts. DEPLOY THE BACKEND THAT KNOWS THE demo ROLE FIRST: older code treats it as
staff, with full write access.

On Modal, STOP THE APP FIRST (modal app stop educore-ai-school-platform), then deploy again afterwards: a
running web container keeps its own copy of the database and can write it back over the new account.

The password is typed at a hidden prompt, never given as an argument; only its bcrypt hash is stored.
It never changes an existing account. There is no screen for removing an administrator, so a mistake
is undone by restoring the backup it takes. This reads no application secrets.
"""
import argparse
import re
import sys
from getpass import getpass
from pathlib import Path

from sqlalchemy import func
from sqlmodel import Session, create_engine, select

from models.user import (
    DEMO_MIN_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
    ROLE_DEMO,
    User,
    hash_password,
    password_problem,
)
from services.backup_service import create_consistent_backup


def ask_password_hash(demo: bool = False) -> str:
    """Prompts twice and returns the hash, or stops with the reason."""
    password = getpass("New account password (hidden): ")
    problem = password_problem(password, DEMO_MIN_PASSWORD_LENGTH if demo else MIN_PASSWORD_LENGTH)
    if problem:
        raise SystemExit(f"Password is not acceptable: {problem}.")
    if getpass("Type it again: ") != password:
        raise SystemExit("The two passwords differ.")
    return hash_password(password)


def add_admin(database: Path, username: str, password_hash: str = "", demo: bool = False) -> int:
    """Without a password_hash this only reports."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,50}", username):
        print("A username is 3-50 letters, numbers, dots, dashes or underscores.")
        return 2
    if not database.exists():
        print(f"{database} does not exist.")
        return 2

    role = ROLE_DEMO if demo else "admin"
    kind = "demo (add and edit, no removal) account" if demo else "administrator"
    engine = create_engine(f"sqlite:///{database}")
    try:
        with Session(engine) as session:
            if session.exec(select(User).where(func.lower(User.username) == username.lower())).first():
                print(f"'{username}' is already taken. Nothing was changed.")
                return 1
            if not password_hash:
                print(f"Report only. --apply would add the {kind} '{username}'.")
                return 0

            backup = database.with_name(f"{database.name}.backup-before-admin-{username}")
            if not create_consistent_backup(database, backup):
                print("The backup failed, so nothing was changed.")
                return 1
            print("Backed up to", backup.name)

            session.add(User(username=username, password_hash=password_hash, role=role))
            session.commit()
            print(f"Added the {kind} '{username}'.")
            return 0
    finally:
        engine.dispose()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("username")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--demo", action="store_true")
    args = parser.parse_args(argv)
    password_hash = ask_password_hash(args.demo) if args.apply else ""
    return add_admin(args.database, args.username, password_hash, args.demo)


if __name__ == "__main__":
    sys.exit(main())
