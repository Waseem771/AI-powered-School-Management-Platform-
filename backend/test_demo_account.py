"""The shared demo login: reads what an administrator reads, changes nothing."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from database import engine
from main import app
from models.user import ROLE_DEMO, User, hash_password

DEMO_PASSWORD = "test-demo-1"
PUBLIC = {("POST", "/auth/login"), ("POST", "/auth/logout"), ("POST", "/auth/forgot-password"),
          ("POST", "/auth/reset-password"), ("POST", "/auth/reset-password/check")}
ALLOWED = {("POST", "/chatbot/ask"), ("DELETE", "/chatbot/history/{session_id}"), ("POST", "/ai/simulate")}


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


def test_every_write_route_refuses_the_demo_account(client, demo):
    problems, checked = [], 0
    for route_path, operations in app.openapi()["paths"].items():
        path = "/".join("1" if part.startswith("{") else part for part in route_path.split("/"))
        for method in (name.upper() for name in operations if name in {"post", "put", "delete", "patch"}):
            # change-password validates its body first; it is checked with a valid one in the next test.
            if (method, route_path) in PUBLIC | ALLOWED | {("POST", "/auth/change-password")}:
                continue
            checked += 1
            status = client.request(method, path, headers=demo).status_code
            if status != 403:
                problems.append(f"{method} {route_path}: {status}")
    assert checked > 30
    assert problems == []


def test_a_valid_write_is_refused_and_saves_nothing(client, demo):
    payload = {"username": "sneaky", "full_name": "Sneaky", "password": "a-long-password-1"}

    response = client.post("/teachers", headers=demo, json=payload)
    assert response.status_code == 403
    assert "cannot change anything" in response.json()["detail"]
    change = {"current_password": DEMO_PASSWORD, "new_password": "another-password-1"}
    assert client.post("/auth/change-password", headers=demo, json=change).status_code == 403
    with Session(engine) as session:
        assert session.exec(select(User).where(User.username == "sneaky")).first() is None


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
