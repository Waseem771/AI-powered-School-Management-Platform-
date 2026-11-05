"""What the improved pages rely on: filters, per-student fees, receipts, activity, and whole-class marks."""
import itertools

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from conftest import TEST_ADMIN_PASSWORD
from database import engine
from main import app
from models.fee import Invoice, Payment
from models.result import Result
from models.student import Student
from services.fee_ledger import monthly_totals, school_totals

_rolls = itertools.count(1)
A4_SAFE_HEADER = b"%PDF"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def headers(client):
    token = client.post("/auth/login", json={"username": "admin", "password": TEST_ADMIN_PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _student(client, headers, grade="Grade 7", section="B", name="Sample Student"):
    response = client.post("/students", headers=headers, json={
        "name": name, "roll_number": f"P8-{next(_rolls)}", "grade": grade, "section": section,
        "guardian_name": "Sample Guardian", "phone": "0300-1234567",
    })
    assert response.status_code == 201, response.text
    return response.json()


def _challan(client, headers, student_id, month="March 2031", amount=4000, due="2031-03-10"):
    response = client.post("/fees/generate", headers=headers, json={"student_id": student_id, "amount": amount, "month": month, "due_date": due})
    assert response.status_code == 201, response.text
    return response.json()["invoice_id"]


def _pay(client, headers, invoice_id, amount, mode="bank"):
    response = client.post(f"/fees/{invoice_id}/pay", headers=headers, json={"amount_paid": amount, "payment_mode": mode})
    assert response.status_code == 201, response.text
    return response.json()


# ── Students ──────────────────────────────────────────────────────────────────

def test_students_filter_by_section(client, headers):
    student = _student(client, headers, grade="Grade 6", section="B")

    rows = client.get("/students", headers=headers, params={"grade": "Grade 6", "section": "B"}).json()

    assert student["id"] in [row["id"] for row in rows]
    assert {row["section"] for row in rows} == {"B"}
    assert {row["grade"] for row in rows} == {"Grade 6"}


# ── One student's fees ────────────────────────────────────────────────────────

def test_student_fee_summary_uses_payment_records(client, headers):
    student = _student(client, headers)
    first = _challan(client, headers, student["id"], "January 2031", 4000, "2031-01-10")
    _challan(client, headers, student["id"], "February 2031", 3000, "2031-02-10")
    _pay(client, headers, first, 1500)

    summary = client.get(f"/fees/student/{student['id']}/summary", headers=headers).json()

    assert summary["invoiced"] == 7000
    assert summary["collected"] == 1500
    assert summary["outstanding"] == 5500
    assert summary["invoice_count"] == 2


def test_student_fee_summary_for_a_student_with_no_invoices(client, headers):
    student = _student(client, headers)

    summary = client.get(f"/fees/student/{student['id']}/summary", headers=headers).json()

    assert summary == {"invoice_count": 0, "invoiced": 0, "collected": 0, "outstanding": 0, "overdue": 0}


def test_student_fee_summary_for_an_unknown_student(client, headers):
    assert client.get("/fees/student/999999/summary", headers=headers).status_code == 404


def test_chatbot_and_page_agree_on_one_students_fees(client, headers):
    from services.data_assistant_service import SchoolDataAssistant

    student = _student(client, headers)
    invoice = _challan(client, headers, student["id"], "April 2031", 4000, "2031-04-10")
    _pay(client, headers, invoice, 1000)
    page = client.get(f"/fees/student/{student['id']}/summary", headers=headers).json()

    with Session(engine) as session:
        chat = SchoolDataAssistant(session).get_student_fee_summary(f"id:{student['id']}")["totals"]

    assert (chat["invoiced"], chat["paid"], chat["pending"]) == (page["invoiced"], page["collected"], page["outstanding"])


# ── Receipts ──────────────────────────────────────────────────────────────────

def test_payment_response_and_history_name_the_receipt(client, headers):
    student = _student(client, headers)
    invoice = _challan(client, headers, student["id"], "May 2031", 4000, "2031-05-10")

    paid = _pay(client, headers, invoice, 1500)
    history = client.get(f"/fees/{invoice}/payments", headers=headers).json()

    assert paid["payment_id"] == history[0]["id"]
    assert paid["receipt_number"] == history[0]["receipt_number"] == f"RCP-{paid['payment_id']:06d}"
    assert history[0]["paid_at"].endswith("+00:00")


def test_receipt_is_a_pdf_named_by_its_number_with_no_student_name(client, headers):
    student = _student(client, headers, name="Hina Soomro")
    invoice = _challan(client, headers, student["id"], "June 2031", 4000, "2031-06-10")
    paid = _pay(client, headers, invoice, 4000)

    response = client.get(f"/fees/payments/{paid['payment_id']}/receipt", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(A4_SAFE_HEADER)
    disposition = response.headers["content-disposition"]
    assert paid["receipt_number"] in disposition
    assert "Hina" not in disposition


def test_receipt_prints_awkward_older_text_safely():
    from services.receipts import generate_receipt_pdf

    pdf = generate_receipt_pdf({
        "receipt_number": "RCP-000001", "received_at": "5 Nov 2026", "payment_mode": "cash",
        "amount_received": 1000.5, "invoice_amount": 4000, "paid_to_date": 1000.5, "balance_after": 2999.5,
        "challan_number": "CHN-1", "month": "November 2026", "student_name": "Ali <b>Bold & Co", "roll_number": "1",
        "class_name": "Grade 8-A", "guardian_name": "<script>",
    })

    assert pdf.startswith(A4_SAFE_HEADER)


def test_receipt_details_show_the_balance_as_of_that_payment(client, headers):
    from services.receipts import receipt_details

    student = _student(client, headers)
    invoice = _challan(client, headers, student["id"], "July 2031", 4000, "2031-07-10")
    first = _pay(client, headers, invoice, 1000)
    second = _pay(client, headers, invoice, 500)

    with Session(engine) as session:
        early = receipt_details(session, first["payment_id"])
        late = receipt_details(session, second["payment_id"])

    assert (early["amount_received"], early["paid_to_date"], early["balance_after"]) == (1000, 1000, 3000)
    assert (late["amount_received"], late["paid_to_date"], late["balance_after"]) == (500, 1500, 2500)


def test_receipt_prints_for_an_urdu_name(client, headers):
    student = _student(client, headers, name="محمد علی")
    invoice = _challan(client, headers, student["id"], "August 2031", 4000, "2031-08-10")
    paid = _pay(client, headers, invoice, 100)

    assert client.get(f"/fees/payments/{paid['payment_id']}/receipt", headers=headers).status_code == 200


def test_unknown_receipt_and_login_are_refused(client, headers):
    assert client.get("/fees/payments/999999/receipt", headers=headers).status_code == 404
    assert client.get("/fees/payments/1/receipt").status_code == 401


# ── Dashboard ─────────────────────────────────────────────────────────────────

def test_dashboard_lists_real_billing_months_and_filters_one(client, headers):
    student = _student(client, headers)
    invoice = _challan(client, headers, student["id"], "September 2047", 4000, "2047-09-10")
    _pay(client, headers, invoice, 1000)

    everything = client.get("/dashboard/stats", headers=headers).json()
    one_month = client.get("/dashboard/stats", headers=headers, params={"month": "September 2047"}).json()

    assert "September 2047" in everything["fee_months"]
    assert everything["fee_period"]["month"] is None
    assert one_month["fee_period"]["month"] == "September 2047"
    assert one_month["fee_period"]["invoiced"] == 4000
    assert one_month["fee_period"]["collected"] == 1000
    assert one_month["fee_period"]["outstanding"] == 3000
    assert [row["value"] for row in one_month["fee_summary"]] == [1000, 3000]
    assert one_month["kpis"]["total_students"] == everything["kpis"]["total_students"]


def test_dashboard_month_with_no_invoices_gives_zeros_not_an_error(client, headers):
    period = client.get("/dashboard/stats", headers=headers, params={"month": "January 1999"}).json()["fee_period"]

    assert (period["invoiced"], period["collected"], period["outstanding"]) == (0, 0, 0)


def test_monthly_rows_add_up_to_the_school_totals_including_overdue():
    with Session(engine) as session:
        rows = monthly_totals(session)
        totals = school_totals(session)

    assert round(sum(row["overdue"] for row in rows), 2) == totals["overdue"]
    assert round(sum(row["outstanding"] for row in rows), 2) == totals["outstanding"]


def test_recent_activity_comes_from_real_records_newest_first(client, headers):
    student = _student(client, headers, name="Recent Activity")
    invoice = _challan(client, headers, student["id"], "October 2031", 4000, "2031-10-10")
    paid = _pay(client, headers, invoice, 1500)

    activity = client.get("/dashboard/activity", headers=headers).json()

    times = [item["at"] for item in activity["items"]]
    assert times == sorted(times, reverse=True)
    payment = next(item for item in activity["items"] if item["kind"] == "payment" and item["payment_id"] == paid["payment_id"])
    assert payment["student_id"] == student["id"]
    assert payment["amount"] == 1500
    assert any(item["kind"] == "challan" and item["student_id"] == student["id"] for item in activity["items"])
    assert any(item["kind"] == "enrolment" and item["student_id"] == student["id"] for item in activity["items"])


def test_recent_activity_has_a_limit_and_no_contact_details(client, headers):
    activity = client.get("/dashboard/activity", headers=headers, params={"limit": 3}).json()

    assert len(activity["items"]) <= 3
    assert all("phone" not in item and "guardian_name" not in item for item in activity["items"])
    assert client.get("/dashboard/activity", headers=headers, params={"limit": 5000}).status_code == 422
    assert client.get("/dashboard/activity").status_code == 401


def test_archived_students_do_not_appear_as_enrolments(client, headers):
    student = _student(client, headers, name="Archived Enrolment")
    client.post(f"/students/{student['id']}/archive", headers=headers)

    items = client.get("/dashboard/activity", headers=headers).json()["items"]

    assert not any(item["kind"] == "enrolment" and item["student_id"] == student["id"] for item in items)


# ── Whole-class marks ─────────────────────────────────────────────────────────

def _class_sheet(client, headers, grade="Grade 10", section="A", subject="Science", exam="Midterm"):
    return client.get("/results/class", headers=headers, params={"grade": grade, "section": section, "subject": subject, "exam_type": exam})


def test_class_sheet_lists_current_students_with_saved_marks(client, headers):
    student = _student(client, headers, grade="Grade 10", section="A")
    client.post("/results", headers=headers, json={"student_id": student["id"], "subject": "Science", "marks_obtained": 55, "total_marks": 75, "exam_type": "Midterm"})
    archived = _student(client, headers, grade="Grade 10", section="A", name="Left School")
    client.post(f"/students/{archived['id']}/archive", headers=headers)

    sheet = _class_sheet(client, headers).json()

    ids = [row["id"] for row in sheet["students"]]
    row = next(item for item in sheet["students"] if item["id"] == student["id"])
    assert (row["marks_obtained"], row["total_marks"]) == (55, 75)
    assert archived["id"] not in ids
    assert all(item["grade"] == "Grade 10" and item["section"] == "A" for item in sheet["students"])


def test_class_sheet_refuses_an_unknown_subject(client, headers):
    assert _class_sheet(client, headers, subject="Astrology").status_code == 422


def test_saving_class_marks_inserts_and_updates(client, headers):
    first = _student(client, headers, grade="Grade 9", section="B")
    second = _student(client, headers, grade="Grade 9", section="B")
    client.post("/results", headers=headers, json={"student_id": first["id"], "subject": "Urdu", "marks_obtained": 10, "exam_type": "Midterm"})

    response = client.post("/results/class", headers=headers, json={
        "subject": "Urdu", "exam_type": "Midterm", "total_marks": 100,
        "entries": [{"student_id": first["id"], "marks_obtained": 80}, {"student_id": second["id"], "marks_obtained": 35.5}],
    })

    assert response.status_code == 200, response.text
    assert response.json()["saved"] == 2
    with Session(engine) as session:
        marks = session.exec(select(Result).where(Result.subject == "Urdu", Result.exam_type == "Midterm", Result.student_id.in_([first["id"], second["id"]]))).all()
    assert sorted(mark.marks_obtained for mark in marks) == [35.5, 80]


def test_one_bad_mark_saves_nothing(client, headers):
    good = _student(client, headers, grade="Grade 9", section="A")
    archived = _student(client, headers, grade="Grade 9", section="A")
    client.post(f"/students/{archived['id']}/archive", headers=headers)

    too_high = client.post("/results/class", headers=headers, json={
        "subject": "English", "exam_type": "Midterm", "total_marks": 50,
        "entries": [{"student_id": good["id"], "marks_obtained": 40}, {"student_id": good["id"], "marks_obtained": 60}],
    })
    has_archived = client.post("/results/class", headers=headers, json={
        "subject": "English", "exam_type": "Midterm", "total_marks": 50,
        "entries": [{"student_id": good["id"], "marks_obtained": 40}, {"student_id": archived["id"], "marks_obtained": 40}],
    })
    unknown = client.post("/results/class", headers=headers, json={
        "subject": "English", "exam_type": "Midterm", "total_marks": 50,
        "entries": [{"student_id": good["id"], "marks_obtained": 40}, {"student_id": 999999, "marks_obtained": 40}],
    })

    assert too_high.status_code == 422
    assert has_archived.status_code == 409
    assert archived["roll_number"] in has_archived.json()["detail"]
    assert unknown.status_code == 404
    with Session(engine) as session:
        assert not session.exec(select(Result).where(Result.student_id == good["id"])).all()


def test_the_same_student_twice_in_one_save_is_refused(client, headers):
    student = _student(client, headers)

    response = client.post("/results/class", headers=headers, json={
        "subject": "English", "exam_type": "Midterm", "total_marks": 50,
        "entries": [{"student_id": student["id"], "marks_obtained": 10}, {"student_id": student["id"], "marks_obtained": 20}],
    })

    assert response.status_code == 422


def test_class_marks_limits_and_login(client, headers):
    empty = client.post("/results/class", headers=headers, json={"subject": "English", "exam_type": "Midterm", "total_marks": 50, "entries": []})
    no_login = client.post("/results/class", json={"subject": "English", "exam_type": "Midterm", "total_marks": 50, "entries": [{"student_id": 1, "marks_obtained": 1}]})

    assert empty.status_code == 422
    assert no_login.status_code == 401
    assert client.get("/results/class", params={"grade": "Grade 9", "section": "A", "subject": "Urdu"}).status_code == 401


# ── Demo mode ─────────────────────────────────────────────────────────────────

def test_public_school_details_are_limited_and_need_no_login(client):
    details = client.get("/school/public").json()

    assert set(details) == {"name", "demo_mode"}
    assert details["demo_mode"] is False


def test_demo_mode_follows_its_setting(client, headers, monkeypatch):
    from routers import school

    monkeypatch.setattr(school, "DEMO_MODE", True)

    assert client.get("/school/public").json()["demo_mode"] is True
    assert client.get("/school/info", headers=headers).json()["demo_mode"] is True


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-q"]))
