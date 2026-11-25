"""Real-email test of "forgot password" for ONE teacher and ONE parent on the LOCAL database (local_dev.db).

    python local_smtp_reset_test.py [--teacher waseem7711] [--parent reset.test.parent]

It asks for a reset link through the real route (POST /auth/forgot-password), so the app's own rate limits apply and
nothing is bypassed, and it lets the real service send through the SMTP settings in the environment. It never opens
the link, never sets a password, and changes nothing except the one reset-link row the request itself creates.

Settings come from the environment (see staging.env; the password is typed at a prompt). Nothing printed here
contains a password, a token, a reset link or an email address.
"""
import argparse
import os
import smtplib
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REQUIRED = ["EMAIL_BACKEND", "SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "EMAIL_FROM"]


def fail(message: str) -> None:
    print(f"STOPPED: {message}")
    sys.exit(2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--teacher", default="waseem7711")
    parser.add_argument("--parent", default="reset.test.parent")
    args = parser.parse_args()

    missing = [name for name in REQUIRED if not os.environ.get(name, "").strip()]
    if missing:
        fail("set these environment variables first: " + ", ".join(missing))
    if os.environ["EMAIL_BACKEND"].strip().lower() != "smtp":
        fail("EMAIL_BACKEND must be smtp (otherwise emails only go to dev_outbox).")
    if os.environ["SMTP_HOST"].strip().lower().endswith(("gmail.com", "googlemail.com")):
        sys.path.insert(0, str(HERE))
        from smtp_password_check import clean_google_app_password

        os.environ["SMTP_PASSWORD"], problem = clean_google_app_password(os.environ["SMTP_PASSWORD"])
        if problem:
            fail(f"that is not a Google App Password: {problem}. Nothing was sent to Google.")

    db_path = HERE / "local_dev.db"
    if not db_path.is_file():
        fail("local_dev.db was not found.")
    os.environ["APP_ENV"] = "development"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    os.environ["ADMIN_PASSWORD"] = ""
    os.environ.setdefault("PASSWORD_RESET_URL_BASE", "http://localhost:5173")

    sys.path.insert(0, str(HERE))
    import config  # noqa: E402

    if not config.DATABASE_URL.endswith("local_dev.db") or config.IS_PRODUCTION:
        fail("this test only runs on local_dev.db in development mode.")

    # Accounts: look up by username, read-only. The address must belong to this one active account.
    ro = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    targets = []
    for role, username in (("teacher", args.teacher), ("parent", args.parent)):
        row = ro.execute("SELECT id, role, is_active, email FROM users WHERE username=?", (username,)).fetchone()
        if row is None or row[1] != role or not row[2] or not (row[3] or "").strip():
            fail(f"{username} must be an active {role} account with a registered email.")
        shared = ro.execute("SELECT count(*) FROM users WHERE lower(trim(email))=lower(trim(?))", (row[3],)).fetchone()[0]
        if shared != 1:
            fail(f"the address on {username} is shared by {shared} accounts, so no link would be sent (by design).")
        targets.append((role, username, row[0], row[3].strip()))
    ro.close()

    from fastapi.testclient import TestClient  # noqa: E402
    from main import app  # noqa: E402
    from services import email_service, self_service_reset  # noqa: E402

    trace = {"connects": 0, "auth_ok": 0, "delivered": 0, "error": None, "bodies": []}
    real_login = smtplib.SMTP.login
    real_send_smtp = email_service._send_smtp

    def traced_login(self, user, password, *a, **k):
        result = real_login(self, user, password, *a, **k)
        trace["auth_ok"] += 1  # reached only when the server accepted the sign-in
        return result

    def traced_send(built):
        trace["connects"] += 1
        trace["bodies"].append(built.get_content())
        try:
            real_send_smtp(built)
            trace["delivered"] += 1
        except Exception as error:  # the service swallows it; report only the kind
            code = getattr(error, "smtp_code", None)
            trace["error"] = type(error).__name__ + (f" (SMTP {code})" if code else "")
            raise

    smtplib.SMTP.login = traced_login
    email_service._send_smtp = traced_send

    ok_all = True

    def line(ok: bool, label: str, detail: str = "") -> None:
        nonlocal ok_all
        ok_all = ok_all and ok
        print(f"    [{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))

    print(f"Database: local_dev.db   SMTP: {config.SMTP_HOST}:{config.SMTP_PORT} ({config.SMTP_SECURITY}); credentials not shown")
    print(f"Backend in use: {config.EMAIL_BACKEND} (dev_outbox is NOT used)")
    with TestClient(app) as client:
        for role, username, user_id, address in targets:
            before = {k: (v if not isinstance(v, list) else len(v)) for k, v in trace.items()}
            response = client.post("/auth/forgot-password", json={"email": address})
            self_service_reset.drain_background_work()
            print(f"  {role.upper()} account '{username}':")
            line(response.status_code == 202, "request accepted", f"status {response.status_code}")
            line(trace["connects"] == before["connects"] + 1, "one email handed to the SMTP client")
            line(trace["auth_ok"] == before["auth_ok"] + 1, "SMTP sign-in accepted by the server")
            line(trace["delivered"] == before["delivered"] + 1 and not trace["error"], "message accepted by the SMTP server", trace["error"] or "")
            body = trace["bodies"][-1] if trace["bodies"] else ""
            line("within 60 minutes" in body and "/reset-password#token=" in body, "email states 60 minutes and carries a link")
            conn = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
            rows = conn.execute(
                "SELECT created_at, expires_at, used_at FROM password_reset_tokens WHERE user_id=? ORDER BY id DESC", (user_id,)
            ).fetchall()
            conn.close()
            if rows:
                created, expires, used = rows[0]
                minutes = (datetime.fromisoformat(expires) - datetime.fromisoformat(created)).total_seconds() / 60
                line(round(minutes) == 60 and config.PASSWORD_RESET_TOKEN_MINUTES == 60, "link lifetime stored as 60 minutes", f"{minutes:.1f} min")
                line(used is None, "link is unused (password untouched)")
                unused = sum(1 for r in rows if r[2] is None)
                line(unused == 1, "only one live link for this account (earlier ones cancelled)", f"{unused} live")
            else:
                line(False, "a reset-link row was created")
    print()
    print("RESULT:", "both emails were accepted by the SMTP server." if ok_all else "at least one check failed.")
    if ok_all:
        print("Inbox delivery still needs your confirmation: look for 'Reset your ... password' (check Spam).")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
