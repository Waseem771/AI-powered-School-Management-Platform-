"""Student records: validation at the API, and archiving that never loses history."""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlmodel import Session, select

from database import create_db_and_tables, engine, schema_problems
from main import app
from models.fee import Invoice, Payment
from models.result import Result
from models.student import Student
from services.data_assistant_service import SchoolDataAssistant


SEEDED_STUDENT_COUNT = 50


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def headers(client, admin_password):
    response = client.post("/auth/login", json={"username": "admin", "password": admin_password})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _payload(**changes):
    return {
        "name": "Sana Mirza",
        "roll_number": f"T{uuid.uuid4().hex[:8]}",
        "grade": "Grade 7",
        "section": "A",
        "guardian_name": "Imran Mirza",
        "phone": "0301-2345678",
        "dob": "2013-03-14",
        **changes,
    }


def _create(client, headers, **changes):
    response = client.post("/students", headers=headers, json=_payload(**changes))
    assert response.status_code == 201, response.text
    return response.json()


def test_create_returns_201_and_trims_text(client, headers):
    response = client.post(
        "/students", headers=headers, json=_payload(name="  Sana   Mirza ", guardian_name=" Imran Mirza ")
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Sana Mirza"
    assert response.json()["guardian_name"] == "Imran Mirza"
    assert response.json()["archived_at"] is None


@pytest.mark.parametrize(
    "changes",
    [
        {"name": ""},
        {"name": "   "},
        {"name": "A"},
        {"name": "<script>alert(1)</script>"},
        {"name": "Sana123"},
        {"guardian_name": ""},
        {"roll_number": "   "},
        {"roll_number": "12 34"},
        {"roll_number": "x" * 21},
        {"grade": "Grade 99"},
        {"section": "Z"},
        {"phone": ""},
        {"phone": "not-a-phone"},
        {"phone": "12345"},
        {"phone": "0" * 16},
        {"dob": "banana"},
        {"dob": "2099-01-01"},
        {"dob": "1900-01-01"},
        {"dob": "2025-13-45"},
    ],
)
def test_create_rejects_invalid_values(client, headers, changes):
    response = client.post("/students", headers=headers, json=_payload(**changes))

    assert response.status_code == 422, response.text


@pytest.mark.parametrize(
    "changes",
    [
        {"name": "محمد علی"},
        {"name": "Muhammad O'Brien-Khan Jr."},
        {"phone": "+92 300 1234567"},
        {"phone": "051-2854321"},
        {"dob": None},
        {"dob": ""},
    ],
)
def test_create_accepts_real_world_values(client, headers, changes):
    response = client.post("/students", headers=headers, json=_payload(**changes))

    assert response.status_code == 201, response.text


def test_blank_date_of_birth_is_stored_as_unknown(client, headers):
    assert _create(client, headers, dob="")["dob"] is None


def test_duplicate_roll_on_create_is_a_conflict(client, headers):
    student = _create(client, headers)

    response = client.post("/students", headers=headers, json=_payload(roll_number=student["roll_number"]))

    assert response.status_code == 409
    assert student["roll_number"] in response.json()["detail"]


def test_duplicate_roll_on_update_is_a_conflict_not_a_crash(client, headers):
    first, second = _create(client, headers), _create(client, headers)

    response = client.put(
        f"/students/{second['id']}", headers=headers, json={"roll_number": first["roll_number"]}
    )

    assert response.status_code == 409


def test_update_can_keep_its_own_roll_number(client, headers):
    student = _create(client, headers)

    response = client.put(
        f"/students/{student['id']}", headers=headers, json={"roll_number": student["roll_number"], "section": "B"}
    )

    assert response.status_code == 200
    assert response.json()["section"] == "B"


@pytest.mark.parametrize(
    "changes",
    [
        {"name": None},
        {"roll_number": None},
        {"grade": None},
        {"section": None},
        {"guardian_name": None},
        {"phone": None},
        {"name": ""},
        {"grade": "Grade 99"},
        {"dob": "banana"},
    ],
)
def test_update_rejects_invalid_values(client, headers, changes):
    student = _create(client, headers)

    response = client.put(f"/students/{student['id']}", headers=headers, json=changes)

    assert response.status_code == 422, response.text


def test_update_can_clear_date_of_birth(client, headers):
    student = _create(client, headers)

    response = client.put(f"/students/{student['id']}", headers=headers, json={"dob": None})

    assert response.status_code == 200
    assert response.json()["dob"] is None


def test_every_seeded_student_passes_the_new_rules(client, headers):
    """Editing an existing record must not fail because of an untouched field."""
    with Session(engine) as session:
        # Other test files add awkward old-style records on purpose, so only the seeded ones count.
        students = session.exec(select(Student).where(Student.id <= SEEDED_STUDENT_COUNT)).all()

    for student in students:
        response = client.put(
            f"/students/{student.id}",
            headers=headers,
            json={
                "name": student.name,
                "roll_number": student.roll_number,
                "grade": student.grade,
                "section": student.section,
                "guardian_name": student.guardian_name,
                "phone": student.phone,
                "dob": student.dob,
            },
        )
        assert response.status_code == 200, f"{student.roll_number}: {response.text}"


def _add_history(student_id):
    with Session(engine) as session:
        invoice = Invoice(
            student_id=student_id,
            amount=4000,
            month="January 2026",
            due_date="10-Jan-2026",
            challan_number=f"CHN-T{uuid.uuid4().hex[:8]}",
            status="partial",
        )
        session.add(invoice)
        session.commit()
        session.add(Payment(invoice_id=invoice.id, amount_paid=1000, payment_mode="cash"))
        session.add(Result(student_id=student_id, subject="English", marks_obtained=70))
        session.commit()
        return invoice.id


def _history_counts(student_id, invoice_id):
    with Session(engine) as session:
        return (
            len(session.exec(select(Invoice).where(Invoice.student_id == student_id)).all()),
            len(session.exec(select(Payment).where(Payment.invoice_id == invoice_id)).all()),
            len(session.exec(select(Result).where(Result.student_id == student_id)).all()),
        )


def test_archive_keeps_all_history_and_hides_the_student(client, headers):
    student = _create(client, headers)
    invoice_id = _add_history(student["id"])

    response = client.post(f"/students/{student['id']}/archive", headers=headers)

    assert response.status_code == 200
    assert response.json()["archived_at"] is not None
    assert _history_counts(student["id"], invoice_id) == (1, 1, 1)
    active = client.get("/students", headers=headers, params={"search": student["roll_number"]}).json()
    assert active == []
    archived = client.get(
        "/students", headers=headers, params={"search": student["roll_number"], "status": "archived"}
    ).json()
    assert [row["id"] for row in archived] == [student["id"]]
    every = client.get("/students", headers=headers, params={"search": student["roll_number"], "status": "all"}).json()
    assert len(every) == 1


def test_list_rejects_an_unknown_status(client, headers):
    assert client.get("/students", headers=headers, params={"status": "banana"}).status_code == 422


def test_archive_twice_and_restore_active_are_conflicts(client, headers):
    student = _create(client, headers)

    assert client.post(f"/students/{student['id']}/restore", headers=headers).status_code == 409
    assert client.post(f"/students/{student['id']}/archive", headers=headers).status_code == 200
    assert client.post(f"/students/{student['id']}/archive", headers=headers).status_code == 409


def test_restore_brings_the_student_and_history_back(client, headers):
    student = _create(client, headers)
    invoice_id = _add_history(student["id"])
    client.post(f"/students/{student['id']}/archive", headers=headers)

    response = client.post(f"/students/{student['id']}/restore", headers=headers)

    assert response.status_code == 200
    assert response.json()["archived_at"] is None
    assert _history_counts(student["id"], invoice_id) == (1, 1, 1)
    active = client.get("/students", headers=headers, params={"search": student["roll_number"]}).json()
    assert len(active) == 1


def test_archived_roll_number_stays_reserved(client, headers):
    student = _create(client, headers)
    client.post(f"/students/{student['id']}/archive", headers=headers)

    response = client.post("/students", headers=headers, json=_payload(roll_number=student["roll_number"]))

    assert response.status_code == 409
    assert "archived" in response.json()["detail"]


def test_archive_and_restore_unknown_student_are_404(client, headers):
    assert client.post("/students/999999/archive", headers=headers).status_code == 404
    assert client.post("/students/999999/restore", headers=headers).status_code == 404


def test_delete_refuses_a_student_with_any_history(client, headers):
    student = _create(client, headers)
    invoice_id = _add_history(student["id"])

    response = client.delete(f"/students/{student['id']}", headers=headers)

    assert response.status_code == 409
    assert "archive" in response.json()["detail"].lower()
    assert _history_counts(student["id"], invoice_id) == (1, 1, 1)
    assert client.get(f"/students/{student['id']}", headers=headers).status_code == 200


def test_delete_refuses_a_student_with_only_exam_marks(client, headers):
    student = _create(client, headers)
    with Session(engine) as session:
        session.add(Result(student_id=student["id"], subject="English", marks_obtained=70))
        session.commit()

    assert client.delete(f"/students/{student['id']}", headers=headers).status_code == 409


def test_delete_removes_a_mistaken_entry_with_no_history(client, headers):
    student = _create(client, headers)

    assert client.delete(f"/students/{student['id']}", headers=headers).status_code == 200
    assert client.get(f"/students/{student['id']}", headers=headers).status_code == 404


def test_archived_student_cannot_get_new_challans_but_can_still_pay(client, headers):
    student = _create(client, headers)
    invoice_id = _add_history(student["id"])
    client.post(f"/students/{student['id']}/archive", headers=headers)

    challan = client.post(
        "/fees/generate",
        headers=headers,
        json={"student_id": student["id"], "amount": 4000, "month": "March 2026", "due_date": "2026-03-10"},
    )
    payment = client.post(f"/fees/{invoice_id}/pay", headers=headers, json={"amount_paid": 500, "payment_mode": "cash"})

    assert challan.status_code == 409
    assert "archived" in challan.json()["detail"]
    assert payment.status_code == 201


def test_archived_invoice_stays_visible_and_flagged_on_the_fees_list(client, headers):
    student = _create(client, headers)
    _add_history(student["id"])
    client.post(f"/students/{student['id']}/archive", headers=headers)

    rows = client.get("/fees", headers=headers, params={"student_id": student["id"]}).json()

    assert len(rows) == 1
    assert rows[0]["student_archived"] is True


def test_archived_student_leaves_counts_but_not_money(client, headers):
    student = _create(client, headers, grade="Grade 9")
    _add_history(student["id"])
    before = client.get("/dashboard/stats", headers=headers).json()
    summary_before = client.get("/fees/summary", headers=headers).json()
    at_risk_before = client.get("/ai/at-risk", headers=headers).json()
    assert student["id"] in [row["id"] for row in at_risk_before]

    client.post(f"/students/{student['id']}/archive", headers=headers)

    after = client.get("/dashboard/stats", headers=headers).json()
    assert after["kpis"]["total_students"] == before["kpis"]["total_students"] - 1
    grade_nine = lambda stats: next(row["count"] for row in stats["grade_distribution"] if row["grade"] == "Grade 9")
    assert grade_nine(after) == grade_nine(before) - 1
    assert client.get("/fees/summary", headers=headers).json() == summary_before
    assert after["kpis"]["total_collected"] == before["kpis"]["total_collected"]
    assert student["id"] not in [row["id"] for row in client.get("/ai/at-risk", headers=headers).json()]


def test_chatbot_roster_skips_archived_students_but_lookup_finds_them(client, headers):
    student = _create(client, headers, grade="Grade 10", name="Zubaida Archivetest")
    _add_history(student["id"])
    client.post(f"/students/{student['id']}/archive", headers=headers)

    with Session(engine) as session:
        assistant = SchoolDataAssistant(session)
        roster = assistant.get_students_by_grade("Grade 10")
        found = assistant.find_students("Archivetest")
        pending = assistant.get_students_with_pending_fees()

    assert student["id"] not in [row["id"] for row in roster["students"]]
    assert [row["archived"] for row in found] == [True]
    # They still owe the money, so the dues list keeps them, clearly marked.
    assert next(row for row in pending["students"] if row["id"] == student["id"])["archived"] is True


def test_schema_check_names_a_missing_column(tmp_path, monkeypatch):
    from sqlmodel import create_engine

    old = create_engine(f"sqlite:///{(tmp_path / 'old.db').as_posix()}")
    with old.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE students (id INTEGER PRIMARY KEY, name VARCHAR)")

    problems = schema_problems(old)

    assert "students.archived_at" in problems


def test_schema_check_passes_on_the_current_database():
    create_db_and_tables()
    assert schema_problems(engine) == []


def test_startup_refuses_an_old_database_with_clear_instructions(tmp_path, monkeypatch):
    import database
    from sqlmodel import create_engine

    old = create_engine(f"sqlite:///{(tmp_path / 'old.db').as_posix()}")
    with old.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE students (id INTEGER PRIMARY KEY, name VARCHAR)")
    monkeypatch.setattr(database, "engine", old)

    with pytest.raises(RuntimeError, match="migrate_db.py"):
        database.create_db_and_tables()

    # Refused means untouched: not even the missing new tables were added.
    assert inspect(old).get_table_names() == ["students"]


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-q"]))
