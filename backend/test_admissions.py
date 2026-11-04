"""The Admissions feature must be protected, and must not be able to stop the app starting."""
import builtins
import sys
import types

import pytest
from fastapi.testclient import TestClient

from main import app

EVALUATE_URL = "/api/admissions-crew/evaluate"
KNOWN_ROLL = "045"


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def auth_headers(client):
    login = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    client.cookies.clear()
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _body(roll=KNOWN_ROLL):
    return {"student_roll_number": roll, "desired_program": "Grade 9"}


def test_anonymous_request_is_rejected_before_any_student_lookup(client):
    response = client.post(EVALUATE_URL, json=_body())

    assert response.status_code == 401


def test_unknown_roll_number_returns_404(client, auth_headers):
    response = client.post(EVALUATE_URL, json=_body("no-such-roll"), headers=auth_headers)

    assert response.status_code == 404


def test_returns_503_with_clear_message_when_crewai_is_not_installed(client, auth_headers, monkeypatch):
    real_import = builtins.__import__

    def import_without_crewai(name, *args, **kwargs):
        if name == "crewai" or name.startswith("school_crew"):
            raise ImportError("crewai is not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.delitem(sys.modules, "school_crew.crew", raising=False)
    monkeypatch.setattr(builtins, "__import__", import_without_crewai)

    response = client.post(EVALUATE_URL, json=_body(), headers=auth_headers)

    assert response.status_code == 503
    assert "not available" in response.json()["detail"]


def test_returns_503_without_leaking_details_when_the_ai_call_fails(client, auth_headers, monkeypatch):
    def failing_crew(*_args):
        raise RuntimeError("upstream said: secret-internal-detail")

    stub = types.ModuleType("school_crew.crew")
    stub.run_admissions_crew = failing_crew
    monkeypatch.setitem(sys.modules, "school_crew.crew", stub)

    response = client.post(EVALUATE_URL, json=_body(), headers=auth_headers)

    assert response.status_code == 503
    assert "secret-internal-detail" not in response.text


def test_student_contact_details_are_not_sent_to_the_ai(client, auth_headers, monkeypatch):
    captured = {}

    def recording_crew(profile, program):
        captured["profile"] = profile
        return "Recommendation text"

    stub = types.ModuleType("school_crew.crew")
    stub.run_admissions_crew = recording_crew
    monkeypatch.setitem(sys.modules, "school_crew.crew", stub)

    response = client.post(EVALUATE_URL, json=_body(), headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["recommendation"] == "Recommendation text"
    assert "Phone" not in captured["profile"]
    assert "Guardian" not in captured["profile"]


def test_llm_config_refuses_to_build_without_credentials(monkeypatch):
    crewai_stub = types.ModuleType("crewai")
    crewai_stub.LLM = lambda **kwargs: kwargs
    monkeypatch.setitem(sys.modules, "crewai", crewai_stub)
    monkeypatch.delitem(sys.modules, "school_crew.llm_config", raising=False)
    monkeypatch.delenv("MODAL_PROXY_TOKEN_ID", raising=False)
    monkeypatch.delenv("MODAL_PROXY_TOKEN_SECRET", raising=False)
    # Stop load_dotenv from restoring values out of a developer's local .env file.
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)

    with pytest.raises(RuntimeError, match="MODAL_PROXY_TOKEN"):
        import school_crew.llm_config  # noqa: F401


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
