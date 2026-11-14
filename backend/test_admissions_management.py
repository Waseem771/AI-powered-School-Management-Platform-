"""New-student admissions: applications, workflow, entry tests, enrollment, permissions, AI fallback.

Uses the temporary seeded database from conftest.py and made-up applicants only.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from database import engine
from main import app
from models.admission import AdmissionApplication, AdmissionStatusHistory
from models.fee import AcademicYear, Invoice
from models.student import Student
from models.user import User, hash_password
from services import admission_assistant, admissions

STAFF_PASSWORD = "synthetic-staff-password-1"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def _login(client, username, password):
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(scope="module")
def admin(client):
    from conftest import TEST_ADMIN_PASSWORD

    return _login(client, "admin", TEST_ADMIN_PASSWORD)


@pytest.fixture(scope="module")
def users(client):
    with Session(engine) as session:
        for name, role in (("registrar_test", "registrar"), ("teacher_test", "teacher")):
            if not session.exec(select(User).where(User.username == name)).first():
                session.add(User(username=name, password_hash=hash_password(STAFF_PASSWORD), role=role))
        session.commit()
    return {
        "registrar": _login(client, "registrar_test", STAFF_PASSWORD),
        "teacher": _login(client, "teacher_test", STAFF_PASSWORD),
    }


_counter = {"n": 0}


def _payload(**overrides):
    _counter["n"] += 1
    body = {
        "student_name": f"Test Applicant {chr(64 + _counter['n'] % 26 + 1)}",
        "dob": "2013-05-10",
        "gender": "Female",
        "applying_grade": "Grade 7",
        "previous_class": "Grade 6",
        "previous_school": "Sample Public School",
        "guardian_name": "Sample Guardian",
        "guardian_relationship": "Father",
        "phone": "0300-1112233",
        "address": "House 1, Test Street, Khairpur",
    }
    body.update(overrides)
    return body


def _create(client, headers, **overrides):
    response = client.post("/admissions", json=_payload(**overrides), headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


def _move(client, headers, application_id, to_status, note=None):
    return client.post(f"/admissions/{application_id}/status", json={"to_status": to_status, "note": note}, headers=headers)


def _approved(client, admin, **overrides):
    application = _create(client, admin, **overrides)
    assert _move(client, admin, application["id"], "under_review").status_code == 200
    assert _move(client, admin, application["id"], "approved", "Meets the school's requirements.").status_code == 200
    return application


def _enroll_body(application, **overrides):
    body = {
        "section": "A",
        "confirm_academic_year_id": application["academic_year_id"],
        "confirm_grade": application["applying_grade"],
    }
    body.update(overrides)
    return body


# 1. Creating an application
def test_create_application_stores_everything_and_a_checklist(client, admin):
    application = _create(client, admin, staff_notes="Walk-in enquiry")

    assert application["application_number"].startswith("ADM-")
    assert application["status"] == "new"
    assert application["academic_session"]
    assert len(application["documents"]) == 5 and not any(doc["received"] for doc in application["documents"])
    assert application["history"][0]["to_status"] == "new"
    assert application["student_id"] is None


def test_documents_already_in_hand_are_recorded(client, admin):
    application = _create(client, admin, documents_received=["Guardian CNIC copy"])

    received = [doc["name"] for doc in application["documents"] if doc["received"]]
    assert received == ["Guardian CNIC copy"]


# 2. Required fields and validation
@pytest.mark.parametrize(
    "field,value",
    [
        ("student_name", ""),
        ("student_name", "Bad123"),
        ("dob", "not-a-date"),
        ("dob", "1990-01-01"),
        ("applying_grade", "Grade 2"),
        ("guardian_name", ""),
        ("phone", "123"),
        ("alt_phone", "abc"),
        ("address", "x"),
        ("gender", "Unknown"),
        ("documents_received", ["Made-up document"]),
        ("application_date", "2999-01-01"),
    ],
)
def test_invalid_input_is_refused(client, admin, field, value):
    response = client.post("/admissions", json=_payload(**{field: value}), headers=admin)

    assert response.status_code == 422


def test_missing_required_fields_are_refused(client, admin):
    response = client.post("/admissions", json={"student_name": "Only Name"}, headers=admin)

    assert response.status_code == 422
    fields = {item["loc"][-1] for item in response.json()["detail"]}
    assert {"dob", "applying_grade", "guardian_name", "phone", "address"} <= fields


def test_optional_fields_may_be_left_out(client, admin):
    body = _payload()
    for field in ("gender", "previous_class", "previous_school", "alt_phone"):
        body.pop(field, None)

    assert client.post("/admissions", json=body, headers=admin).status_code == 201


# 3. Unique application numbers
def test_application_numbers_are_unique_and_the_database_enforces_it(client, admin):
    numbers = [_create(client, admin)["application_number"] for _ in range(4)]

    assert len(set(numbers)) == 4
    with Session(engine) as session:
        first = session.exec(select(AdmissionApplication).where(AdmissionApplication.application_number == numbers[0])).one()
        duplicate = AdmissionApplication(
            application_number=numbers[0], academic_year_id=first.academic_year_id, student_name="Dup Test",
            applying_grade="Grade 7", guardian_name="Dup Guardian", phone="0300-1112233", address="Somewhere here",
        )
        session.add(duplicate)
        with pytest.raises(IntegrityError):
            session.commit()


# 4. Listing and filtering
def test_listing_filters_searches_and_paginates(client, admin):
    marker = _create(client, admin, student_name="Zebulon Findable", applying_grade="Grade 10")

    by_search = client.get("/admissions", params={"search": "Findable"}, headers=admin).json()
    by_number = client.get("/admissions", params={"search": marker["application_number"]}, headers=admin).json()
    by_grade = client.get("/admissions", params={"grade": "Grade 10", "status": "new"}, headers=admin).json()
    paged = client.get("/admissions", params={"page": 1, "page_size": 2}, headers=admin).json()

    assert [row["id"] for row in by_search["items"]] == [marker["id"]]
    assert by_number["total"] == 1
    assert marker["id"] in [row["id"] for row in by_grade["items"]]
    assert len(paged["items"]) == 2 and paged["total"] >= 3
    assert client.get("/admissions", params={"status": "bogus"}, headers=admin).status_code == 422


def test_stats_count_every_status(client, admin):
    stats = client.get("/admissions/stats", headers=admin).json()

    assert stats["total"] == sum(stats[name] for name in ("new", "under_review", "test_interview", "approved", "rejected", "enrolled"))


# 5. Status transitions
def test_valid_path_through_the_workflow_is_audited(client, admin):
    application = _create(client, admin)
    for target in ("under_review", "test_interview", "approved"):
        assert _move(client, admin, application["id"], target, "ok").status_code == 200

    detail = client.get(f"/admissions/{application['id']}", headers=admin).json()
    assert [row["to_status"] for row in detail["history"]] == ["new", "under_review", "test_interview", "approved"]
    assert detail["history"][-1]["changed_by"] == "admin"
    assert detail["decided_by"] == "admin"


@pytest.mark.parametrize("path,bad", [([], "approved"), ([], "test_interview"), (["under_review"], "under_review")])
def test_invalid_transitions_are_refused_and_nothing_changes(client, admin, path, bad):
    application = _create(client, admin)
    for target in path:
        _move(client, admin, application["id"], target)

    assert _move(client, admin, application["id"], bad, "note here").status_code == 409
    detail = client.get(f"/admissions/{application['id']}", headers=admin).json()
    assert len(detail["history"]) == 1 + len(path)


def test_enrolled_cannot_be_set_by_a_plain_status_change(client, admin):
    application = _approved(client, admin)

    assert _move(client, admin, application["id"], "enrolled").status_code == 422


# 7. Approval and rejection
def test_rejection_needs_a_reason_and_stays_in_the_history(client, admin):
    application = _create(client, admin)
    _move(client, admin, application["id"], "under_review")

    assert _move(client, admin, application["id"], "rejected").status_code == 422
    assert _move(client, admin, application["id"], "rejected", "No seats left in this class.").status_code == 200
    assert client.get(f"/admissions/{application['id']}", headers=admin).json()["decision_note"].startswith("No seats")
    assert application["id"] in [row["id"] for row in client.get("/admissions", params={"status": "rejected"}, headers=admin).json()["items"]]


def test_a_rejected_application_can_be_reopened_but_not_enrolled(client, admin):
    application = _create(client, admin)
    _move(client, admin, application["id"], "rejected", "Incomplete documents.")

    assert client.post(f"/admissions/{application['id']}/enroll", json=_enroll_body(application), headers=admin).status_code == 409
    assert _move(client, admin, application["id"], "under_review", "Documents arrived.").status_code == 200


def test_only_leadership_can_approve_or_reject(client, admin, users):
    application = _create(client, users["registrar"])

    assert _move(client, users["registrar"], application["id"], "under_review").status_code == 200
    assert _move(client, users["registrar"], application["id"], "approved", "ok").status_code == 403
    assert _move(client, users["registrar"], application["id"], "rejected", "no reason given").status_code == 403
    detail = client.get(f"/admissions/{application['id']}", headers=users["registrar"]).json()
    assert detail["status"] == "under_review"
    assert all(option["value"] not in ("approved", "rejected") for option in detail["allowed_next_statuses"])


# 6. Entry tests
def test_entry_test_percentage_is_calculated(client, admin):
    application = _create(client, admin)
    body = {"test_date": "2026-11-10", "subject": "Mathematics", "max_marks": 40, "obtained_marks": 31, "remarks": "Good", "interview_notes": "Polite"}

    response = client.post(f"/admissions/{application['id']}/assessments", json=body, headers=admin)

    assert response.status_code == 201
    assessment = response.json()["assessments"][0]
    assert assessment["percentage"] == 77.5
    assert assessment["interview_notes"] == "Polite"


@pytest.mark.parametrize(
    "changes",
    [{"obtained_marks": 41}, {"obtained_marks": -1}, {"max_marks": 0}, {"subject": ""}, {"test_date": "bad"}],
)
def test_bad_entry_test_marks_are_refused(client, admin, changes):
    application = _create(client, admin)
    body = {"test_date": "2026-11-10", "subject": "English", "max_marks": 40, "obtained_marks": 20, **changes}

    assert client.post(f"/admissions/{application['id']}/assessments", json=body, headers=admin).status_code == 422


def test_entry_tests_do_not_touch_the_results_module(client, admin):
    from models.result import Result

    with Session(engine) as session:
        before = len(session.exec(select(Result)).all())
    application = _create(client, admin)
    client.post(
        f"/admissions/{application['id']}/assessments",
        json={"test_date": "2026-11-10", "subject": "English", "max_marks": 50, "obtained_marks": 45},
        headers=admin,
    )
    with Session(engine) as session:
        assert len(session.exec(select(Result)).all()) == before


# 8. Enrollment and roll numbers
def test_enrollment_creates_the_student_and_links_it(client, admin):
    application = _approved(client, admin, student_name="Enrol Candidate")
    expected_roll = client.get("/admissions/next-roll-number", headers=admin).json()["roll_number"]

    response = client.post(f"/admissions/{application['id']}/enroll", json=_enroll_body(application, section="B"), headers=admin)

    assert response.status_code == 201, response.text
    result = response.json()
    assert result["roll_number"] == expected_roll
    student = client.get(f"/students/{result['student_id']}", headers=admin).json()
    assert (student["name"], student["grade"], student["section"], student["dob"]) == ("Enrol Candidate", "Grade 7", "B", "2013-05-10")
    detail = client.get(f"/admissions/{application['id']}", headers=admin).json()
    assert detail["status"] == "enrolled" and detail["student_id"] == result["student_id"]
    assert detail["history"][-1]["to_status"] == "enrolled"


def test_roll_numbers_never_repeat(client, admin):
    rolls = []
    for _ in range(2):
        application = _approved(client, admin)
        rolls.append(client.post(f"/admissions/{application['id']}/enroll", json=_enroll_body(application), headers=admin).json()["roll_number"])

    assert rolls[0] != rolls[1]


def test_a_chosen_roll_number_that_is_taken_is_refused(client, admin):
    application = _approved(client, admin)

    response = client.post(f"/admissions/{application['id']}/enroll", json=_enroll_body(application, roll_number="045"), headers=admin)

    assert response.status_code == 409
    assert client.get(f"/admissions/{application['id']}", headers=admin).json()["status"] == "approved"


def test_enrollment_needs_an_approved_application_and_matching_session_and_class(client, admin):
    pending = _create(client, admin)
    assert client.post(f"/admissions/{pending['id']}/enroll", json=_enroll_body(pending), headers=admin).status_code == 409

    approved = _approved(client, admin)
    assert client.post(f"/admissions/{approved['id']}/enroll", json=_enroll_body(approved, confirm_grade="Grade 9"), headers=admin).status_code == 409
    assert client.post(f"/admissions/{approved['id']}/enroll", json=_enroll_body(approved, confirm_academic_year_id=99999), headers=admin).status_code == 409


def test_existing_students_are_never_overwritten(client, admin):
    with Session(engine) as session:
        before = {student.id: (student.name, student.roll_number) for student in session.exec(select(Student)).all()}
    application = _approved(client, admin)
    client.post(f"/admissions/{application['id']}/enroll", json=_enroll_body(application), headers=admin)
    with Session(engine) as session:
        after = {student.id: (student.name, student.roll_number) for student in session.exec(select(Student)).all()}

    assert all(after[key] == value for key, value in before.items())
    assert len(after) == len(before) + 1


# 9. Duplicate enrollment
def test_the_same_applicant_cannot_be_enrolled_twice(client, admin):
    application = _approved(client, admin)
    first = client.post(f"/admissions/{application['id']}/enroll", json=_enroll_body(application), headers=admin)
    with Session(engine) as session:
        students_after_first = len(session.exec(select(Student)).all())

    second = client.post(f"/admissions/{application['id']}/enroll", json=_enroll_body(application), headers=admin)

    assert first.status_code == 201 and second.status_code == 409
    with Session(engine) as session:
        assert len(session.exec(select(Student)).all()) == students_after_first


def test_the_database_refuses_two_applications_linked_to_one_student(client, admin):
    application = _approved(client, admin)
    student_id = client.post(f"/admissions/{application['id']}/enroll", json=_enroll_body(application), headers=admin).json()["student_id"]
    other = _create(client, admin)

    with Session(engine) as session:
        row = session.get(AdmissionApplication, other["id"])
        row.student_id = student_id
        session.add(row)
        with pytest.raises(IntegrityError):
            session.commit()


# 10. Transaction rollback
def test_a_failure_part_way_through_enrollment_leaves_nothing_behind(client, admin, monkeypatch):
    application = _approved(client, admin)
    with Session(engine) as session:
        students_before = len(session.exec(select(Student)).all())
        history_before = len(session.exec(select(AdmissionStatusHistory)).all())

    def explode(*_args, **_kwargs):
        raise RuntimeError("simulated failure after the student was added")

    monkeypatch.setattr(admissions, "record_enrollment_history", explode)
    with TestClient(app, raise_server_exceptions=False) as failing_client:
        response = failing_client.post(f"/admissions/{application['id']}/enroll", json=_enroll_body(application), headers=admin)
    monkeypatch.undo()

    assert response.status_code == 500
    with Session(engine) as session:
        assert len(session.exec(select(Student)).all()) == students_before
        assert len(session.exec(select(AdmissionStatusHistory)).all()) == history_before
        row = session.get(AdmissionApplication, application["id"])
        assert row.status == "approved" and row.student_id is None
    assert client.post(f"/admissions/{application['id']}/enroll", json=_enroll_body(application), headers=admin).status_code == 201


# 7b. Fees integration
def test_fees_are_never_created_automatically_but_the_existing_module_works_after_enrollment(client, admin):
    application = _approved(client, admin)
    with Session(engine) as session:
        invoices_before = len(session.exec(select(Invoice)).all())
    student_id = client.post(f"/admissions/{application['id']}/enroll", json=_enroll_body(application), headers=admin).json()["student_id"]
    with Session(engine) as session:
        assert len(session.exec(select(Invoice)).all()) == invoices_before

    policy = client.get(f"/admissions/{application['id']}/fee-policy", headers=admin).json()
    assert policy["student_id"] == student_id and policy["configured"] and policy["monthly_fee"] > 0
    challan = client.post(
        "/fees/generate",
        json={"student_id": student_id, "amount": policy["monthly_fee"], "month": "December 2026", "due_date": "2026-12-10"},
        headers=admin,
    )
    assert challan.status_code == 201
    assert client.get(f"/fees/student/{student_id}/summary", headers=admin).status_code == 200


def test_an_enrolled_student_with_an_application_cannot_be_deleted(client, admin):
    application = _approved(client, admin)
    student_id = client.post(f"/admissions/{application['id']}/enroll", json=_enroll_body(application), headers=admin).json()["student_id"]

    assert client.delete(f"/students/{student_id}", headers=admin).status_code == 409


# 11. Authentication and permissions
@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/admissions"), ("post", "/admissions"), ("get", "/admissions/stats"), ("get", "/admissions/options"),
        ("get", "/admissions/1"), ("put", "/admissions/1"), ("post", "/admissions/1/status"),
        ("post", "/admissions/1/enroll"), ("post", "/admissions/1/assessments"), ("put", "/admissions/1/documents"),
        ("get", "/admissions/1/fee-policy"), ("post", "/admissions/assistant/policy"),
        ("post", "/admissions/1/assistant/reminder"), ("get", "/admissions/1/assistant/summary"),
    ],
)
def test_anonymous_requests_are_refused(client, method, path):
    assert getattr(client, method)(path).status_code == 401


def test_staff_without_an_admissions_role_are_refused(client, users):
    assert client.get("/admissions", headers=users["teacher"]).status_code == 403
    assert client.post("/admissions", json=_payload(), headers=users["teacher"]).status_code == 403


def test_nothing_about_applicants_is_on_a_public_route(client):
    assert client.get("/school/public").json().keys() == {"name", "demo_mode"}


def test_an_unknown_application_is_a_404(client, admin):
    assert client.get("/admissions/999999", headers=admin).status_code == 404


def test_editing_an_application_keeps_required_fields(client, admin):
    application = _create(client, admin)

    ok = client.put(f"/admissions/{application['id']}", json={"address": "New address, Khairpur", "alt_phone": "0301-9998877"}, headers=admin)
    cleared = client.put(f"/admissions/{application['id']}", json={"guardian_name": None}, headers=admin)

    assert ok.status_code == 200 and ok.json()["alt_phone"] == "0301-9998877"
    assert cleared.status_code == 422


# 12. AI assistant, and its fallback
def test_missing_documents_reminder_and_summary_are_drafts_for_staff(client, admin):
    application = _create(client, admin, documents_received=["Guardian CNIC copy"])
    base = f"/admissions/{application['id']}/assistant"

    missing = client.get(f"{base}/missing-documents", headers=admin).json()["missing_documents"]
    english = client.post(f"{base}/reminder", json={"language": "en"}, headers=admin).json()
    urdu = client.post(f"{base}/reminder", json={"language": "ur"}, headers=admin).json()
    summary = client.get(f"{base}/summary", headers=admin).json()

    assert "Guardian CNIC copy" not in missing and len(missing) == 4
    assert english["review_required"] and "Birth certificate" in english["draft"]
    assert "برتھ سرٹیفکیٹ" in urdu["draft"]
    assert application["application_number"] in summary["summary"] and summary["review_required"]
    assert "approve" not in summary["summary"].lower().replace("approved", "")


def test_no_reminder_is_drafted_when_nothing_is_missing(client, admin):
    application = _create(client, admin, documents_received=[
        "Birth certificate or B-Form", "Guardian CNIC copy", "Previous school leaving certificate",
        "Previous result card", "Passport-size photographs",
    ])

    result = client.post(f"/admissions/{application['id']}/assistant/reminder", json={"language": "en"}, headers=admin).json()

    assert result["draft"] is None


def test_the_ai_helper_never_changes_the_application(client, admin):
    application = _create(client, admin)
    client.get(f"/admissions/{application['id']}/assistant/summary", headers=admin)
    client.post(f"/admissions/{application['id']}/assistant/reminder", json={"language": "en"}, headers=admin)

    assert client.get(f"/admissions/{application['id']}", headers=admin).json()["status"] == "new"


def test_policy_question_falls_back_cleanly_when_the_assistant_is_down(client, admin, monkeypatch):
    class BrokenSearch:
        def answer_query(self, _question):
            raise RuntimeError("secret-internal-detail")

    result = admission_assistant.explain_policy("What is the admission policy?", BrokenSearch())

    assert result["available"] is False and result["answer"] is None
    assert "secret-internal-detail" not in str(result)

    monkeypatch.setattr("services.rag_service.rag_service", BrokenSearch())
    response = client.post("/admissions/assistant/policy", json={"question": "What is the admission policy?"}, headers=admin)
    assert response.status_code == 200 and response.json()["available"] is False
    # Ordinary admissions work carries on.
    assert client.get("/admissions/stats", headers=admin).status_code == 200


def test_an_ungrounded_policy_answer_is_not_presented_as_policy():
    class Unsure:
        def answer_query(self, _question):
            return {"answer": "I cannot answer that", "sources": [], "grounded": False}

    result = admission_assistant.explain_policy("What is the moon made of?", Unsure())

    assert result["answer"] is None and result["sources"] == []


def test_applicant_details_are_not_sent_to_the_policy_search(client, admin, monkeypatch):
    seen = []

    class Recorder:
        def answer_query(self, question):
            seen.append(question)
            return {"answer": "Policy text", "sources": ["admissions_policy.txt"], "grounded": True}

    monkeypatch.setattr("services.rag_service.rag_service", Recorder())
    client.post("/admissions/assistant/policy", json={"question": "Which documents are needed?"}, headers=admin)

    assert seen == ["Which documents are needed?"]


# 13. Regression checks for existing modules
def test_existing_modules_still_work_with_admissions_installed(client, admin):
    assert client.get("/students", headers=admin).status_code == 200
    assert client.get("/fees", headers=admin).status_code == 200
    assert client.get("/fees/summary", headers=admin).status_code == 200
    assert client.get("/results/class", params={"grade": "Grade 8", "section": "B", "subject": "English", "exam_type": "Final Term"}, headers=admin).status_code in (200, 422)
    assert client.get("/dashboard/stats", headers=admin).status_code == 200
    assert client.get("/school/info", headers=admin).status_code == 200


def test_the_old_admissions_route_is_still_protected_and_registered(client):
    assert client.post("/api/admissions-crew/evaluate", json={"student_roll_number": "045", "desired_program": "Grade 9"}).status_code == 401


def test_a_student_can_still_be_added_by_hand(client, admin):
    with Session(engine) as session:
        roll = admissions.next_roll_number(session)
    response = client.post(
        "/students",
        json={"name": "Manual Student", "roll_number": roll, "grade": "Grade 6", "section": "A", "guardian_name": "Some Guardian", "phone": "0300-1234567"},
        headers=admin,
    )

    assert response.status_code == 201


# 14. The school's date, not the server's
def test_the_application_date_follows_the_school_clock_not_the_servers(client, admin, monkeypatch):
    """The browser sends Pakistan's date. A server in UTC is a day behind for the first hours of the school's day."""
    import services.fee_ledger as ledger
    from datetime import date

    school_day = date(2031, 1, 1)  # far from the real date, so the server's own date can never match it
    monkeypatch.setattr(ledger, "school_today", lambda: school_day)
    monkeypatch.setattr(admissions, "school_today", lambda: school_day)

    on_the_school_day = client.post("/admissions", json=_payload(application_date="2031-01-01"), headers=admin)
    assert on_the_school_day.status_code == 201, on_the_school_day.text
    assert on_the_school_day.json()["application_number"].startswith("ADM-2031-")

    defaulted = client.post("/admissions", json=_payload(), headers=admin)
    assert defaulted.status_code == 201
    assert defaulted.json()["application_date"] == "2031-01-01"

    after_the_school_day = client.post("/admissions", json=_payload(application_date="2031-01-02"), headers=admin)
    assert after_the_school_day.status_code == 422


# 15. Roll-number suggestion follows the school's 3-digit style
@pytest.fixture
def add_students():
    """Adds made-up students, and removes them afterwards so other test files see the same school."""
    added = []

    def add(rolls):
        with Session(engine) as session:
            for roll in rolls:
                student = Student(name=f"Roll Test {roll}", roll_number=roll, grade="Grade 6", section="A", guardian_name="Sample Guardian", phone="0300-1112233")
                session.add(student)
                session.flush()
                added.append(student.id)
            session.commit()

    yield add
    with Session(engine) as session:
        for student_id in added:
            student = session.get(Student, student_id)
            if student:
                session.delete(student)
        session.commit()


def test_a_long_test_roll_number_does_not_move_the_suggestion(client, admin, add_students):
    with Session(engine) as session:
        before = admissions.next_roll_number(session)
    add_students(["111111", "5555"])
    with Session(engine) as session:
        suggested = admissions.next_roll_number(session)

    assert suggested == before and len(suggested) == 3
    assert client.get("/admissions/next-roll-number", headers=admin).json()["roll_number"] == suggested


def test_the_suggestion_is_padded_unused_and_follows_the_highest_three_digit_number(add_students):
    add_students(["840"])
    with Session(engine) as session:
        assert admissions.next_roll_number(session) == "841"
    add_students(["841", "842"])
    with Session(engine) as session:
        assert admissions.next_roll_number(session) == "843"


def test_when_the_top_of_the_range_is_used_a_free_gap_is_suggested(add_students):
    add_students(["999"])
    with Session(engine) as session:
        suggested = admissions.next_roll_number(session)
        taken = set(session.exec(select(Student.roll_number)).all())

    assert suggested not in taken and len(suggested) == 3


def test_enrolling_with_a_taken_roll_number_never_touches_the_existing_student(client, admin, add_students):
    add_students(["111111"])
    application = _approved(client, admin)
    response = client.post(f"/admissions/{application['id']}/enroll", json=_enroll_body(application, roll_number="111111"), headers=admin)

    assert response.status_code == 409
    with Session(engine) as session:
        assert len(session.exec(select(Student).where(Student.roll_number == "111111")).all()) == 1
