"""Teacher accounts, role-based access, and the safety of the users-table upgrade."""
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

import migrate_db
from config import ALGORITHM, SECRET_KEY
from database import engine
from main import app
from models.user import User, hash_password

TEACHER_PASSWORD = "teacher-test-password-1"


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _login(client, username, password):
    return client.post("/auth/login", json={"username": username, "password": password})


@pytest.fixture()
def admin_token(client, admin_password):
    return _login(client, "admin", admin_password).json()["access_token"]


def _create(client, admin_token, **overrides):
    payload = {
        "username": "sara.khan",
        "full_name": "Sara Khan",
        "email": "sara.khan@example.test",
        "password": TEACHER_PASSWORD,
        **overrides,
    }
    return client.post("/teachers", headers=_bearer(admin_token), json=payload)


@pytest.fixture()
def teacher(client, admin_token):
    """A fresh teacher account for one test, removed afterwards so tests stay independent."""
    response = _create(client, admin_token)
    assert response.status_code == 201, response.text
    yield response.json()
    with Session(engine) as session:
        for user in session.exec(select(User).where(User.role == "teacher")).all():
            session.delete(user)
        session.commit()


@pytest.fixture()
def teacher_token(client, teacher):
    return _login(client, teacher["username"], TEACHER_PASSWORD).json()["access_token"]


# ── Admin manages teacher accounts ──────────────────────────────────────────

def test_admin_creates_a_teacher(client, teacher):
    assert teacher["role"] == "teacher"
    assert teacher["is_active"] is True
    assert teacher["full_name"] == "Sara Khan"
    assert teacher["email"] == "sara.khan@example.test"


def test_responses_never_contain_a_password_or_hash(client, admin_token, teacher):
    listing = client.get("/teachers", headers=_bearer(admin_token))

    assert listing.status_code == 200
    for body in (str(teacher), listing.text):
        assert "password" not in body.lower()
        assert "$2" not in body


def test_the_stored_password_is_hashed(teacher):
    with Session(engine) as session:
        stored = session.exec(select(User).where(User.username == teacher["username"])).one()

    assert stored.password_hash.startswith("$2")
    assert TEACHER_PASSWORD not in stored.password_hash


def test_duplicate_username_is_rejected_even_in_another_case(client, admin_token, teacher):
    same = _create(client, admin_token)
    different_case = _create(client, admin_token, username="SARA.KHAN", email="other@example.test")
    taking_admin = _create(client, admin_token, username="ADMIN", email="x@example.test")

    assert same.status_code == different_case.status_code == taking_admin.status_code == 409


def test_duplicate_email_is_rejected(client, admin_token, teacher):
    assert _create(client, admin_token, username="another.teacher").status_code == 409


@pytest.mark.parametrize(
    "overrides",
    [
        {"username": "ab"},
        {"username": "has space"},
        {"username": "bad/chars"},
        {"full_name": " "},
        {"email": "not-an-email"},
        {"password": "short"},
        {"password": "password123"},
        {"password": "x" * 73},
    ],
    ids=["short-name", "space", "chars", "blank-full-name", "bad-email", "short-pw", "common-pw", "long-pw"],
)
def test_invalid_teacher_input_is_rejected(client, admin_token, overrides):
    assert _create(client, admin_token, **overrides).status_code == 422


def test_admin_can_deactivate_and_reactivate(client, admin_token, teacher):
    url = f"/teachers/{teacher['id']}"

    off = client.post(f"{url}/deactivate", headers=_bearer(admin_token))
    assert off.status_code == 200 and off.json()["is_active"] is False
    assert client.post(f"{url}/deactivate", headers=_bearer(admin_token)).status_code == 200  # repeatable

    on = client.post(f"{url}/activate", headers=_bearer(admin_token))
    assert on.status_code == 200 and on.json()["is_active"] is True


def test_the_teacher_endpoints_cannot_touch_an_administrator(client, admin_token):
    with Session(engine) as session:
        admin_id = session.exec(select(User).where(User.username == "admin")).one().id

    assert client.post(f"/teachers/{admin_id}/deactivate", headers=_bearer(admin_token)).status_code == 404
    assert client.post("/teachers/999999/activate", headers=_bearer(admin_token)).status_code == 404
    with Session(engine) as session:
        assert session.exec(select(User).where(User.username == "admin")).one().is_active is True


def test_only_teacher_accounts_are_listed(client, admin_token, teacher):
    usernames = [row["username"] for row in client.get("/teachers", headers=_bearer(admin_token)).json()]

    assert usernames == [teacher["username"]]


# ── Signing in and out ──────────────────────────────────────────────────────

def test_teacher_logs_in_and_out(client, teacher):
    response = _login(client, teacher["username"], TEACHER_PASSWORD)

    assert response.status_code == 200
    assert response.json()["role"] == "teacher"
    token = response.json()["access_token"]
    assert client.get("/auth/me", headers=_bearer(token)).status_code == 200

    assert client.post("/auth/logout", headers=_bearer(token)).status_code == 204
    assert client.get("/auth/me", headers=_bearer(token)).status_code == 401


def test_teacher_with_wrong_password_is_rejected(client, teacher):
    assert _login(client, teacher["username"], "wrong-password").status_code == 401


def test_deactivated_teacher_cannot_log_in(client, admin_token, teacher):
    client.post(f"/teachers/{teacher['id']}/deactivate", headers=_bearer(admin_token))

    response = _login(client, teacher["username"], TEACHER_PASSWORD)

    assert response.status_code == 403
    assert "deactivated" in response.json()["detail"]
    assert "access_token" not in response.text


def test_a_wrong_password_on_a_deactivated_account_does_not_reveal_it(client, admin_token, teacher):
    client.post(f"/teachers/{teacher['id']}/deactivate", headers=_bearer(admin_token))

    assert _login(client, teacher["username"], "wrong-password").status_code == 401


def test_deactivation_ends_an_existing_token_at_once_and_reactivation_restores_it(
    client, admin_token, teacher, teacher_token
):
    assert client.get("/teacher/profile", headers=_bearer(teacher_token)).status_code == 200

    client.post(f"/teachers/{teacher['id']}/deactivate", headers=_bearer(admin_token))
    assert client.get("/teacher/profile", headers=_bearer(teacher_token)).status_code == 401
    assert client.get("/auth/me", headers=_bearer(teacher_token)).status_code == 401
    assert client.post(
        "/auth/change-password",
        headers=_bearer(teacher_token),
        json={"current_password": TEACHER_PASSWORD, "new_password": "another-password-12"},
    ).status_code == 401

    client.post(f"/teachers/{teacher['id']}/activate", headers=_bearer(admin_token))
    assert client.get("/teacher/profile", headers=_bearer(teacher_token)).status_code == 200


# ── What a teacher can and cannot reach ─────────────────────────────────────

def test_teacher_reaches_the_teacher_endpoints(client, teacher, teacher_token):
    profile = client.get("/teacher/profile", headers=_bearer(teacher_token))
    me = client.get("/auth/me", headers=_bearer(teacher_token))

    assert profile.status_code == me.status_code == 200
    assert profile.json()["username"] == teacher["username"]
    assert me.json()["full_name"] == "Sara Khan"
    assert me.json()["is_active"] is True


def test_teacher_endpoints_refuse_other_roles_and_anonymous_callers(client, admin_token):
    assert client.get("/teacher/profile").status_code == 401
    assert client.get("/teacher/profile", headers=_bearer(admin_token)).status_code == 403


@pytest.mark.parametrize(
    "method, path",
    [
        ("get", "/dashboard/stats"),
        ("get", "/fees"),
        ("get", "/fees/summary"),
        ("post", "/fees/generate"),
        ("get", "/students"),
        ("get", "/students/1"),
        ("post", "/students"),
        ("get", "/results/class"),
        ("get", "/admissions"),
        ("get", "/admissions/stats"),
        ("post", "/admissions/1/status"),
        ("post", "/admissions/1/enroll"),
        ("get", "/ai/at-risk"),
        ("post", "/chatbot/ask"),
        ("get", "/school/info"),
        ("get", "/teachers"),
        ("post", "/teachers"),
        ("post", "/teachers/1/activate"),
        ("post", "/teachers/1/deactivate"),
    ],
)
def test_teacher_is_refused_everywhere_outside_the_portal(client, teacher_token, method, path):
    response = getattr(client, method)(path, headers=_bearer(teacher_token))

    assert response.status_code == 403, f"{method.upper()} {path} answered {response.status_code}"


def test_teacher_cannot_create_or_change_users(client, teacher, teacher_token):
    payload = {"username": "sneaky.teacher", "full_name": "Sneaky", "password": TEACHER_PASSWORD}

    assert client.post("/teachers", headers=_bearer(teacher_token), json=payload).status_code == 403
    assert client.post(f"/teachers/{teacher['id']}/deactivate", headers=_bearer(teacher_token)).status_code == 403
    with Session(engine) as session:
        assert session.exec(select(User).where(User.username == "sneaky.teacher")).first() is None
        assert session.exec(select(User).where(User.username == teacher["username"])).one().is_active is True


def test_a_teacher_cannot_promote_themselves_by_forging_the_role_claim(client, teacher, teacher_token):
    claims = jwt.decode(teacher_token, SECRET_KEY, algorithms=[ALGORITHM])
    claims["role"] = "admin"
    forged = jwt.encode(claims, SECRET_KEY, algorithm=ALGORITHM)

    # The role is read from the database, never from the token.
    assert client.get("/students", headers=_bearer(forged)).status_code == 403
    assert client.get("/teachers", headers=_bearer(forged)).status_code == 403


def test_a_teacher_may_change_their_own_password_only(client, teacher, teacher_token):
    response = client.post(
        "/auth/change-password",
        headers=_bearer(teacher_token),
        json={"current_password": TEACHER_PASSWORD, "new_password": "changed-password-12"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "teacher"
    assert client.get("/teacher/profile", headers=_bearer(teacher_token)).status_code == 401


def test_every_route_is_either_public_or_refuses_a_teacher(client, teacher_token):
    """The audit: no school-data route may be reachable by a teacher, and none may be open to
    anonymous callers, except the ones listed here on purpose."""
    open_to_anyone = {("GET", "/"), ("GET", "/school/public"), ("POST", "/auth/login"), ("POST", "/auth/logout")}
    open_to_teachers = {
        ("GET", "/auth/me"),
        ("POST", "/auth/change-password"),
        ("GET", "/teacher/profile"),
    }
    problems = []
    checked = 0
    # The OpenAPI schema lists every route however the routers are nested.
    for route_path, operations in app.openapi()["paths"].items():
        path = "/".join("1" if part.startswith("{") else part for part in route_path.split("/"))
        for method in (name.upper() for name in operations if name in {"get", "post", "put", "delete", "patch"}):
            if (method, route_path) in open_to_anyone:
                continue
            checked += 1
            anonymous = client.request(method, path).status_code
            if anonymous != 401:
                problems.append(f"{method} {route_path}: anonymous got {anonymous}")
            if (method, route_path) in open_to_teachers:
                continue
            as_teacher = client.request(method, path, headers=_bearer(teacher_token)).status_code
            if as_teacher != 403:
                problems.append(f"{method} {route_path}: teacher got {as_teacher}")

    assert checked > 50, f"only {checked} routes were found, so this audit proves nothing"
    assert problems == []


# ── Existing behaviour is preserved ─────────────────────────────────────────

def test_existing_admin_still_signs_in_and_uses_staff_routes(client, admin_password):
    token = _login(client, "admin", admin_password).json()["access_token"]

    for path in ("/students", "/fees", "/dashboard/stats", "/admissions", "/school/info"):
        assert client.get(path, headers=_bearer(token)).status_code == 200, path
    me = client.get("/auth/me", headers=_bearer(token)).json()
    assert me["role"] == "admin" and me["is_active"] is True


@pytest.mark.parametrize("role", ["principal", "registrar", "staff"])
def test_other_staff_roles_keep_their_access(client, role):
    username = f"{role}.legacy"
    with Session(engine) as session:
        session.add(User(username=username, password_hash=hash_password(TEACHER_PASSWORD), role=role))
        session.commit()
    try:
        token = _login(client, username, TEACHER_PASSWORD).json()["access_token"]

        assert client.get("/students", headers=_bearer(token)).status_code == 200
        assert client.get("/admissions", headers=_bearer(token)).status_code == 200
        # Teacher management stays with administrators only.
        assert client.get("/teachers", headers=_bearer(token)).status_code == 403
    finally:
        with Session(engine) as session:
            session.delete(session.exec(select(User).where(User.username == username)).one())
            session.commit()


def test_a_deactivated_staff_account_loses_access_too(client):
    with Session(engine) as session:
        session.add(User(username="former.staff", password_hash=hash_password(TEACHER_PASSWORD), role="staff"))
        session.commit()
    try:
        token = _login(client, "former.staff", TEACHER_PASSWORD).json()["access_token"]
        with Session(engine) as session:
            user = session.exec(select(User).where(User.username == "former.staff")).one()
            user.is_active = False
            session.add(user)
            session.commit()

        assert client.get("/students", headers=_bearer(token)).status_code == 401
    finally:
        with Session(engine) as session:
            session.delete(session.exec(select(User).where(User.username == "former.staff")).one())
            session.commit()


def test_expired_and_revoked_teacher_tokens_are_rejected(client, teacher, teacher_token):
    claims = jwt.decode(teacher_token, SECRET_KEY, algorithms=[ALGORITHM])
    claims["exp"] = datetime.now(timezone.utc) - timedelta(minutes=1)
    expired = jwt.encode(claims, SECRET_KEY, algorithm=ALGORITHM)
    assert client.get("/teacher/profile", headers=_bearer(expired)).status_code == 401

    client.post("/auth/logout", headers=_bearer(teacher_token))
    assert client.get("/teacher/profile", headers=_bearer(teacher_token)).status_code == 401


# ── Upgrading an existing database ──────────────────────────────────────────

def _make_legacy_database(path, with_users=True):
    """The deployed schema: users has no is_active, full_name or email. Synthetic rows only."""
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE students (id INTEGER PRIMARY KEY, name VARCHAR NOT NULL, roll_number VARCHAR NOT NULL,
            grade VARCHAR NOT NULL, section VARCHAR NOT NULL, guardian_name VARCHAR NOT NULL,
            phone VARCHAR NOT NULL, dob VARCHAR, created_at DATETIME NOT NULL, archived_at DATETIME);
        CREATE TABLE invoices (id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL, amount FLOAT NOT NULL,
            month VARCHAR NOT NULL, due_date VARCHAR NOT NULL, challan_number VARCHAR NOT NULL,
            status VARCHAR NOT NULL, created_at DATETIME NOT NULL);
        CREATE TABLE payments (id INTEGER PRIMARY KEY, invoice_id INTEGER NOT NULL, amount_paid FLOAT NOT NULL,
            paid_at DATETIME NOT NULL, payment_mode VARCHAR NOT NULL);
        CREATE TABLE results (id INTEGER PRIMARY KEY, student_id INTEGER NOT NULL, subject VARCHAR NOT NULL,
            marks_obtained FLOAT NOT NULL, total_marks FLOAT NOT NULL, exam_type VARCHAR NOT NULL,
            academic_year_id INTEGER);
        INSERT INTO students VALUES (1, 'Sana Mirza', '001', 'Grade 7', 'A', 'Imran Mirza', '0301-2345678', NULL, '2025-08-01', NULL);
        INSERT INTO invoices VALUES (1, 1, 4000, 'October 2025', '10-Oct-2025', 'CHN-1', 'paid', '2025-10-01');
        INSERT INTO payments VALUES (1, 1, 4000, '2025-10-02', 'cash');
        INSERT INTO results VALUES (1, 1, 'English', 70, 100, 'Final Term', 1);
        CREATE UNIQUE INDEX uq_invoices_student_month ON invoices (student_id, month);
        CREATE UNIQUE INDEX uq_results_student_subject_exam_year ON results (student_id, subject, exam_type, academic_year_id);
        """
    )
    if with_users:
        connection.executescript(
            """
            CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR NOT NULL, password_hash VARCHAR NOT NULL,
                role VARCHAR NOT NULL, created_at DATETIME NOT NULL);
            CREATE UNIQUE INDEX ix_users_username ON users (username);
            INSERT INTO users VALUES (1, 'admin', '$2b$12$syntheticsyntheticsyntheticsyntheticsyntheticsynthe', 'admin', '2025-08-01');
            INSERT INTO users VALUES (7, 'legacy.registrar', 'aaaa1111legacy-sha256-style-hash', 'registrar', '2025-09-01');
            """
        )
    connection.commit()
    connection.close()


def _users(path):
    connection = sqlite3.connect(path)
    rows = connection.execute("SELECT id, username, password_hash, role, created_at FROM users ORDER BY id").fetchall()
    connection.close()
    return rows


def _user_columns(path):
    connection = sqlite3.connect(path)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
    connection.close()
    return columns


def test_the_upgrade_adds_the_user_columns_and_keeps_every_account(tmp_path):
    db = tmp_path / "school.db"
    _make_legacy_database(db)
    before = _users(db)

    assert migrate_db.main([str(db), "--apply"]) == 0

    assert {"is_active", "full_name", "email"} <= _user_columns(db)
    assert _users(db) == before
    connection = sqlite3.connect(db)
    # Nobody who could sign in before is locked out, and nobody gained or lost a role.
    assert connection.execute("SELECT count(*) FROM users WHERE is_active = 1").fetchone() == (2,)
    assert connection.execute("SELECT role FROM users ORDER BY id").fetchall() == [("admin",), ("registrar",)]
    assert connection.execute("SELECT count(*) FROM students").fetchone() == (1,)
    connection.close()
    assert len(list(tmp_path.glob("*.backup-*"))) == 1


def test_the_user_upgrade_is_repeatable(tmp_path, capsys):
    db = tmp_path / "school.db"
    _make_legacy_database(db)
    migrate_db.main([str(db), "--apply"])
    snapshot = db.read_bytes()
    backups = list(tmp_path.glob("*.backup-*"))

    assert migrate_db.main([str(db), "--apply"]) == 0
    assert "Already upgraded" in capsys.readouterr().out
    assert db.read_bytes() == snapshot
    assert list(tmp_path.glob("*.backup-*")) == backups


def test_the_user_upgrade_is_reported_before_it_is_applied(tmp_path, capsys):
    db = tmp_path / "school.db"
    _make_legacy_database(db)
    before = db.read_bytes()

    assert migrate_db.main([str(db)]) == 0

    assert db.read_bytes() == before
    assert "3 change(s) waiting" in capsys.readouterr().out


def test_a_database_without_a_users_table_is_left_for_the_app_to_create(tmp_path, capsys):
    db = tmp_path / "school.db"
    _make_legacy_database(db, with_users=False)

    assert migrate_db.main([str(db), "--apply"]) == 0
    assert "Already upgraded" in capsys.readouterr().out


def test_the_app_refuses_to_start_on_an_unupgraded_users_table_and_starts_after_the_upgrade(tmp_path):
    from sqlalchemy import create_engine

    from database import schema_problems

    db = tmp_path / "school.db"
    _make_legacy_database(db)
    legacy_engine = create_engine(f"sqlite:///{db.as_posix()}")
    try:
        assert {"users.is_active", "users.full_name", "users.email"} <= set(schema_problems(legacy_engine))

        migrate_db.main([str(db), "--apply"])

        assert [problem for problem in schema_problems(legacy_engine) if problem.startswith("users.")] == []
        # A legacy account can sign in through the real model once upgraded.
        with Session(legacy_engine) as session:
            legacy = session.exec(select(User).where(User.username == "legacy.registrar")).one()
            assert legacy.is_active is True and legacy.role == "registrar" and legacy.full_name is None
    finally:
        legacy_engine.dispose()


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
