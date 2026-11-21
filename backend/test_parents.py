"""Parent Portal: account management, strict access to linked children only, and read-only data.

Uses the seeded test database. Every test removes what it added, so tests stay independent.
"""
import sys
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from database import engine
from main import app
from models.attendance import AttendanceChangeHistory, StudentAttendance
from models.fee import Invoice, Payment
from models.parent import ParentStudentLink, PublishedExam
from models.result import Result
from models.student import Student
from models.user import User, hash_password
from services.fee_ledger import school_today

PARENT_PASSWORD = "parent-test-password-1"
OTHER_PASSWORD = "other-parent-password-1"
AHMED, BILAL = "045", "012"  # seeded students, see CLAUDE.md


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


def _student_id(roll):
    with Session(engine) as session:
        return session.exec(select(Student).where(Student.roll_number == roll)).one().id


@pytest.fixture()
def ahmed():
    return _student_id(AHMED)


@pytest.fixture()
def bilal():
    return _student_id(BILAL)


@pytest.fixture(autouse=True)
def clean_up():
    """Removes every parent, link, publication and attendance row a test created."""
    yield
    with Session(engine) as session:
        for model in (ParentStudentLink, PublishedExam, AttendanceChangeHistory, StudentAttendance):
            for row in session.exec(select(model)).all():
                session.delete(row)
        for user in session.exec(select(User).where(User.role.in_(["parent", "teacher", "registrar"]))).all():
            session.delete(user)
        # Marks and payments a test added are removed below by the tests' own markers.
        for result in session.exec(select(Result).where(Result.exam_type == "Midterm")).all():
            session.delete(result)
        for payment in session.exec(select(Payment).where(Payment.payment_mode == "test-added")).all():
            session.delete(payment)
        for invoice in session.exec(select(Invoice).where(Invoice.challan_number.like("CHN-TEST%"))).all():
            session.delete(invoice)
        session.commit()


def _create_parent(client, admin_token, student_ids, **overrides):
    payload = {
        "username": "mr.khan",
        "full_name": "Imran Khan",
        "email": "imran.khan@example.test",
        "password": PARENT_PASSWORD,
        "student_ids": student_ids,
        "relationship": "Father",
        **overrides,
    }
    return client.post("/parents", headers=_bearer(admin_token), json=payload)


@pytest.fixture()
def parent(client, admin_token, ahmed):
    """A parent of Ahmed only."""
    response = _create_parent(client, admin_token, [ahmed])
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture()
def token(client, parent):
    return _login(client, parent["username"], PARENT_PASSWORD).json()["access_token"]


def _mark_attendance(student_id, days_ago, status):
    with Session(engine) as session:
        student = session.get(Student, student_id)
        admin = session.exec(select(User).where(User.username == "admin")).one()
        session.add(StudentAttendance(
            student_id=student_id, grade=student.grade, section=student.section, academic_year_id=1,
            attendance_date=school_today() - timedelta(days=days_ago), status=status, marked_by=admin.id))
        session.commit()


def _publish(client, admin_token, exam_type="Final Term", year=1, published=True):
    return client.put("/result-publishing", headers=_bearer(admin_token),
                      json={"academic_year_id": year, "exam_type": exam_type, "published": published})


# ── Administrator manages parent accounts ───────────────────────────────────

def test_admin_creates_a_parent_linked_to_children(client, admin_token, ahmed, bilal):
    response = _create_parent(client, admin_token, [ahmed, bilal])

    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "parent" and body["is_active"] is True
    assert {child["roll_number"] for child in body["children"]} == {AHMED, BILAL}
    assert all(child["relationship"] == "Father" for child in body["children"])


def test_responses_never_contain_a_password_or_hash(client, admin_token, parent):
    listing = client.get("/parents", headers=_bearer(admin_token))

    assert listing.status_code == 200
    for body in (str(parent), listing.text):
        assert "password_hash" not in body.lower() and "new_password" not in body.lower()
        assert "$2" not in body


def test_the_stored_password_is_hashed(parent):
    with Session(engine) as session:
        stored = session.exec(select(User).where(User.username == parent["username"])).one()

    assert stored.password_hash.startswith("$2")
    assert PARENT_PASSWORD not in stored.password_hash


def test_duplicate_username_and_email_are_rejected(client, admin_token, parent, bilal):
    assert _create_parent(client, admin_token, [bilal]).status_code == 409
    assert _create_parent(client, admin_token, [bilal], username="MR.KHAN", email="x@example.test").status_code == 409
    assert _create_parent(client, admin_token, [bilal], username="ADMIN", email="y@example.test").status_code == 409
    assert _create_parent(client, admin_token, [bilal], username="someone.else").status_code == 409  # same email


@pytest.mark.parametrize(
    "overrides",
    [
        {"username": "ab"}, {"username": "has space"}, {"full_name": " "}, {"email": "not-an-email"},
        {"password": "short"}, {"password": "password123"}, {"password": "x" * 73},
        {"student_ids": []}, {"relationship": "Uncle"},
    ],
    ids=["short-name", "space", "blank-full-name", "bad-email", "short-pw", "common-pw", "long-pw", "no-children", "bad-relationship"],
)
def test_invalid_parent_input_is_rejected(client, admin_token, ahmed, overrides):
    assert _create_parent(client, admin_token, overrides.pop("student_ids", [ahmed]), **overrides).status_code == 422


def test_an_unknown_child_is_refused_and_no_account_is_left_behind(client, admin_token, ahmed):
    assert _create_parent(client, admin_token, [ahmed, 999999]).status_code == 404
    assert _create_parent(client, admin_token, [ahmed, ahmed]).status_code == 422
    with Session(engine) as session:
        assert session.exec(select(User).where(User.role == "parent")).all() == []
        assert session.exec(select(ParentStudentLink)).all() == []


def test_an_archived_student_cannot_be_linked(client, admin_token, ahmed):
    client.post(f"/students/{ahmed}/archive", headers=_bearer(admin_token))
    try:
        assert _create_parent(client, admin_token, [ahmed]).status_code == 409
    finally:
        client.post(f"/students/{ahmed}/restore", headers=_bearer(admin_token))


def test_admin_can_deactivate_and_reactivate_and_it_ends_the_session(client, admin_token, parent, token):
    url = f"/parents/{parent['id']}"
    assert client.get("/parent/children", headers=_bearer(token)).status_code == 200

    off = client.post(f"{url}/deactivate", headers=_bearer(admin_token))
    assert off.status_code == 200 and off.json()["is_active"] is False
    assert client.post(f"{url}/deactivate", headers=_bearer(admin_token)).status_code == 200  # repeatable
    assert client.get("/parent/children", headers=_bearer(token)).status_code == 401
    refused = _login(client, parent["username"], PARENT_PASSWORD)
    assert refused.status_code == 403 and "deactivated" in refused.json()["detail"]
    assert "access_token" not in refused.text

    on = client.post(f"{url}/activate", headers=_bearer(admin_token))
    assert on.status_code == 200 and on.json()["is_active"] is True
    assert client.get("/parent/children", headers=_bearer(token)).status_code == 200


def test_the_parent_endpoints_cannot_touch_other_kinds_of_account(client, admin_token):
    with Session(engine) as session:
        admin_id = session.exec(select(User).where(User.username == "admin")).one().id
    assert client.post(f"/parents/{admin_id}/deactivate", headers=_bearer(admin_token)).status_code == 404
    assert client.post("/parents/999999/activate", headers=_bearer(admin_token)).status_code == 404
    assert client.post(f"/parents/{admin_id}/children", headers=_bearer(admin_token), json={"student_id": 1}).status_code == 404
    with Session(engine) as session:
        assert session.exec(select(User).where(User.username == "admin")).one().is_active is True


def test_admin_links_and_unlinks_children(client, admin_token, parent, bilal, ahmed):
    base = f"/parents/{parent['id']}/children"

    linked = client.post(base, headers=_bearer(admin_token), json={"student_id": bilal, "relationship": "Guardian"})
    assert linked.status_code == 201
    assert {child["roll_number"] for child in linked.json()["children"]} == {AHMED, BILAL}
    assert client.post(base, headers=_bearer(admin_token), json={"student_id": bilal}).status_code == 409
    assert client.post(base, headers=_bearer(admin_token), json={"student_id": 999999}).status_code == 404

    unlinked = client.delete(f"{base}/{bilal}", headers=_bearer(admin_token))
    assert unlinked.status_code == 200
    assert [child["roll_number"] for child in unlinked.json()["children"]] == [AHMED]
    assert client.delete(f"{base}/{bilal}", headers=_bearer(admin_token)).status_code == 404
    assert client.delete(f"{base}/{ahmed}", headers=_bearer(admin_token)).json()["children"] == []


def test_a_parent_account_has_a_limit_on_children(client, admin_token, parent):
    with Session(engine) as session:
        others = [s.id for s in session.exec(select(Student).where(Student.roll_number != AHMED).limit(12)).all()]
    codes = [client.post(f"/parents/{parent['id']}/children", headers=_bearer(admin_token), json={"student_id": sid}).status_code
             for sid in others]

    assert codes.count(201) == 9 and codes[-1] == 422


def test_two_parents_may_share_a_child(client, admin_token, parent, ahmed):
    second = _create_parent(client, admin_token, [ahmed], username="mrs.khan", email="mrs@example.test", relationship="Mother")
    assert second.status_code == 201


def test_a_linked_student_cannot_be_deleted(client, admin_token, parent, ahmed):
    response = client.delete(f"/students/{ahmed}", headers=_bearer(admin_token))

    assert response.status_code == 409


def test_admin_only_endpoints_refuse_everyone_else(client, parent, token):
    with Session(engine) as session:
        session.add(User(username="reg.legacy", password_hash=hash_password(PARENT_PASSWORD), role="registrar"))
        session.commit()
    registrar = _login(client, "reg.legacy", PARENT_PASSWORD).json()["access_token"]
    for who in (token, registrar):
        assert client.get("/parents", headers=_bearer(who)).status_code == 403
        assert client.post("/parents", headers=_bearer(who), json={}).status_code == 403
        assert client.post(f"/parents/{parent['id']}/deactivate", headers=_bearer(who)).status_code == 403
        assert client.get("/result-publishing", headers=_bearer(who)).status_code == 403
        assert client.put("/result-publishing", headers=_bearer(who), json={}).status_code == 403


# ── Signing in ──────────────────────────────────────────────────────────────

def test_parent_logs_in_and_out(client, parent):
    response = _login(client, parent["username"], PARENT_PASSWORD)

    assert response.status_code == 200 and response.json()["role"] == "parent"
    token = response.json()["access_token"]
    assert client.get("/auth/me", headers=_bearer(token)).status_code == 200
    assert client.post("/auth/logout", headers=_bearer(token)).status_code == 204
    assert client.get("/parent/children", headers=_bearer(token)).status_code == 401
    assert _login(client, parent["username"], "wrong-password").status_code == 401


def test_a_parent_may_change_their_own_password(client, parent, token):
    response = client.post("/auth/change-password", headers=_bearer(token),
                           json={"current_password": PARENT_PASSWORD, "new_password": "changed-password-12"})

    assert response.status_code == 200 and response.json()["role"] == "parent"
    assert client.get("/parent/children", headers=_bearer(token)).status_code == 401  # older sessions end
    assert _login(client, parent["username"], "changed-password-12").status_code == 200
    assert client.post("/auth/change-password", headers=_bearer(response.json()["access_token"]),
                       json={"current_password": "wrong", "new_password": "another-password-12"}).status_code == 400


def test_a_parent_cannot_promote_themselves_by_forging_the_role_claim(client, parent, token):
    import jwt
    from config import ALGORITHM, SECRET_KEY
    claims = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    claims["role"] = "admin"
    forged = jwt.encode(claims, SECRET_KEY, algorithm=ALGORITHM)

    assert client.get("/students", headers=_bearer(forged)).status_code == 403
    assert client.get("/parents", headers=_bearer(forged)).status_code == 403


# ── What a parent can and cannot reach ──────────────────────────────────────

@pytest.mark.parametrize(
    "method, path",
    [
        ("get", "/dashboard/stats"), ("get", "/students"), ("get", "/students/1"), ("post", "/students"),
        ("get", "/fees"), ("get", "/fees/summary"), ("get", "/fees/student/1/summary"), ("get", "/fees/1/payments"),
        ("get", "/fees/1/pdf"), ("get", "/fees/payments/1/receipt"), ("post", "/fees/1/pay"), ("post", "/fees/generate"),
        ("get", "/results/1"), ("get", "/results/1/report-card/pdf"), ("get", "/results/class"), ("post", "/results"),
        ("get", "/attendance/overview"), ("get", "/attendance/students/1/history"), ("put", "/attendance/class-day"),
        ("get", "/teacher/classes"), ("put", "/teacher/classes/1/attendance"), ("get", "/teacher/profile"),
        ("get", "/teachers"), ("post", "/teachers"), ("get", "/teacher-assignments"),
        ("get", "/admissions"), ("get", "/ai/at-risk"), ("get", "/ai/at-risk/1"), ("post", "/chatbot/ask"),
        ("get", "/school/info"), ("get", "/parents"), ("post", "/parents"), ("get", "/result-publishing"),
    ],
)
def test_a_parent_is_refused_everywhere_outside_the_portal(client, token, method, path):
    response = getattr(client, method)(path, headers=_bearer(token))

    assert response.status_code == 403, f"{method.upper()} {path} answered {response.status_code}"


def test_every_route_is_either_public_or_refuses_a_parent(client, token):
    """The audit: a parent reaches only their portal, the account routes, and nothing is open to anonymous callers."""
    open_to_anyone = {("GET", "/"), ("GET", "/school/public"), ("POST", "/auth/login"), ("POST", "/auth/logout"),
                     ("POST", "/auth/forgot-password"), ("POST", "/auth/reset-password"), ("POST", "/auth/reset-password/check")}
    open_to_parents = {
        ("GET", "/auth/me"), ("POST", "/auth/change-password"),
        ("GET", "/parent/profile"), ("GET", "/parent/children"), ("GET", "/parent/children/{student_id}"),
        ("GET", "/parent/children/{student_id}/attendance"), ("GET", "/parent/children/{student_id}/results"),
        ("GET", "/parent/children/{student_id}/report-card/pdf"), ("GET", "/parent/children/{student_id}/fees"),
        ("GET", "/parent/children/{student_id}/invoices/{invoice_id}/challan/pdf"),
        ("GET", "/parent/children/{student_id}/payments/{payment_id}/receipt"),
    }
    problems, checked = [], 0
    for route_path, operations in app.openapi()["paths"].items():
        path = "/".join("1" if part.startswith("{") else part for part in route_path.split("/"))
        for method in (name.upper() for name in operations if name in {"get", "post", "put", "delete", "patch"}):
            if (method, route_path) in open_to_anyone:
                continue
            checked += 1
            anonymous = client.request(method, path).status_code
            if anonymous != 401:
                problems.append(f"{method} {route_path}: anonymous got {anonymous}")
            if (method, route_path) in open_to_parents:
                continue
            as_parent = client.request(method, path, headers=_bearer(token)).status_code
            if as_parent != 403:
                problems.append(f"{method} {route_path}: parent got {as_parent}")

    assert checked > 60, f"only {checked} routes were found, so this audit proves nothing"
    assert problems == []


def test_the_portal_is_read_only(client, token, ahmed):
    for method in ("post", "put", "delete", "patch"):
        for path in (f"/parent/children/{ahmed}/attendance", f"/parent/children/{ahmed}/fees", f"/parent/children/{ahmed}",
                     "/parent/children", "/parent/profile"):
            assert client.request(method, path, headers=_bearer(token)).status_code == 405, f"{method} {path}"


def test_a_teacher_cannot_use_the_parent_portal(client, admin_token, parent):
    client.post("/teachers", headers=_bearer(admin_token), json={
        "username": "sara.khan", "full_name": "Sara Khan", "password": "teacher-test-password-1"})
    teacher = _login(client, "sara.khan", "teacher-test-password-1").json()["access_token"]

    assert client.get("/parent/children", headers=_bearer(teacher)).status_code == 403
    assert client.get("/parent/profile", headers=_bearer(admin_token)).status_code == 403


# ── A parent sees only their own children ───────────────────────────────────

def test_the_dashboard_lists_only_linked_children(client, token, ahmed, bilal):
    body = client.get("/parent/children", headers=_bearer(token)).json()

    assert [child["roll_number"] for child in body["children"]] == [AHMED]
    assert BILAL not in str(body) and "Bilal" not in str(body)
    child = body["children"][0]
    assert child["name"] == "Ahmed Khan" and child["grade"] == "Grade 8" and child["section"] == "B"
    # Contact details and the date of birth are not needed on the portal.
    assert "phone" not in child and "dob" not in child


def test_a_child_that_is_not_linked_looks_like_it_does_not_exist(client, token, bilal):
    """Every per-child route gives the same 404 for someone else's child as for an id that does not exist."""
    with Session(engine) as session:
        bilal_invoice = session.exec(select(Invoice).where(Invoice.student_id == bilal)).first().id
        bilal_payment = session.exec(select(Payment).join(Invoice).where(Invoice.student_id == bilal)).first()
    paths = [
        "", "/attendance", "/results", "/report-card/pdf", "/fees",
        f"/invoices/{bilal_invoice}/challan/pdf",
        f"/payments/{bilal_payment.id}/receipt" if bilal_payment else "/payments/1/receipt",
    ]
    for other in (bilal, 999999):
        for suffix in paths:
            response = client.get(f"/parent/children/{other}{suffix}", headers=_bearer(token))
            assert response.status_code == 404, f"/parent/children/{other}{suffix} answered {response.status_code}"
            assert response.json() == {"detail": "Student not found"}


def test_invoices_and_receipts_of_another_child_cannot_be_reached_through_a_linked_child(client, token, ahmed, bilal):
    """Asking for Bilal's invoice or payment under Ahmed's own address must not work either."""
    with Session(engine) as session:
        bilal_invoice = session.exec(select(Invoice).where(Invoice.student_id == bilal)).first()
        bilal_payment = session.exec(select(Payment).where(Payment.invoice_id == bilal_invoice.id)).first()
        if bilal_payment is None:
            bilal_payment = Payment(invoice_id=bilal_invoice.id, amount_paid=100.0, payment_mode="test-added")
            session.add(bilal_payment)
            session.commit()
            session.refresh(bilal_payment)
        invoice_id, payment_id = bilal_invoice.id, bilal_payment.id

    assert client.get(f"/parent/children/{ahmed}/invoices/{invoice_id}/challan/pdf", headers=_bearer(token)).status_code == 404
    assert client.get(f"/parent/children/{ahmed}/payments/{payment_id}/receipt", headers=_bearer(token)).status_code == 404


def test_unlinking_removes_access_at_once(client, admin_token, parent, token, ahmed):
    assert client.get(f"/parent/children/{ahmed}/fees", headers=_bearer(token)).status_code == 200

    client.delete(f"/parents/{parent['id']}/children/{ahmed}", headers=_bearer(admin_token))

    assert client.get(f"/parent/children/{ahmed}/fees", headers=_bearer(token)).status_code == 404
    assert client.get("/parent/children", headers=_bearer(token)).json()["children"] == []


def test_two_parents_each_see_only_their_own_children(client, admin_token, parent, token, bilal):
    _create_parent(client, admin_token, [bilal], username="mr.tariq", email="tariq@example.test")
    other = _login(client, "mr.tariq", PARENT_PASSWORD).json()["access_token"]

    assert [c["roll_number"] for c in client.get("/parent/children", headers=_bearer(other)).json()["children"]] == [BILAL]
    assert [c["roll_number"] for c in client.get("/parent/children", headers=_bearer(token)).json()["children"]] == [AHMED]
    assert client.get(f"/parent/children/{bilal}/fees", headers=_bearer(token)).status_code == 404


def test_a_parent_with_several_children_sees_them_all(client, admin_token, bilal, ahmed):
    _create_parent(client, admin_token, [ahmed, bilal])
    parent_token = _login(client, "mr.khan", PARENT_PASSWORD).json()["access_token"]

    body = client.get("/parent/children", headers=_bearer(parent_token)).json()

    assert {c["roll_number"] for c in body["children"]} == {AHMED, BILAL}
    assert body["totals"]["outstanding"] == round(sum(c["fees"]["outstanding"] for c in body["children"]), 2)


def test_profile_shows_the_account_and_its_children(client, parent, token):
    body = client.get("/parent/profile", headers=_bearer(token)).json()

    assert body["username"] == parent["username"] and body["full_name"] == "Imran Khan"
    assert [c["roll_number"] for c in body["children"]] == [AHMED]
    assert "password_hash" not in str(body).lower() and "$2" not in str(body)


# ── Attendance ──────────────────────────────────────────────────────────────

def test_attendance_shows_real_records_and_the_percentage(client, token, ahmed):
    _mark_attendance(ahmed, 1, "present")
    _mark_attendance(ahmed, 2, "late")
    _mark_attendance(ahmed, 3, "absent")
    _mark_attendance(ahmed, 4, "leave")
    month = school_today().strftime("%Y-%m")

    body = client.get(f"/parent/children/{ahmed}/attendance?month={month}", headers=_bearer(token)).json()

    in_month = [d for d in body["days"] if d["date"].startswith(month)]
    assert len(body["days"]) == len(in_month)  # only the requested month
    summary = body["session_summary"]
    assert summary["recorded"] == 4 and summary["present"] == 1 and summary["late"] == 1
    assert summary["absent"] == 1 and summary["leave"] == 1
    assert summary["attendance_rate"] == 50.0  # (present + late) of recorded, like the staff reports
    assert body["session_label"] == "2025-2026"


def test_a_day_without_a_record_is_not_shown_as_absent(client, token, ahmed):
    body = client.get(f"/parent/children/{ahmed}/attendance", headers=_bearer(token)).json()

    assert body["days"] == []
    assert body["month_summary"]["recorded"] == 0 and body["month_summary"]["absent"] == 0
    assert body["month_summary"]["attendance_rate"] is None


def test_attendance_hides_who_marked_it_and_why_it_was_corrected(client, admin_token, token, ahmed):
    _mark_attendance(ahmed, 1, "absent")
    with Session(engine) as session:
        record = session.exec(select(StudentAttendance).where(StudentAttendance.student_id == ahmed)).one()
        session.add(AttendanceChangeHistory(
            attendance_id=record.id, student_id=ahmed, attendance_date=record.attendance_date, old_status="present",
            new_status="absent", reason="secret staff reason", changed_by=record.marked_by))
        session.commit()

    text = client.get(f"/parent/children/{ahmed}/attendance", headers=_bearer(token)).text

    assert "secret staff reason" not in text and "marked_by" not in text and "changes" not in text


def test_attendance_month_must_be_valid(client, token, ahmed):
    assert client.get(f"/parent/children/{ahmed}/attendance?month=nonsense", headers=_bearer(token)).status_code == 422


def test_a_parent_cannot_change_attendance(client, token, ahmed):
    _mark_attendance(ahmed, 1, "absent")
    today = school_today().isoformat()

    for method, path, body in (
        ("put", "/attendance/class-day", {"date": today, "grade": "Grade 8", "section": "B", "entries": []}),
        ("put", "/teacher/classes/1/attendance", {"date": today, "entries": []}),
        ("put", f"/parent/children/{ahmed}/attendance", {"date": today, "status": "present"}),
        ("post", f"/parent/children/{ahmed}/attendance", {"date": today, "status": "present"}),
    ):
        assert getattr(client, method)(path, headers=_bearer(token), json=body).status_code in (403, 405)
    with Session(engine) as session:
        assert session.exec(select(StudentAttendance)).one().status == "absent"


# ── Results ─────────────────────────────────────────────────────────────────

def test_results_stay_hidden_until_the_school_publishes_them(client, admin_token, token, ahmed):
    before = client.get(f"/parent/children/{ahmed}/results", headers=_bearer(token)).json()
    assert before["results"] == [] and before["available_exams"] == [] and before["exam"] is None
    assert client.get(f"/parent/children/{ahmed}/report-card/pdf", headers=_bearer(token)).status_code == 404

    assert _publish(client, admin_token).status_code == 200
    after = client.get(f"/parent/children/{ahmed}/results", headers=_bearer(token)).json()

    assert len(after["results"]) == 6
    assert after["exam"] == {"exam_type": "Final Term", "academic_year_id": 1, "session": "2025-2026"}
    assert after["summary"]["percentage"] > 0 and after["summary"]["grade"] != "N/A"
    row = after["results"][0]
    assert {"subject", "marks_obtained", "total_marks", "percentage", "grade", "passed"} <= set(row)
    assert after["promotion"]["status"] in {"promoted", "not_promoted", "incomplete"}

    _publish(client, admin_token, published=False)
    assert client.get(f"/parent/children/{ahmed}/results", headers=_bearer(token)).json()["results"] == []
    assert client.get(f"/parent/children/{ahmed}/report-card/pdf", headers=_bearer(token)).status_code == 404


def test_results_match_what_the_staff_see(client, admin_token, token, ahmed):
    _publish(client, admin_token)
    staff = client.get(f"/results/{ahmed}", headers=_bearer(admin_token)).json()
    parent_view = client.get(f"/parent/children/{ahmed}/results", headers=_bearer(token)).json()

    strip = lambda rows: [{k: v for k, v in r.items() if k in {"subject", "marks_obtained", "total_marks", "grade", "percentage"}} for r in rows]
    assert strip(parent_view["results"]) == strip(staff["results"])
    assert parent_view["summary"] == staff["summary"]


def test_only_the_published_exam_is_shown_even_if_a_newer_one_is_recorded(client, admin_token, token, ahmed):
    """The final term is the newest exam, but only the midterm was released, so only it shows."""
    with Session(engine) as session:
        for subject in ("English", "Math"):
            session.add(Result(student_id=ahmed, subject=subject, marks_obtained=33, total_marks=50,
                               exam_type="Midterm", academic_year_id=1))
        session.commit()
    assert _publish(client, admin_token, exam_type="Midterm").status_code == 200

    body = client.get(f"/parent/children/{ahmed}/results", headers=_bearer(token)).json()

    assert body["exam"]["exam_type"] == "Midterm" and len(body["results"]) == 2
    assert [exam["exam_type"] for exam in body["available_exams"]] == ["Midterm"]
    # Asking for the unreleased exam by name does not work either.
    asked = client.get(f"/parent/children/{ahmed}/results?exam_type=Final%20Term", headers=_bearer(token)).json()
    assert asked["results"] == [] and asked["exam"] is None
    card = client.get(f"/parent/children/{ahmed}/report-card/pdf?exam_type=Final%20Term", headers=_bearer(token))
    assert card.status_code == 404


def test_a_published_report_card_downloads_as_a_pdf(client, admin_token, token, ahmed):
    _publish(client, admin_token)

    response = client.get(f"/parent/children/{ahmed}/report-card/pdf", headers=_bearer(token))

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf" and response.content.startswith(b"%PDF")


def test_results_contain_no_estimate_or_contact_details(client, admin_token, token, ahmed):
    _publish(client, admin_token)

    text = client.get(f"/parent/children/{ahmed}/results", headers=_bearer(token)).text.lower()

    for private in ("risk", "shap", "phone", "dob", "0300"):
        assert private not in text


def test_publishing_is_checked_and_reversible(client, admin_token):
    assert _publish(client, admin_token, year=99).status_code == 404
    first = _publish(client, admin_token).json()
    again = _publish(client, admin_token).json()  # repeating changes nothing
    row = next(r for r in first if r["exam_type"] == "Final Term")
    assert row["published"] is True and row["session"] == "2025-2026" and row["students_with_marks"] >= 50
    assert again == first
    assert next(r for r in _publish(client, admin_token, published=False).json() if r["exam_type"] == "Final Term")["published"] is False
    assert client.get("/result-publishing", headers=_bearer(admin_token)).status_code == 200
    assert client.put("/result-publishing", headers=_bearer(admin_token),
                      json={"academic_year_id": 1, "exam_type": "Quiz", "published": True}).status_code == 422


# ── Fees ────────────────────────────────────────────────────────────────────

def test_fees_show_real_invoices_balances_and_payment_history(client, token, ahmed):
    with Session(engine) as session:
        invoice = session.exec(select(Invoice).where(Invoice.student_id == ahmed, Invoice.month == "October 2025")).one()
        session.add(Payment(invoice_id=invoice.id, amount_paid=1000.0, payment_mode="test-added"))
        session.commit()
        invoice_id = invoice.id

    body = client.get(f"/parent/children/{ahmed}/fees", headers=_bearer(token)).json()

    ids = [i["id"] for i in body["invoices"]]
    assert ids == sorted(ids, reverse=True) and len(ids) == 2
    row = next(i for i in body["invoices"] if i["id"] == invoice_id)
    assert row["amount"] == 4000.0 and row["amount_paid"] == 1000.0 and row["balance"] == 3000.0
    assert row["challan_number"].startswith("CHN-") and row["month"] == "October 2025"
    assert len(row["payments"]) == 1 and row["payments"][0]["receipt_number"].startswith("RCP-")
    assert body["totals"]["invoiced"] == 7500.0 and body["totals"]["collected"] == 1000.0
    assert body["totals"]["outstanding"] == 6500.0


def test_fee_totals_equal_the_ledger_the_staff_use(client, admin_token, token, ahmed):
    parent_totals = client.get(f"/parent/children/{ahmed}/fees", headers=_bearer(token)).json()["totals"]
    staff_totals = client.get(f"/fees/student/{ahmed}/summary", headers=_bearer(admin_token)).json()

    assert parent_totals == staff_totals
    dashboard = client.get("/parent/children", headers=_bearer(token)).json()["children"][0]["fees"]
    assert dashboard == staff_totals


def test_a_receipt_and_a_challan_download_for_the_parents_own_child(client, token, ahmed):
    with Session(engine) as session:
        invoice = session.exec(select(Invoice).where(Invoice.student_id == ahmed)).first()
        payment = Payment(invoice_id=invoice.id, amount_paid=500.0, payment_mode="test-added")
        session.add(payment)
        session.commit()
        session.refresh(payment)
        invoice_id, payment_id = invoice.id, payment.id

    receipt = client.get(f"/parent/children/{ahmed}/payments/{payment_id}/receipt", headers=_bearer(token))
    challan = client.get(f"/parent/children/{ahmed}/invoices/{invoice_id}/challan/pdf", headers=_bearer(token))

    for response in (receipt, challan):
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf" and response.content.startswith(b"%PDF")
    assert client.get(f"/parent/children/{ahmed}/payments/999999/receipt", headers=_bearer(token)).status_code == 404
    assert client.get(f"/parent/children/{ahmed}/invoices/999999/challan/pdf", headers=_bearer(token)).status_code == 404


def test_there_is_no_way_to_pay_online(client, token, ahmed):
    with Session(engine) as session:
        invoice_id = session.exec(select(Invoice).where(Invoice.student_id == ahmed)).first().id

    for method, path in (("post", f"/fees/{invoice_id}/pay"), ("post", f"/parent/children/{ahmed}/fees"),
                         ("post", f"/parent/children/{ahmed}/invoices/{invoice_id}/pay")):
        assert getattr(client, method)(path, headers=_bearer(token), json={"amount_paid": 10}).status_code in (403, 404, 405)
    with Session(engine) as session:
        assert session.exec(select(Payment).where(Payment.invoice_id == invoice_id, Payment.amount_paid == 10)).first() is None


# ── Existing behaviour is preserved ─────────────────────────────────────────

def test_administrators_and_teachers_keep_their_access(client, admin_token):
    for path in ("/students", "/fees", "/dashboard/stats", "/admissions", "/school/info", "/teachers", "/attendance/overview"):
        assert client.get(path, headers=_bearer(admin_token)).status_code == 200, path

    client.post("/teachers", headers=_bearer(admin_token), json={
        "username": "sara.khan", "full_name": "Sara Khan", "password": "teacher-test-password-1"})
    teacher = _login(client, "sara.khan", "teacher-test-password-1").json()["access_token"]
    assert client.get("/teacher/profile", headers=_bearer(teacher)).status_code == 200
    assert client.get("/teacher/classes", headers=_bearer(teacher)).status_code == 200
    assert client.get("/students", headers=_bearer(teacher)).status_code == 403


def test_the_new_tables_are_new_and_touch_no_existing_table():
    from sqlalchemy import inspect

    with Session(engine) as session:
        tables = set(inspect(session.get_bind()).get_table_names())
        user_columns = {c["name"] for c in inspect(session.get_bind()).get_columns("users")}

    assert {"parent_student_links", "published_exams"} <= tables
    assert user_columns == {"id", "username", "password_hash", "role", "created_at", "is_active", "full_name", "email"}


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
