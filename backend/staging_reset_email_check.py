"""Staging check of the forgot-password email over REAL SMTP (for example Hostinger), on a throwaway database.

    python staging_reset_email_check.py [--source local_dev.db] [--no-redeem]

What it does, in order:
  1. Copies the source database to a temporary folder. The copy is the only database touched. It refuses school.db,
     demo.db, anything under /data, and any path outside this folder or the temp folder named by --source.
  2. Gives the first active teacher in the COPY the address in STAGING_TEST_RECIPIENT (an inbox you can read).
  3. Asks for a reset link through the real route (POST /auth/forgot-password) and lets the real service send it.
  4. Unless --no-redeem: opens the link once, sets a throwaway password in the copy, and checks that the link
     cannot be used a second time. A second real email ("your password was changed") is sent by that step.
  5. Checks the link's lifetime is exactly the approved 60 minutes.

Settings come from the environment only (never from this file):
  EMAIL_BACKEND=smtp  SMTP_HOST  SMTP_PORT  SMTP_SECURITY  SMTP_USERNAME  SMTP_PASSWORD  EMAIL_FROM
  STAGING_TEST_RECIPIENT   PASSWORD_RESET_URL_BASE (optional, default http://localhost:5173)

Nothing printed here contains a password, a token, a reset link or an email address.
"""
import argparse
import os
import re
import secrets
import shutil
import smtplib
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
BLOCKED_NAMES = {"school.db", "demo.db"}

REQUIRED = ["EMAIL_BACKEND", "SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "EMAIL_FROM", "STAGING_TEST_RECIPIENT"]


def fail(message: str) -> None:
    print(f"STOPPED: {message}")
    sys.exit(2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default="local_dev.db")
    parser.add_argument("--no-redeem", action="store_true", help="send the email only; leave the link unused")
    args = parser.parse_args()

    missing = [name for name in REQUIRED if not os.environ.get(name, "").strip()]
    if missing:
        fail("set these environment variables first: " + ", ".join(missing))
    if os.environ["SMTP_HOST"].strip().lower().endswith(("gmail.com", "googlemail.com")):
        # Google shows an App Password as four groups of four letters; the spaces are not part of it. Anything else
        # (a normal password, a 6-digit code) is refused by Google, and repeated bad logins can lock the account's SMTP.
        from smtp_password_check import clean_google_app_password

        app_password, problem = clean_google_app_password(os.environ["SMTP_PASSWORD"])
        if problem:
            fail(f"that is not a Google App Password: {problem} (create one at myaccount.google.com/apppasswords). "
                 "Nothing was sent to Google.")
        os.environ["SMTP_PASSWORD"] = app_password
    if os.environ["EMAIL_BACKEND"].strip().lower() != "smtp":
        fail("EMAIL_BACKEND must be smtp for a real delivery test.")
    if os.environ.get("MODAL_ENVIRONMENT") or os.environ.get("MODAL_TASK_ID"):
        fail("this looks like a Modal container. Staging checks run locally only.")

    source = Path(args.source)
    source = source if source.is_absolute() else HERE / source
    if source.name.lower() in BLOCKED_NAMES or str(source).replace("\\", "/").startswith("/data"):
        fail(f"{source.name} is not allowed as a source. Use local_dev.db or another throwaway copy.")
    if not source.is_file():
        fail(f"no database at {source}.")

    workdir = Path(tempfile.mkdtemp(prefix="educore-staging-"))
    staging_db = workdir / "staging.db"
    shutil.copyfile(source, staging_db)

    # Everything below must see the copy, never the real database. Set before config is imported.
    os.environ["APP_ENV"] = "development"
    os.environ["DATABASE_URL"] = f"sqlite:///{staging_db.as_posix()}"
    os.environ.setdefault("PASSWORD_RESET_URL_BASE", "http://localhost:5173")
    os.environ["ADMIN_PASSWORD"] = ""  # never prints or sets an admin password
    recipient = os.environ["STAGING_TEST_RECIPIENT"].strip()

    sys.path.insert(0, str(HERE))
    import config  # noqa: E402

    assert config.DATABASE_URL.endswith("staging.db"), "staging must use the temporary copy"
    from services.email_address import email_problem  # noqa: E402

    problem = email_problem(recipient)
    if problem:
        fail(f"STAGING_TEST_RECIPIENT is not usable ({problem}).")

    db = sqlite3.connect(staging_db)
    teacher = db.execute("SELECT id FROM users WHERE role='teacher' AND is_active=1 ORDER BY id LIMIT 1").fetchone()
    if teacher is None:
        fail("the copy has no active teacher account.")
    # A reset link never goes to an address shared by two accounts, so the test address must sit on exactly one
    # account. Only the temporary copy is changed: take it off any other account, then give it to the teacher.
    cleared = db.execute("UPDATE users SET email=NULL WHERE lower(trim(email))=lower(?) AND id<>?", (recipient, teacher[0])).rowcount
    db.execute("UPDATE users SET email=? WHERE id=?", (recipient, teacher[0]))
    db.commit()
    if cleared:
        print(f"Note: {cleared} other account(s) in the copy already used the test address; removed there so it is unique.")
    db.close()

    from fastapi.testclient import TestClient  # noqa: E402
    from main import app  # noqa: E402
    from services import email_service, self_service_reset  # noqa: E402

    sent = {"attempts": 0, "delivered": 0, "error": None, "bodies": []}
    real_send_smtp = email_service._send_smtp

    def recording_send(built):
        sent["attempts"] += 1
        sent["bodies"].append(built.get_content())
        try:
            real_send_smtp(built)
            sent["delivered"] += 1
        except Exception as error:  # the service swallows it; report only the kind, never the text
            code = getattr(error, "smtp_code", None)
            sent["error"] = f"{type(error).__name__}" + (f" (SMTP {code})" if code else "")
            if isinstance(error, smtplib.SMTPServerDisconnected) and config.SMTP_USERNAME:
                sent["error"] += " - the server hung up during sign-in; Google does this for a wrong or revoked App Password"
            raise

    email_service._send_smtp = recording_send

    results = []

    def check(label: str, ok: bool, detail: str = "") -> None:
        results.append(ok)
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))

    print(f"Staging database: temporary copy of {source.name} (original untouched)")
    print(f"SMTP: host={config.SMTP_HOST} port={config.SMTP_PORT} security={config.SMTP_SECURITY} (credentials not shown)")

    with TestClient(app) as client:
        unknown = client.post("/auth/forgot-password", json={"email": "nobody-here@example.test"})
        known = client.post("/auth/forgot-password", json={"email": recipient})
        self_service_reset.drain_background_work()
        check("forgot-password answers the same for a known and an unknown address",
              unknown.status_code == known.status_code and unknown.json() == known.json(), f"status {known.status_code}")
        check("one email was sent to the SMTP server", sent["attempts"] == 1 and sent["delivered"] == 1,
              sent["error"] or ("no send was attempted: no single eligible account for the address" if sent["attempts"] == 0 else f"{sent['delivered']} delivered"))

        if sent["delivered"] == 1:
            conn = sqlite3.connect(staging_db)
            created, expires = conn.execute("SELECT created_at, expires_at FROM password_reset_tokens ORDER BY id DESC LIMIT 1").fetchone()
            conn.close()
            minutes = (datetime.fromisoformat(expires) - datetime.fromisoformat(created)).total_seconds() / 60
            check("link lifetime is exactly 60 minutes", round(minutes) == 60 and config.PASSWORD_RESET_TOKEN_MINUTES == 60, f"{minutes:.1f} min")
            check("email says 60 minutes", "within 60 minutes" in sent["bodies"][0])

            if not args.no_redeem:
                match = re.search(r"#token=([\w-]+)", sent["bodies"][0])
                token = match.group(1) if match else ""
                check("email contains a reset link", bool(token))
                if token:
                    check("link check accepts the fresh token", client.post("/auth/reset-password/check", json={"token": token}).status_code == 200)
                    throwaway = f"Stg-{secrets.token_urlsafe(12)}-9x"
                    first = client.post("/auth/reset-password", json={"token": token, "new_password": throwaway})
                    second = client.post("/auth/reset-password", json={"token": token, "new_password": throwaway + "2"})
                    self_service_reset.drain_background_work()
                    check("new password accepted once", first.status_code == 200, f"status {first.status_code}")
                    check("the same link is refused the second time", second.status_code in (400, 404, 410), f"status {second.status_code}")

    print()
    if all(results):
        print("RESULT: all checks passed. Now confirm in the recipient inbox that the message arrived (also check Spam).")
        print("        Delete the temporary folder when done:", workdir)
        return 0
    print("RESULT: at least one check failed. Temporary folder kept for inspection:", workdir)
    return 1


if __name__ == "__main__":
    sys.exit(main())
