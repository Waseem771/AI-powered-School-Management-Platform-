"""Builds the demo database for the online demo (modal_demo_app.py), with both of its logins.

    python build_online_demo_db.py path\\to\\folder\\demo.db

Made-up records only (seed_demo.py). Asks at hidden prompts for the `admin` password (full access to the demo
school only) and the `demo` password (adds and edits, never removes or manages accounts). Prints no password.
Then upload the file: python -m modal volume put educore-demo-data <that file> demo.db
"""
import os
import sys
from getpass import getpass
from pathlib import Path

os.environ["APP_ENV"] = "development"  # a local file build; the online app runs with production safeguards

from add_admin_account import add_admin, ask_password_hash  # noqa: E402
from models.user import password_problem  # noqa: E402
from seed_demo import build_demo_database  # noqa: E402


def ask_admin_password() -> str:
    password = getpass("Password for the demo school's 'admin' (hidden): ")
    problem = password_problem(password)
    if problem:
        raise SystemExit(f"Password is not acceptable: {problem}.")
    if getpass("Type it again: ") != password:
        raise SystemExit("The two passwords differ.")
    return password


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print(__doc__)
        return 2
    path = Path(args[0]).resolve()
    if path.parent == Path(__file__).resolve().parent:
        raise SystemExit("Build it outside backend/, so the local demo.db and the app's files are never touched.")
    path.parent.mkdir(parents=True, exist_ok=True)

    summary = build_demo_database(path, admin_password=ask_admin_password())
    print(f"Built {path.name}: {summary['students']} made-up students, {summary['invoices']} challans.")
    print("Now the shared 'demo' login (at least 9 characters):")
    return add_admin(path, "demo", ask_password_hash(demo=True), demo=True)


if __name__ == "__main__":
    sys.exit(main())
