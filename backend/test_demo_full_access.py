"""The isolated online demo (config.DEMO_FULL_ACCESS): the shared demo login manages the whole made-up school,
but never its own login or an administrator's, and no real email leaves. Without the switch nothing changes."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

import config
from database import engine
from main import app
from models.attendance import StudentAttendance, TeacherClassAssignment
from models.parent import ParentStudentLink
from models.student import Student
from models.user import ROLE_DEMO, ROLE_TEACHER, PasswordResetEvent, User, hash_password
from routers.auth import DEMO_PASSWORD_FIXED, DEMO_REFUSAL
from services import admissions, email_service

PASSWORD = "test-demo-1"
NEW_PASSWORD = "a-long-password-1"


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def demo(client):
    with Session(engine) as session:
        session.add(User(username="demo.full", password_hash=hash_password(PASSWORD), role=ROLE_DEMO))
        session.commit()
    token = client.post("/auth/login", json={"username": "demo.full", "password": PASSWORD}).json()["access_token"]
    yield {"Authorization": f"Bearer {token}"}
    with Session(engine) as session:
        session.delete(session.exec(select(User).where(User.username == "demo.full")).one())
        session.commit()


@pytest.fixture()
def full(monkeypatch):
    monkeypatch.setattr(config, "DEMO_FULL_ACCESS", True)


def ok(response, status=200):
    assert response.status_code == status, f"{response.request.method} {response.request.url.path}: {response.text}"
    return response


def new_student(client, headers, roll):
    return ok(client.post("/students", headers=headers, json={
        "name": "Synthetic Student", "roll_number": roll, "grade": "Grade 8", "section": "A",
        "guardian_name": "Sample Guardian", "phone": "0300-1234567",
    }), 201).json()["id"]


def account(username, **extra):
    return {"username": username, "full_name": "Synthetic Person", "password": NEW_PASSWORD, **extra}


def drop_students(*ids):
    with Session(engine) as session:
        for student_id in ids:
            student = session.get(Student, student_id)
            if student:
                session.delete(student)
        session.commit()


def test_students_can_be_created_edited_archived_restored_and_deleted(client, demo, full):
    student_id = new_student(client, demo, "FA-1")
    try:
        ok(client.put(f"/students/{student_id}", headers=demo, json={"name": "Synthetic Edited"}))
        ok(client.post(f"/students/{student_id}/archive", headers=demo))
        ok(client.post(f"/students/{student_id}/restore", headers=demo))
        ok(client.delete(f"/students/{student_id}", headers=demo))
        ok(client.get(f"/students/{student_id}", headers=demo), 404)
    finally:
        drop_students(student_id)


def test_parent_accounts_full_lifecycle(client, demo, full):
    first, second = new_student(client, demo, "FA-2"), new_student(client, demo, "FA-3")
    try:
        parent_id = ok(client.post("/parents", headers=demo, json=account(
            "fa.parent", student_ids=[first], email="fa.parent@demo.invalid")), 201).json()["id"]
        ok(client.put(f"/parents/{parent_id}/email", headers=demo,
                      json={"email": "fa.parent2@demo.invalid", "admin_password": PASSWORD}))
        ok(client.post(f"/parents/{parent_id}/children", headers=demo, json={"student_id": second}), 201)
        ok(client.delete(f"/parents/{parent_id}/children/{second}", headers=demo))
        ok(client.post(f"/parents/{parent_id}/deactivate", headers=demo))
        ok(client.post(f"/parents/{parent_id}/activate", headers=demo))
        ok(client.post(f"/parents/{parent_id}/reset-password", headers=demo, json={"new_password": "another-password-2"}))
        ok(client.delete(f"/parents/{parent_id}", headers=demo), 204)
        with Session(engine) as session:
            assert session.get(User, parent_id) is None
            for model, column in ((ParentStudentLink, ParentStudentLink.parent_id),
                                  (PasswordResetEvent, PasswordResetEvent.user_id)):
                assert session.exec(select(model).where(col(column) == parent_id)).first() is None
    finally:
        drop_students(first, second)


def test_teacher_accounts_full_lifecycle_with_class_assignment(client, demo, full):
    teacher_id = ok(client.post("/teachers", headers=demo, json=account("fa.teacher")), 201).json()["id"]
    ok(client.put(f"/teachers/{teacher_id}/email", headers=demo,
                  json={"email": "fa.teacher@demo.invalid", "admin_password": PASSWORD}))
    ok(client.post(f"/teachers/{teacher_id}/deactivate", headers=demo))
    ok(client.post(f"/teachers/{teacher_id}/activate", headers=demo))
    ok(client.post(f"/teachers/{teacher_id}/reset-password", headers=demo, json={"new_password": "another-password-2"}))
    options = ok(client.get("/teacher-assignments/options", headers=demo)).json()
    year = options.get("current_academic_year_id") or 1
    assignment = ok(client.post("/teacher-assignments", headers=demo, json={
        "teacher_id": teacher_id, "grade": "Grade 8", "section": "A", "academic_year_id": year}), 201).json()
    ok(client.delete(f"/teacher-assignments/{assignment['id']}", headers=demo), 204)
    ok(client.post("/teacher-assignments", headers=demo, json={
        "teacher_id": teacher_id, "grade": "Grade 8", "section": "A", "academic_year_id": year}), 201)
    ok(client.delete(f"/teachers/{teacher_id}", headers=demo), 204)
    with Session(engine) as session:
        assert session.get(User, teacher_id) is None
        assert session.exec(select(TeacherClassAssignment).where(
            TeacherClassAssignment.teacher_id == teacher_id)).first() is None


def test_a_teacher_with_recorded_attendance_is_kept(client, demo, full):
    from datetime import date

    student_id = new_student(client, demo, "FA-4")
    teacher_id = ok(client.post("/teachers", headers=demo, json=account("fa.marker")), 201).json()["id"]
    try:
        with Session(engine) as session:
            session.add(StudentAttendance(student_id=student_id, grade="Grade 8", section="A", academic_year_id=1,
                                          attendance_date=date(2026, 1, 5), status="present", marked_by=teacher_id))
            session.commit()
        ok(client.delete(f"/teachers/{teacher_id}", headers=demo), 409)
    finally:
        with Session(engine) as session:
            for row in session.exec(select(StudentAttendance).where(StudentAttendance.student_id == student_id)).all():
                session.delete(row)
            session.delete(session.get(User, teacher_id))
            session.commit()
        drop_students(student_id)


def test_fees_payments_receipts_and_marks(client, demo, full):
    from models.fee import Invoice, Payment
    from models.result import Result

    student_id = new_student(client, demo, "FA-5")
    try:
        ok(client.post("/fees/generate", headers=demo, json={
            "student_id": student_id, "month": "November 2026", "due_date": "2026-11-10", "amount": 3500}), 201)
        invoice_id = ok(client.get(f"/fees?student_id={student_id}", headers=demo)).json()[0]["id"]
        ok(client.post(f"/fees/{invoice_id}/pay", headers=demo, json={"amount_paid": 3500, "payment_mode": "cash"}), 201)
        payment_id = ok(client.get(f"/fees/{invoice_id}/payments", headers=demo)).json()
        payment_id = (payment_id if isinstance(payment_id, list) else payment_id["payments"])[0]["id"]
        receipt = ok(client.get(f"/fees/payments/{payment_id}/receipt", headers=demo))
        assert receipt.headers["content-type"].startswith("application/pdf")
        ok(client.post("/results", headers=demo, json={
            "student_id": student_id, "subject": "English", "marks_obtained": 70, "total_marks": 100,
            "exam_type": "Midterm"}))
        ok(client.get(f"/results/{student_id}/report-card/pdf", headers=demo))
    finally:
        with Session(engine) as session:
            for invoice in session.exec(select(Invoice).where(Invoice.student_id == student_id)).all():
                for payment in session.exec(select(Payment).where(Payment.invoice_id == invoice.id)).all():
                    session.delete(payment)
                session.delete(invoice)
            for result in session.exec(select(Result).where(Result.student_id == student_id)).all():
                session.delete(result)
            session.commit()
        drop_students(student_id)


def test_every_dashboard_module_and_the_assistant_answer(client, demo, full):
    for path in ("/dashboard/stats", "/dashboard/activity", "/ai/at-risk", "/admissions/options", "/admissions",
                 "/attendance/overview", "/result-publishing", "/teachers", "/parents", "/chatbot/status"):
        ok(client.get(path, headers=demo))
    ok(client.post("/chatbot/ask", headers=demo, json={"question": "How many students are there?", "session_id": "fa"}))
    ok(client.post("/ai/simulate", headers=demo, json={"avg_marks_pct": 55, "failing_subjects": 1}))


def test_the_demo_login_decides_admissions_only_with_the_switch(monkeypatch):
    assert not set(admissions.allowed_next("under_review", "demo")) & set(admissions.DECISION_STATUSES)
    monkeypatch.setattr(config, "DEMO_FULL_ACCESS", True)
    assert admissions.allowed_next("under_review", "demo") == admissions.allowed_next("under_review", "admin")
    assert admissions.allowed_next("under_review", "registrar") != admissions.allowed_next("under_review", "admin")


def test_the_demo_login_and_administrators_cannot_be_touched(client, demo, full):
    change = {"current_password": PASSWORD, "new_password": "another-password-1"}
    response = ok(client.post("/auth/change-password", headers=demo, json=change), 403)
    assert response.json()["detail"] == DEMO_PASSWORD_FIXED
    with Session(engine) as session:
        protected = session.exec(select(User).where(col(User.role).in_(["admin", ROLE_DEMO]))).all()
        before = {user.id: (user.role, user.password_hash, user.is_active) for user in protected}
    assert before
    for user_id in before:
        for prefix in ("/teachers", "/parents"):
            ok(client.delete(f"{prefix}/{user_id}", headers=demo), 404)
            ok(client.post(f"{prefix}/{user_id}/deactivate", headers=demo), 404)
            ok(client.post(f"{prefix}/{user_id}/reset-password", headers=demo, json={"new_password": NEW_PASSWORD}), 404)
    with Session(engine) as session:
        assert {i: (u.role, u.password_hash, u.is_active) for i in before for u in [session.get(User, i)]} == before
    # A new account cannot take over the shared login's name.
    ok(client.post("/teachers", headers=demo, json=account("DEMO.FULL")), 409)


def test_without_the_switch_nothing_is_opened(client, demo):
    refused = ok(client.post("/parents", headers=demo, json=account("nope", student_ids=[1])), 403)
    assert refused.json()["detail"] == DEMO_REFUSAL
    assert ok(client.delete("/teachers/1", headers=demo), 403).json()["detail"] == DEMO_REFUSAL
    assert ok(client.get("/school/info", headers=demo)).json()["demo_full_access"] is False


def test_without_the_switch_not_even_an_administrator_deletes_an_account(client):
    from routers.auth import create_access_token

    with Session(engine) as session:
        admin = session.exec(select(User).where(User.role == "admin")).first()
        teacher = User(username="fa.kept", password_hash=hash_password(NEW_PASSWORD), role=ROLE_TEACHER)
        session.add(teacher)
        session.commit()
        headers = {"Authorization": f"Bearer {create_access_token(admin)}"}
        teacher_id = teacher.id
    try:
        ok(client.delete(f"/teachers/{teacher_id}", headers=headers), 403)
    finally:
        with Session(engine) as session:
            session.delete(session.get(User, teacher_id))
            session.commit()


def test_a_demo_copy_never_sends_real_email(monkeypatch):
    for name, value in (("EMAIL_BACKEND", "smtp"), ("SMTP_HOST", "smtp.invalid"), ("EMAIL_FROM", "a@demo.invalid")):
        monkeypatch.setattr(config, name, value)
    monkeypatch.setattr(config, "DEMO_MODE", True)
    monkeypatch.setattr(email_service, "_send_smtp", lambda message: pytest.fail("a real email was attempted"))
    assert not email_service.email_enabled()
    assert email_service.send_email("someone@demo.invalid", "s", "b") is False
    monkeypatch.setattr(config, "DEMO_MODE", False)
    assert email_service.email_enabled()
