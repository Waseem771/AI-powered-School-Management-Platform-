"""Fee integrity: invoices are valid, money received is what is recorded, and totals agree everywhere."""
import itertools
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from database import engine
from main import app
from models.fee import Invoice, Payment
from services.data_assistant_service import SchoolDataAssistant
from services.fee_ledger import is_overdue, outstanding_balance, parse_due_date, payment_status

_rolls = itertools.count(1)
_months = itertools.count(1)


@pytest.fixture()
def client(admin_password):
    with TestClient(app) as test_client:
        token = test_client.post(
            "/auth/login", json={"username": "admin", "password": admin_password}
        ).json()["access_token"]
        test_client.headers.update({"Authorization": f"Bearer {token}"})
        yield test_client


@pytest.fixture()
def student_id(client):
    response = client.post(
        "/students",
        json={
            "name": "Fee Test",
            "roll_number": f"FEE-{next(_rolls)}",
            "grade": "Grade 8",
            "section": "A",
            "guardian_name": "Guardian",
            "phone": "0300-1234567",
        },
    )
    return response.json()["id"]


def _next_month():
    index = next(_months)
    names = ["January", "February", "March", "April", "May", "June", "July",
             "August", "September", "October", "November", "December"]
    return f"{names[index % 12]} {2030 + index // 12}"


def _generate(client, student_id, **overrides):
    body = {"student_id": student_id, "amount": 4000, "month": _next_month(), "due_date": "2030-01-10", **overrides}
    return client.post("/fees/generate", json=body)


@pytest.fixture()
def invoice_id(client, student_id):
    return _generate(client, student_id).json()["invoice_id"]


def _invoice(client, student_id, invoice_id):
    rows = client.get("/fees", params={"student_id": student_id}).json()
    return next(row for row in rows if row["id"] == invoice_id)


def _payment_rows(invoice_id):
    with Session(engine) as session:
        return session.exec(select(Payment).where(Payment.invoice_id == invoice_id)).all()


# ── Issuing challans ────────────────────────────────────────────────────────

def test_valid_challan_is_created_as_pending_with_a_full_balance(client, student_id):
    response = _generate(client, student_id, amount=4000)

    assert response.status_code == 201
    row = _invoice(client, student_id, response.json()["invoice_id"])
    assert row["status"] == "pending"
    assert row["amount_paid"] == 0
    assert row["balance"] == 4000


@pytest.mark.parametrize(
    "overrides",
    [
        {"amount": -500},
        {"amount": 0},
        {"amount": float("1e12")},
        {"month": "banana"},
        {"month": "13-2026"},
        {"due_date": "??"},
        {"due_date": "2026-02-31"},
    ],
    ids=["negative", "zero", "absurd", "junk-month", "bad-month", "junk-date", "impossible-date"],
)
def test_invalid_challan_details_are_rejected(client, student_id, overrides):
    assert _generate(client, student_id, **overrides).status_code == 422


def test_challan_needs_every_field_rather_than_stale_defaults(client, student_id):
    assert client.post("/fees/generate", json={"student_id": student_id}).status_code == 422


def test_unknown_student_gets_404(client):
    assert _generate(client, 999999).status_code == 404


def test_second_challan_for_the_same_month_is_rejected(client, student_id):
    month = _next_month()
    assert _generate(client, student_id, month=month).status_code == 201

    duplicate = _generate(client, student_id, month=month)

    assert duplicate.status_code == 409
    assert month in duplicate.json()["detail"]


def test_same_month_is_fine_for_a_different_student(client, student_id):
    other = client.post(
        "/students",
        json={"name": "Other", "roll_number": f"FEE-{next(_rolls)}", "grade": "Grade 8", "section": "A",
              "guardian_name": "G", "phone": "0300-1234567"},
    ).json()["id"]
    month = _next_month()

    assert _generate(client, student_id, month=month).status_code == 201
    assert _generate(client, other, month=month).status_code == 201


def test_month_and_due_date_are_stored_in_one_format(client, student_id):
    created = _generate(client, student_id, month="november 2031", due_date="2031-11-10").json()

    row = _invoice(client, student_id, created["invoice_id"])

    assert row["month"] == "November 2031"
    assert row["due_date"] == "10-Nov-2031"
    assert row["due_on"] == "2031-11-10"


# ── Recording payments ──────────────────────────────────────────────────────

def _pay(client, invoice_id, **body):
    return client.post(f"/fees/{invoice_id}/pay", json=body)


def test_paying_without_an_amount_settles_the_remaining_balance(client, student_id, invoice_id):
    response = _pay(client, invoice_id, payment_mode="cash")

    assert response.status_code == 201
    assert response.json()["amount_paid"] == 4000
    assert response.json()["balance"] == 0
    assert response.json()["status"] == "paid"
    assert len(_payment_rows(invoice_id)) == 1


def test_paying_a_settled_invoice_is_rejected_and_records_nothing(client, invoice_id):
    _pay(client, invoice_id)

    second = _pay(client, invoice_id)
    third = _pay(client, invoice_id, amount_paid=4000, payment_mode="bank")

    assert second.status_code == third.status_code == 409
    assert len(_payment_rows(invoice_id)) == 1


def test_partial_payment_keeps_the_invoice_open_with_the_right_balance(client, student_id, invoice_id):
    response = _pay(client, invoice_id, amount_paid=1500)

    assert response.status_code == 201
    assert response.json()["status"] == "partial"
    assert response.json()["balance"] == 2500
    row = _invoice(client, student_id, invoice_id)
    assert (row["status"], row["amount_paid"], row["balance"]) == ("partial", 1500, 2500)


def test_instalments_add_up_and_settle_the_invoice(client, student_id, invoice_id):
    _pay(client, invoice_id, amount_paid=1000)
    _pay(client, invoice_id, amount_paid=2000, payment_mode="bank")

    last = _pay(client, invoice_id)

    assert last.json()["amount_paid"] == 1000
    assert last.json()["status"] == "paid"
    assert sum(payment.amount_paid for payment in _payment_rows(invoice_id)) == 4000


def test_payment_history_lists_each_instalment(client, invoice_id):
    _pay(client, invoice_id, amount_paid=1000, payment_mode="cash")
    _pay(client, invoice_id, amount_paid=500, payment_mode="online")

    history = client.get(f"/fees/{invoice_id}/payments").json()

    assert [(item["amount_paid"], item["payment_mode"]) for item in history] == [(1000, "cash"), (500, "online")]
    assert all(item["paid_at"] for item in history)


def test_history_of_unknown_invoice_gets_404(client):
    assert client.get("/fees/999999/payments").status_code == 404


def test_overpayment_is_rejected_and_records_nothing(client, invoice_id):
    response = _pay(client, invoice_id, amount_paid=4000.01)

    assert response.status_code == 422
    assert _payment_rows(invoice_id) == []


@pytest.mark.parametrize(
    "body",
    [{"amount_paid": -100}, {"amount_paid": 0}, {"amount_paid": 0.001}, {"payment_mode": "bitcoin"}],
    ids=["negative", "zero", "fraction-of-paisa", "unknown-mode"],
)
def test_invalid_payments_are_rejected_and_record_nothing(client, invoice_id, body):
    assert _pay(client, invoice_id, **body).status_code == 422
    assert _payment_rows(invoice_id) == []


def test_paying_an_unknown_invoice_gets_404(client):
    assert _pay(client, 999999).status_code == 404


def test_simultaneous_payments_record_only_one(client, invoice_id):
    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(lambda _: _pay(client, invoice_id).status_code, range(8)))

    assert statuses.count(201) == 1
    assert statuses.count(409) == 7
    assert len(_payment_rows(invoice_id)) == 1


# ── Listing and totals ──────────────────────────────────────────────────────

def test_status_filter_includes_partial_and_rejects_unknown_values(client, student_id, invoice_id):
    _pay(client, invoice_id, amount_paid=100)

    rows = client.get("/fees", params={"status": "partial", "student_id": student_id}).json()

    assert [row["id"] for row in rows] == [invoice_id]
    assert client.get("/fees", params={"status": "banana"}).status_code == 422


def test_due_date_in_the_past_marks_an_open_invoice_overdue_but_not_a_settled_one(client, student_id):
    yesterday = (date.today() - timedelta(days=2)).isoformat()
    open_id = _generate(client, student_id, due_date=yesterday).json()["invoice_id"]
    settled_id = _generate(client, student_id, due_date=yesterday).json()["invoice_id"]
    future_id = _generate(client, student_id, due_date="2099-01-10").json()["invoice_id"]
    _pay(client, settled_id)

    assert _invoice(client, student_id, open_id)["is_overdue"] is True
    assert _invoice(client, student_id, settled_id)["is_overdue"] is False
    assert _invoice(client, student_id, future_id)["is_overdue"] is False


def _database_totals():
    connection = sqlite3.connect(engine.url.database)
    collected = connection.execute("select coalesce(sum(amount_paid), 0) from payments").fetchone()[0]
    invoiced = connection.execute("select coalesce(sum(amount), 0) from invoices").fetchone()[0]
    connection.close()
    return round(invoiced, 2), round(collected, 2)


def test_every_screen_reports_the_same_money_and_it_matches_the_payments_table(client, student_id, invoice_id):
    _pay(client, invoice_id, amount_paid=1234)
    invoiced, collected = _database_totals()
    outstanding = round(invoiced - collected, 2)

    summary = client.get("/fees/summary").json()
    kpis = client.get("/dashboard/stats").json()["kpis"]
    with Session(engine) as session:
        chatbot = SchoolDataAssistant(session).get_collection_summary()

    assert (summary["invoiced"], summary["collected"], summary["outstanding"]) == (invoiced, collected, outstanding)
    assert (kpis["total_collected"], kpis["total_pending"]) == (collected, outstanding)
    assert (chatbot["invoiced"], chatbot["paid"], chatbot["pending"]) == (invoiced, collected, outstanding)
    assert summary["collection_rate"] == kpis["collection_rate"] == chatbot["collection_rate"]


def test_summary_does_not_depend_on_any_filter_and_reports_overdue(client):
    summary = client.get("/fees/summary").json()

    assert summary["overdue"] <= summary["outstanding"]
    assert summary["invoice_count"] == len(client.get("/fees").json())


def test_chatbot_uses_real_balances_for_a_part_paid_student(client, student_id, invoice_id):
    _pay(client, invoice_id, amount_paid=1500)
    with Session(engine) as session:
        assistant = SchoolDataAssistant(session)
        roster = assistant.get_students_with_pending_fees()
        row = next(item for item in roster["students"] if item["id"] == student_id)

    assert row["pending_amount"] == 2500
    assert row["pending_invoices"] == 1


def test_challan_pdf_opens_for_a_part_paid_invoice(client, invoice_id):
    _pay(client, invoice_id, amount_paid=1500)

    response = client.get(f"/fees/{invoice_id}/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


# ── Calculation rules ───────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "amount, paid, status, balance",
    [
        (4000, 0, "pending", 4000),
        (4000, 1, "partial", 3999),
        (4000, 4000, "paid", 0),
        (4000, 9000, "paid", 0),  # Old over-recorded data must never show a negative balance.
    ],
)
def test_status_and_balance_rules(amount, paid, status, balance):
    assert payment_status(amount, paid) == status
    assert outstanding_balance(amount, paid) == balance


@pytest.mark.parametrize(
    "text, expected",
    [("10-Oct-2025", date(2025, 10, 10)), ("2025-10-10", date(2025, 10, 10)), ("??", None), ("", None)],
)
def test_due_date_parsing_tolerates_old_free_text(text, expected):
    assert parse_due_date(text) == expected


def test_unreadable_due_date_is_never_called_overdue():
    assert is_overdue("pending", "??", date(2030, 1, 1)) is False


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-q"]))
