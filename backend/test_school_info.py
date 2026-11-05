from fastapi.testclient import TestClient
from sqlmodel import Session, select

from config import SCHOOL_NAME
from conftest import TEST_ADMIN_PASSWORD
from database import engine
from main import app
from models.fee import AcademicYear

client = TestClient(app)


def _headers():
    token = client.post("/auth/login", json={"username": "admin", "password": TEST_ADMIN_PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_school_info_needs_a_login():
    assert client.get("/school/info").status_code == 401


def test_school_info_gives_the_configured_name_and_current_session():
    with Session(engine) as session:
        current = session.exec(select(AcademicYear).where(AcademicYear.is_current == True)).first()  # noqa: E712

    info = client.get("/school/info", headers=_headers()).json()

    assert info["name"] == SCHOOL_NAME
    assert info["academic_session"] == (current.label if current else None)


def test_school_info_invents_no_session_when_none_is_current(monkeypatch):
    with Session(engine) as session:
        years = session.exec(select(AcademicYear)).all()
        was_current = {year.id: year.is_current for year in years}
        for year in years:
            year.is_current = False
            session.add(year)
        session.commit()
    try:
        assert client.get("/school/info", headers=_headers()).json()["academic_session"] is None
    finally:
        with Session(engine) as session:
            for year in session.exec(select(AcademicYear)).all():
                year.is_current = was_current[year.id]
                session.add(year)
            session.commit()


if __name__ == "__main__":
    import sys

    import pytest

    sys.exit(pytest.main([__file__, "-q"]))
