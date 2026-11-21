"""Reports email addresses on existing accounts that the current rule would not accept, and addresses shared by
more than one account. READ ONLY: the database is opened read-only and nothing is changed or fixed for you.

    python check_registered_emails.py                 # the database in DATABASE_URL (default: school.db)
    python check_registered_emails.py path/to/file.db

An address listed here still sits on its account. Until the school office corrects it (Teachers or Parents page,
"Change email"), password reset by email will not work for that account (a shared address is skipped on purpose).
"""
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

from services.email_address import email_problem


def default_path() -> str:
    from config import DATABASE_URL

    return DATABASE_URL.replace("sqlite:///", "", 1)


def main(argv) -> int:
    path = Path(argv[0] if argv else default_path())
    if not path.is_file():
        print(f"No database file at {path}.")
        return 2
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "SELECT id, username, role, email FROM users WHERE email IS NOT NULL AND TRIM(email) <> '' ORDER BY id"
        ).fetchall()
    finally:
        connection.close()

    problems, by_address = [], defaultdict(list)
    for user_id, username, role, email in rows:
        reason = email_problem(email)
        if reason:
            problems.append((user_id, username, role, email, reason))
        else:
            by_address[email.strip().lower()].append((user_id, username, role))
    shared = {address: users for address, users in by_address.items() if len(users) > 1}

    print(f"{len(rows)} account(s) have an email address.")
    for user_id, username, role, email, reason in problems:
        print(f"  INVALID  id={user_id} {role} {username}: {email!r} ({reason})")
    for address, users in shared.items():
        print(f"  SHARED   {address!r} is on: " + ", ".join(f"{role} {username} (id={uid})" for uid, username, role in users))
    if not problems and not shared:
        print("All of them are valid and none is shared.")
        return 0
    print(f"{len(problems)} invalid, {len(shared)} shared. Nothing was changed.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
