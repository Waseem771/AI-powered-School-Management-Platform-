"""Administrator password reset for teacher accounts, for a teacher who forgot their password. It follows the
same rules as for parents: policy, hashing, ended sessions, a forced change at next sign-in, administrator-only
access and an audit record without the password. Synthetic accounts only, removed after each test."""
import logging
import sys

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from database import engine
from main import app
from models.attendance import TeacherClassAssignment
from models.fee import AcademicYear
from models.parent import ParentStudentLink
from models.user import PasswordResetEvent, RevokedToken, User, hash_password
from services.password_reset import PASSWORD_CHANGE_REQUIRED

ORIGINAL = "teacher-original-password-1"
TEMPORARY = "temporary-teacher-reset-1"
CHOSEN = "teacher-chosen-password-9"
PARENT_PASSWORD = "parent-test-password-1"


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
        for model in (PasswordResetEvent, TeacherClassAssignment, ParentStudentLink, RevokedToken):
            for row in session.exec(select(model)).all():
                session.delete(row)
        for user in session.exec(select(User).where(User.role.in_(["teacher", "parent", "registrar"]))).all():
            session.delete(user)
        session.commit()


@pytest.fixture()
def admin_token(client, admin_password):
    return _login(client, "admin", admin_password).json()["access_token"]


def _make_teacher(client, admin_token, username="sara.forgot", email="sara.forgot@example.test"):
    response = client.post("/teachers", headers=_bearer(admin_token), json={
        "username": username, "full_name": "Sara Forgot", "email": email, "password": ORIGINAL})
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture()
def teacher(client, admin_token):
    return _make_teacher(client, admin_token)


def _reset(client, admin_token, teacher_id, password=TEMPORARY):
    return client.post(f"/teachers/{teacher_id}/reset-password", headers=_bearer(admin_token),
                       json={"new_password": password})


def _events():
    with Session(engine) as session:
        return session.exec(select(PasswordResetEvent)).all()


# ── The reset itself ────────────────────────────────────────────────────────

def test_admin_resets_a_forgotten_teacher_password(client, admin_token, teacher):
    response = _reset(client, admin_token, teacher["id"])

    assert response.status_code == 200
    body = response.json()
    assert "must choose a new password" in body["message"]
    assert body["teacher"]["must_change_password"] is True and body["teacher"]["last_password_reset"]
    assert _login(client, teacher["username"], ORIGINAL).status_code == 401
    assert _login(client, teacher["username"], TEMPORARY).status_code == 200


def test_no_response_contains_a_password_or_hash(client, admin_token, teacher):
    reset = _reset(client, admin_token, teacher["id"])
    listing = client.get("/teachers", headers=_bearer(admin_token))
    login = _login(client, teacher["username"], TEMPORARY)
    blocked = client.get("/teacher/profile", headers=_bearer(login.json()["access_token"]))

    for response in (reset, listing, login, blocked):
        assert TEMPORARY not in response.text and ORIGINAL not in response.text
        assert "$2" not in response.text and "password_hash" not in response.text


def test_the_new_password_is_stored_only_as_a_hash_and_never_logged(client, admin_token, teacher, caplog):
    with caplog.at_level(logging.DEBUG):
        _reset(client, admin_token, teacher["id"])
        _reset(client, admin_token, teacher["id"], password="refused-weak")

    with Session(engine) as session:
        stored = session.exec(select(User).where(User.username == teacher["username"])).one()
    assert stored.password_hash.startswith("$2") and TEMPORARY not in stored.password_hash
    assert TEMPORARY not in caplog.text and "refused-weak" not in caplog.text
    for event in _events():
        assert TEMPORARY not in str(event.model_dump())


@pytest.mark.parametrize("weak", ["short", "password123", "x" * 73, "admin123"], ids=["short", "common", "too-long", "default"])
def test_the_existing_password_policy_applies(client, admin_token, teacher, weak):
    response = _reset(client, admin_token, teacher["id"], password=weak)

    assert response.status_code == 422 and "not acceptable" in str(response.json()["detail"])
    assert weak not in response.text
    assert _login(client, teacher["username"], ORIGINAL).status_code == 200
    assert _events() == []


def test_an_empty_or_missing_password_is_rejected(client, admin_token, teacher):
    url = f"/teachers/{teacher['id']}/reset-password"
    for payload in ({}, {"new_password": ""}, {"new_password": None}):
        assert client.post(url, headers=_bearer(admin_token), json=payload).status_code == 422


# ── Sessions end, and the change is forced ──────────────────────────────────

def test_every_existing_session_ends_at_once(client, admin_token, teacher):
    first = _login(client, teacher["username"], ORIGINAL).json()["access_token"]
    second = _login(client, teacher["username"], ORIGINAL).json()["access_token"]
    assert client.get("/teacher/profile", headers=_bearer(first)).status_code == 200

    _reset(client, admin_token, teacher["id"])

    for token in (first, second):
        assert client.get("/teacher/profile", headers=_bearer(token)).status_code == 401
        assert client.get("/teacher/classes", headers=_bearer(token)).status_code == 401
        assert client.get("/auth/me", headers=_bearer(token)).status_code == 401


def test_the_teacher_must_change_the_password_before_anything_else(client, admin_token, teacher):
    _reset(client, admin_token, teacher["id"])
    login = _login(client, teacher["username"], TEMPORARY).json()
    token = login["access_token"]

    assert login["must_change_password"] is True
    me = client.get("/auth/me", headers=_bearer(token))
    assert me.status_code == 200 and me.json()["must_change_password"] is True
    for path in ("/teacher/profile", "/teacher/classes", "/students", "/fees"):
        response = client.get(path, headers=_bearer(token))
        assert response.status_code == 403 and response.json()["detail"] == PASSWORD_CHANGE_REQUIRED, path


def test_every_route_is_closed_to_a_teacher_who_must_change_their_password(client, admin_token, teacher):
    _reset(client, admin_token, teacher["id"])
    token = _login(client, teacher["username"], TEMPORARY).json()["access_token"]
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

    assert checked > 60 and problems == []


def test_choosing_a_new_password_opens_the_teacher_portal_again(client, admin_token, teacher):
    _reset(client, admin_token, teacher["id"])
    token = _login(client, teacher["username"], TEMPORARY).json()["access_token"]

    same = client.post("/auth/change-password", headers=_bearer(token),
                       json={"current_password": TEMPORARY, "new_password": TEMPORARY})
    changed = client.post("/auth/change-password", headers=_bearer(token),
                          json={"current_password": TEMPORARY, "new_password": CHOSEN})

    assert same.status_code == 422
    assert changed.status_code == 200 and changed.json()["must_change_password"] is False
    new_token = changed.json()["access_token"]
    assert client.get("/teacher/profile", headers=_bearer(new_token)).status_code == 200
    assert client.get("/teacher/classes", headers=_bearer(new_token)).status_code == 200
    assert _login(client, teacher["username"], TEMPORARY).status_code == 401
    assert _login(client, teacher["username"], CHOSEN).json()["must_change_password"] is False
    assert all(event.completed_at is not None for event in _events())


def test_a_teacher_can_still_sign_out_while_a_change_is_pending(client, admin_token, teacher):
    _reset(client, admin_token, teacher["id"])
    token = _login(client, teacher["username"], TEMPORARY).json()["access_token"]

    assert client.post("/auth/logout", headers=_bearer(token)).status_code == 204
    assert client.get("/auth/me", headers=_bearer(token)).status_code == 401


# ── Who may reset, and whose ────────────────────────────────────────────────

def test_only_an_administrator_can_reset(client, admin_token, teacher):
    with Session(engine) as session:
        session.add(User(username="reg.reset", password_hash=hash_password("registrar-pw-12345"), role="registrar"))
        session.commit()
    client.post("/parents", headers=_bearer(admin_token), json={
        "username": "mr.reset", "full_name": "Mr Reset", "password": PARENT_PASSWORD,
        "student_ids": [_first_student_id()]})
    own = _login(client, teacher["username"], ORIGINAL).json()["access_token"]
    registrar = _login(client, "reg.reset", "registrar-pw-12345").json()["access_token"]
    parent = _login(client, "mr.reset", PARENT_PASSWORD).json()["access_token"]
    url = f"/teachers/{teacher['id']}/reset-password"

    assert client.post(url, json={"new_password": TEMPORARY}).status_code == 401
    for token in (own, registrar, parent):  # a teacher cannot even reset their own password this way
        assert client.post(url, headers=_bearer(token), json={"new_password": TEMPORARY}).status_code == 403
    assert _login(client, teacher["username"], ORIGINAL).status_code == 200
    assert _events() == []


def _first_student_id():
    from models.student import Student
    with Session(engine) as session:
        return session.exec(select(Student)).first().id


def test_the_endpoint_can_reset_only_teacher_accounts(client, admin_token, admin_password):
    client.post("/parents", headers=_bearer(admin_token), json={
        "username": "mr.reset", "full_name": "Mr Reset", "password": PARENT_PASSWORD,
        "student_ids": [_first_student_id()]})
    with Session(engine) as session:
        admin_id = session.exec(select(User).where(User.username == "admin")).one().id
        parent_id = session.exec(select(User).where(User.username == "mr.reset")).one().id

    for target in (admin_id, parent_id, 999999):
        assert _reset(client, admin_token, target).status_code == 404
    assert _login(client, "admin", admin_password).status_code == 200  # the administrator's password is untouched
    assert _login(client, "mr.reset", PARENT_PASSWORD).json()["must_change_password"] is False
    assert _events() == []


def test_parents_cannot_be_reset_through_the_teacher_route_and_teachers_not_through_the_parent_route(client, admin_token, teacher):
    assert client.post(f"/parents/{teacher['id']}/reset-password", headers=_bearer(admin_token),
                       json={"new_password": TEMPORARY}).status_code == 404
    assert _login(client, teacher["username"], ORIGINAL).status_code == 200


# ── Records are preserved, and the list shows the state ─────────────────────

def test_classes_other_teachers_and_a_deactivated_account_are_unaffected(client, admin_token, teacher):
    other = _make_teacher(client, admin_token, username="other.teacher", email="other.teacher@example.test")
    with Session(engine) as session:
        year = session.exec(select(AcademicYear).where(AcademicYear.is_current == True)).first()  # noqa: E712
        session.add(TeacherClassAssignment(teacher_id=teacher["id"], grade="Grade 6", section="A", academic_year_id=year.id))
        session.commit()
    client.post(f"/teachers/{teacher['id']}/deactivate", headers=_bearer(admin_token))

    response = _reset(client, admin_token, teacher["id"])

    assert response.status_code == 200 and response.json()["teacher"]["is_active"] is False  # a reset does not reactivate
    assert _login(client, teacher["username"], TEMPORARY).status_code == 403  # still deactivated
    assert _login(client, other["username"], ORIGINAL).json()["must_change_password"] is False
    listing = {row["username"]: row for row in client.get("/teachers", headers=_bearer(admin_token)).json()}
    assert listing[teacher["username"]]["must_change_password"] is True
    assert listing[other["username"]]["must_change_password"] is False
    assert listing[other["username"]]["last_password_reset"] is None
    with Session(engine) as session:
        assert len(session.exec(select(TeacherClassAssignment)).all()) == 1


def test_the_flag_clears_in_the_list_after_the_teacher_chooses_a_password(client, admin_token, teacher):
    _reset(client, admin_token, teacher["id"])
    token = _login(client, teacher["username"], TEMPORARY).json()["access_token"]
    client.post("/auth/change-password", headers=_bearer(token),
                json={"current_password": TEMPORARY, "new_password": CHOSEN})

    row = client.get("/teachers", headers=_bearer(admin_token)).json()[0]

    assert row["must_change_password"] is False and row["last_password_reset"]


def test_the_reset_is_recorded_with_who_and_when_but_no_password(client, admin_token, teacher):
    _reset(client, admin_token, teacher["id"])
    _reset(client, admin_token, teacher["id"], password="short")  # refused, so not recorded

    with Session(engine) as session:
        admin_id = session.exec(select(User).where(User.username == "admin")).one().id
    events = _events()

    assert len(events) == 1
    assert events[0].user_id == teacher["id"] and events[0].reset_by == admin_id and events[0].completed_at is None
    assert set(PasswordResetEvent.model_fields) == {"id", "user_id", "reset_by", "reset_at", "completed_at"}


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
