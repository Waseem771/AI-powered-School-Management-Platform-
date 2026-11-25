"""The shared demo login: reads what an administrator reads, adds and edits, but never removes or touches accounts."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from database import engine
from main import app
from models.student import Student
from models.user import ROLE_DEMO, User, hash_password
from routers.auth import DEMO_REFUSAL, demo_may

DEMO_PASSWORD = "test-demo-1"
PUBLIC = {("POST", "/auth/login"), ("POST", "/auth/logout"), ("POST", "/auth/forgot-password"),
          ("POST", "/auth/reset-password"), ("POST", "/auth/reset-password/check")}


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def demo(client):
    with Session(engine) as session:
        session.add(User(username="demo.look", password_hash=hash_password(DEMO_PASSWORD), role=ROLE_DEMO))
        session.commit()
    token = client.post("/auth/login", json={"username": "demo.look", "password": DEMO_PASSWORD}).json()["access_token"]
    yield {"Authorization": f"Bearer {token}"}
    with Session(engine) as session:
        session.delete(session.exec(select(User).where(User.username == "demo.look")).one())
        session.commit()


@pytest.mark.parametrize("method, path, allowed", [
    ("POST", "/students", True),
    ("PUT", "/students/{student_id}", True),
    ("POST", "/fees/{invoice_id}/pay", True),
    ("POST", "/students/{student_id}/restore", True),
    ("DELETE", "/chatbot/history/{session_id}", True),
    ("DELETE", "/students/{student_id}", False),
    ("POST", "/students/{student_id}/archive", False),
    ("POST", "/teachers", False),
    ("POST", "/parents/{parent_id}/reset-password", False),
    ("POST", "/teachers/{teacher_id}/deactivate", False),
    ("DELETE", "/teacher-assignments/{assignment_id}", False),
])
def test_what_the_demo_role_may_do(method, path, allowed):
    assert demo_may(method, path) is allowed


def test_every_removal_and_account_route_refuses_the_demo_account(client, demo):
    problems, checked = [], 0
    for route_path, operations in app.openapi()["paths"].items():
        path = "/".join("1" if part.startswith("{") else part for part in route_path.split("/"))
        for method in (name.upper() for name in operations if name in {"post", "put", "delete", "patch"}):
            # Allowed routes are not called here: with no body some would really act. change-password is next test.
            if (method, route_path) in PUBLIC | {("POST", "/auth/change-password")} or demo_may(method, route_path):
                continue
            checked += 1
            response = client.request(method, path, headers=demo)
            if response.status_code != 403 or response.json().get("detail") != DEMO_REFUSAL:
                problems.append(f"{method} {route_path}: {response.status_code}")
    assert checked >= 15
    assert problems == []


def test_account_actions_are_refused_and_save_nothing(client, demo):
    payload = {"username": "sneaky", "full_name": "Sneaky", "password": "a-long-password-1"}

    response = client.post("/teachers", headers=demo, json=payload)
    assert response.status_code == 403
    assert response.json()["detail"] == DEMO_REFUSAL
    change = {"current_password": DEMO_PASSWORD, "new_password": "another-password-1"}
    assert client.post("/auth/change-password", headers=demo, json=change).status_code == 403
    with Session(engine) as session:
        assert session.exec(select(User).where(User.username == "sneaky")).first() is None


def test_the_demo_account_adds_and_edits_but_cannot_remove(client, demo):
    created = client.post("/students", headers=demo, json={
        "name": "Demo Visitor Student", "roll_number": "D-901", "grade": "Grade 8", "section": "A",
        "guardian_name": "Sample Guardian", "phone": "0300-1234567",
    })
    assert created.status_code == 201, created.text
    student_id = created.json()["id"]
    try:
        edited = client.put(f"/students/{student_id}", headers=demo, json={"name": "Demo Visitor Edited"})
        assert edited.status_code == 200, edited.text

        assert client.delete(f"/students/{student_id}", headers=demo).status_code == 403
        assert client.post(f"/students/{student_id}/archive", headers=demo).status_code == 403
        with Session(engine) as session:
            student = session.get(Student, student_id)
            assert student.name == "Demo Visitor Edited" and student.archived_at is None
    finally:
        with Session(engine) as session:
            session.delete(session.get(Student, student_id))
            session.commit()


@pytest.mark.parametrize("path", ["/students", "/fees", "/dashboard/stats", "/teachers", "/parents",
                                  "/attendance/overview", "/admissions/options"])
def test_the_demo_account_can_read_staff_and_admin_screens(client, demo, path):
    assert client.get(path, headers=demo).status_code == 200


@pytest.mark.parametrize("path", ["/teacher/profile", "/parent/profile"])
def test_the_demo_account_has_no_portal(client, demo, path):
    assert client.get(path, headers=demo).status_code == 403


def test_the_demo_account_may_ask_the_assistant(client, demo):
    response = client.post("/chatbot/ask", headers=demo, json={"question": "How many students are there?", "session_id": "demo"})
    assert response.status_code == 200
