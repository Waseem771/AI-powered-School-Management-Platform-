"""Administrator password reset for parent accounts: policy, hashing, ended sessions, the forced change at
next sign-in, access control, and the audit record. Synthetic accounts only, removed after each test."""
import logging
import sys

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from database import engine
from main import app
from models.parent import ParentStudentLink
from models.student import Student
from models.user import PasswordResetEvent, RevokedToken, User, hash_password
from services.password_reset import PASSWORD_CHANGE_REQUIRED

ORIGINAL = "parent-original-password-1"
TEMPORARY = "temporary-reset-password-1"
SECOND = "second-temporary-pw-2"
CHOSEN = "parent-chosen-password-9"
TEACHER_PASSWORD = "teacher-test-password-1"


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def _bearer(token):
    return {"Authorization": f"Bearer {token}"}


def _login(client, username, password):
    return client.post("/auth/login", json={"username": username, "password": password})


@pytest.fixture(autouse=True)
def clean_up():
    yield
    with Session(engine) as session:
        for model in (PasswordResetEvent, ParentStudentLink, RevokedToken):
            for row in session.exec(select(model)).all():
                session.delete(row)
        for user in session.exec(select(User).where(User.role.in_(["parent", "teacher", "registrar"]))).all():
            session.delete(user)
        session.commit()


@pytest.fixture()
def admin_token(client, admin_password):
    return _login(client, "admin", admin_password).json()["access_token"]


def _student_id(roll):
    with Session(engine) as session:
        return session.exec(select(Student).where(Student.roll_number == roll)).one().id


def _make_parent(client, admin_token, username="mr.reset", email="reset@example.test", roll="045"):
    response = client.post("/parents", headers=_bearer(admin_token), json={
        "username": username, "full_name": "Reset Parent", "email": email, "password": ORIGINAL,
        "student_ids": [_student_id(roll)], "relationship": "Father"})
    assert response.status_code == 201, response.text
    return response.json()


def _make_teacher(client, admin_token):
    client.post("/teachers", headers=_bearer(admin_token), json={
        "username": "sara.reset", "full_name": "Sara Reset", "password": TEACHER_PASSWORD})


@pytest.fixture()
def parent(client, admin_token):
    return _make_parent(client, admin_token)


def _reset(client, admin_token, parent_id, password=TEMPORARY):
    return client.post(f"/parents/{parent_id}/reset-password", headers=_bearer(admin_token),
                       json={"new_password": password})


def _events():
    with Session(engine) as session:
        return session.exec(select(PasswordResetEvent)).all()


# ── The reset itself ────────────────────────────────────────────────────────

def test_admin_resets_a_parent_password(client, admin_token, parent):
    response = _reset(client, admin_token, parent["id"])

    assert response.status_code == 200
    body = response.json()
    assert "must choose a new password" in body["message"]
    assert body["parent"]["must_change_password"] is True
    assert body["parent"]["last_password_reset"]
    assert _login(client, parent["username"], ORIGINAL).status_code == 401
    assert _login(client, parent["username"], TEMPORARY).status_code == 200


def test_no_response_contains_a_password_or_hash(client, admin_token, parent):
    reset = _reset(client, admin_token, parent["id"])
    listing = client.get("/parents", headers=_bearer(admin_token))
    login = _login(client, parent["username"], TEMPORARY)
    blocked = client.get("/parent/profile", headers=_bearer(login.json()["access_token"]))

    for response in (reset, listing, login, blocked):
        assert TEMPORARY not in response.text and ORIGINAL not in response.text
        assert "$2" not in response.text and "password_hash" not in response.text


def test_the_new_password_is_stored_only_as_a_hash(client, admin_token, parent):
    _reset(client, admin_token, parent["id"])

    with Session(engine) as session:
        stored = session.exec(select(User).where(User.username == parent["username"])).one()

    assert stored.password_hash.startswith("$2") and TEMPORARY not in stored.password_hash
    for event in _events():
        assert TEMPORARY not in str(event.model_dump())


def test_the_password_is_never_logged(client, admin_token, parent, caplog):
    with caplog.at_level(logging.DEBUG):
        _reset(client, admin_token, parent["id"])
        _reset(client, admin_token, parent["id"], password="refused-weak")

    assert TEMPORARY not in caplog.text and "refused-weak" not in caplog.text


@pytest.mark.parametrize("weak", ["short", "password123", "x" * 73, "admin123"], ids=["short", "common", "too-long", "default"])
def test_the_existing_password_policy_applies(client, admin_token, parent, weak):
    response = _reset(client, admin_token, parent["id"], password=weak)

    assert response.status_code == 422
    assert "not acceptable" in str(response.json()["detail"])
    assert weak not in response.text
    # Nothing changed: the old password still works and no forced change was set.
    assert _login(client, parent["username"], ORIGINAL).status_code == 200
    assert _events() == []


def test_an_empty_or_missing_password_is_rejected(client, admin_token, parent):
    url = f"/parents/{parent['id']}/reset-password"
    for payload in ({}, {"new_password": ""}, {"new_password": None}):
        assert client.post(url, headers=_bearer(admin_token), json=payload).status_code == 422


# ── Sessions end at once ────────────────────────────────────────────────────

def test_every_existing_session_ends_at_once(client, admin_token, parent):
    first = _login(client, parent["username"], ORIGINAL).json()["access_token"]
    second = _login(client, parent["username"], ORIGINAL).json()["access_token"]
    assert client.get("/parent/children", headers=_bearer(first)).status_code == 200

    _reset(client, admin_token, parent["id"])

    for token in (first, second):
        assert client.get("/parent/children", headers=_bearer(token)).status_code == 401
        assert client.get("/auth/me", headers=_bearer(token)).status_code == 401
        assert client.post("/auth/change-password", headers=_bearer(token),
                           json={"current_password": ORIGINAL, "new_password": CHOSEN}).status_code == 401


# ── The forced change ───────────────────────────────────────────────────────

def test_the_parent_must_change_the_password_before_anything_else(client, admin_token, parent):
    _reset(client, admin_token, parent["id"])
    login = _login(client, parent["username"], TEMPORARY).json()
    token = login["access_token"]

    assert login["must_change_password"] is True
    me = client.get("/auth/me", headers=_bearer(token))
    assert me.status_code == 200 and me.json()["must_change_password"] is True
    child = parent["children"][0]["student_id"]
    for path in ("/parent/profile", "/parent/children", f"/parent/children/{child}/fees",
                 f"/parent/children/{child}/attendance", f"/parent/children/{child}/results", "/students", "/fees"):
        response = client.get(path, headers=_bearer(token))
        assert response.status_code == 403, path
        assert response.json()["detail"] == PASSWORD_CHANGE_REQUIRED, path


def test_every_route_is_closed_to_an_account_that_must_change_its_password(client, admin_token, parent):
    """The audit: with a forced change pending, only the account's own routes answer. Every other route in the
    schema, staff, teacher, admin and parent alike, refuses with 403, so the change cannot be skipped."""
    _reset(client, admin_token, parent["id"])
    token = _login(client, parent["username"], TEMPORARY).json()["access_token"]
    open_routes = {("GET", "/"), ("GET", "/school/public"), ("POST", "/auth/login"), ("POST", "/auth/logout"),
                   ("POST", "/auth/forgot-password"), ("POST", "/auth/reset-password"), ("POST", "/auth/reset-password/check"),
                   ("GET", "/auth/me"), ("POST", "/auth/change-password")}
    problems, checked = [], 0
    for route_path, operations in app.openapi()["paths"].items():
        path = "/".join("1" if part.startswith("{") else part for part in route_path.split("/"))
        for method in (name.upper() for name in operations if name in {"get", "post", "put", "delete", "patch"}):
            if (method, route_path) in open_routes:
                continue
            checked += 1
            status = client.request(method, path, headers=_bearer(token)).status_code
            if status != 403:
                problems.append(f"{method} {route_path}: answered {status}")

    assert checked > 60, f"only {checked} routes were found, so this audit proves nothing"
    assert problems == []


def test_a_reset_does_not_end_the_administrators_own_session(client, admin_token, parent):
    _reset(client, admin_token, parent["id"])

    assert client.get("/parents", headers=_bearer(admin_token)).status_code == 200
    assert client.get("/students", headers=_bearer(admin_token)).status_code == 200


def test_changing_the_password_ends_the_forced_change(client, admin_token, parent):
    _reset(client, admin_token, parent["id"])
    token = _login(client, parent["username"], TEMPORARY).json()["access_token"]

    changed = client.post("/auth/change-password", headers=_bearer(token),
                          json={"current_password": TEMPORARY, "new_password": CHOSEN})

    assert changed.status_code == 200 and changed.json()["must_change_password"] is False
    new_token = changed.json()["access_token"]
    assert client.get("/parent/children", headers=_bearer(new_token)).status_code == 200
    assert client.get("/auth/me", headers=_bearer(new_token)).json()["must_change_password"] is False
    assert _login(client, parent["username"], TEMPORARY).status_code == 401
    assert _login(client, parent["username"], CHOSEN).json()["must_change_password"] is False
    assert all(event.completed_at is not None for event in _events())


def test_the_temporary_password_cannot_be_kept(client, admin_token, parent):
    _reset(client, admin_token, parent["id"])
    token = _login(client, parent["username"], TEMPORARY).json()["access_token"]

    same = client.post("/auth/change-password", headers=_bearer(token),
                       json={"current_password": TEMPORARY, "new_password": TEMPORARY})
    weak = client.post("/auth/change-password", headers=_bearer(token),
                       json={"current_password": TEMPORARY, "new_password": "short"})
    wrong = client.post("/auth/change-password", headers=_bearer(token),
                        json={"current_password": "not-it-at-all-1", "new_password": CHOSEN})

    assert (same.status_code, weak.status_code, wrong.status_code) == (422, 422, 400)
    assert client.get("/parent/children", headers=_bearer(token)).status_code == 403  # still locked


def test_a_parent_can_still_sign_out_while_a_change_is_pending(client, admin_token, parent):
    _reset(client, admin_token, parent["id"])
    token = _login(client, parent["username"], TEMPORARY).json()["access_token"]

    assert client.post("/auth/logout", headers=_bearer(token)).status_code == 204
    assert client.get("/auth/me", headers=_bearer(token)).status_code == 401


def test_a_second_reset_replaces_the_first_and_both_are_recorded(client, admin_token, parent):
    _reset(client, admin_token, parent["id"])
    _reset(client, admin_token, parent["id"], password=SECOND)

    assert _login(client, parent["username"], TEMPORARY).status_code == 401
    token = _login(client, parent["username"], SECOND).json()["access_token"]
    client.post("/auth/change-password", headers=_bearer(token),
                json={"current_password": SECOND, "new_password": CHOSEN})
    events = _events()
    assert len(events) == 2 and all(event.completed_at for event in events)


def test_ordinary_accounts_are_not_forced_to_change_anything(client, admin_password, parent):
    login = _login(client, "admin", admin_password).json()

    assert login["must_change_password"] is False
    assert _login(client, parent["username"], ORIGINAL).json()["must_change_password"] is False
    assert client.get("/students", headers=_bearer(login["access_token"])).status_code == 200


# ── Who may reset ───────────────────────────────────────────────────────────

def test_only_an_administrator_can_reset(client, admin_token, parent):
    _make_teacher(client, admin_token)
    with Session(engine) as session:
        session.add(User(username="reg.reset", password_hash=hash_password("registrar-pw-12345"), role="registrar"))
        session.commit()
    teacher = _login(client, "sara.reset", TEACHER_PASSWORD).json()["access_token"]
    registrar = _login(client, "reg.reset", "registrar-pw-12345").json()["access_token"]
    parent_token = _login(client, parent["username"], ORIGINAL).json()["access_token"]
    url = f"/parents/{parent['id']}/reset-password"

    assert client.post(url, json={"new_password": TEMPORARY}).status_code == 401
    for token in (teacher, registrar, parent_token):
        assert client.post(url, headers=_bearer(token), json={"new_password": TEMPORARY}).status_code == 403
    assert _login(client, parent["username"], ORIGINAL).status_code == 200
    assert _events() == []


def test_a_parent_cannot_reset_their_own_or_another_parents_password(client, admin_token, parent):
    other = _make_parent(client, admin_token, username="mr.other", email="other@example.test", roll="012")
    token = _login(client, parent["username"], ORIGINAL).json()["access_token"]

    for target in (parent["id"], other["id"]):
        assert client.post(f"/parents/{target}/reset-password", headers=_bearer(token),
                           json={"new_password": TEMPORARY}).status_code == 403
    assert _login(client, other["username"], ORIGINAL).status_code == 200


def test_the_endpoint_can_reset_only_parent_accounts(client, admin_token, admin_password):
    _make_teacher(client, admin_token)
    with Session(engine) as session:
        admin_id = session.exec(select(User).where(User.username == "admin")).one().id
        teacher_id = session.exec(select(User).where(User.username == "sara.reset")).one().id

    for target in (admin_id, teacher_id, 999999):
        assert _reset(client, admin_token, target).status_code == 404
    assert _login(client, "admin", admin_password).status_code == 200  # the administrator's password is untouched
    assert _login(client, "sara.reset", TEACHER_PASSWORD).status_code == 200
    assert _events() == []


# ── Records are preserved ───────────────────────────────────────────────────

def test_links_other_parents_and_a_deactivated_account_are_unaffected(client, admin_token, parent):
    other = _make_parent(client, admin_token, username="mr.other", email="other@example.test", roll="012")
    client.post(f"/parents/{parent['id']}/deactivate", headers=_bearer(admin_token))

    response = _reset(client, admin_token, parent["id"])

    assert response.status_code == 200
    body = response.json()["parent"]
    assert body["is_active"] is False  # a reset does not reactivate
    assert body["children"] == parent["children"]
    assert _login(client, parent["username"], TEMPORARY).status_code == 403  # still deactivated
    assert _login(client, other["username"], ORIGINAL).json()["must_change_password"] is False
    listing = {row["username"]: row for row in client.get("/parents", headers=_bearer(admin_token)).json()}
    assert listing[other["username"]]["must_change_password"] is False
    assert listing[other["username"]]["last_password_reset"] is None
    assert listing[parent["username"]]["must_change_password"] is True
    with Session(engine) as session:
        assert len(session.exec(select(ParentStudentLink)).all()) == 2


# ── Audit record ────────────────────────────────────────────────────────────

def test_the_reset_is_recorded_with_who_and_when_but_no_password(client, admin_token, parent):
    _reset(client, admin_token, parent["id"])

    with Session(engine) as session:
        admin_id = session.exec(select(User).where(User.username == "admin")).one().id
    events = _events()

    assert len(events) == 1
    event = events[0]
    assert event.user_id == parent["id"] and event.reset_by == admin_id
    assert event.reset_at is not None and event.completed_at is None
    assert set(PasswordResetEvent.model_fields) == {"id", "user_id", "reset_by", "reset_at", "completed_at"}


def test_a_refused_reset_leaves_no_record(client, admin_token, parent):
    _reset(client, admin_token, parent["id"], password="short")
    _reset(client, admin_token, 999999)

    assert _events() == []


# ── Schema ──────────────────────────────────────────────────────────────────

def test_only_a_new_table_was_added():
    from sqlalchemy import inspect

    inspector = inspect(engine)
    assert "password_reset_events" in inspector.get_table_names()
    assert {c["name"] for c in inspector.get_columns("users")} == {
        "id", "username", "password_hash", "role", "created_at", "is_active", "full_name", "email"}


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
