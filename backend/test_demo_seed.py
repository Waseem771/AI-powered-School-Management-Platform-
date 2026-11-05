"""The demo school: safe to build, clearly fictional, and holding what SAMPLE_DEMO_SCENARIO.md promises."""
from collections import Counter
from datetime import date

import pytest
from sqlmodel import Session, create_engine, select

from models.fee import AcademicYear, Invoice, Payment
from models.result import Result
from models.student import Student, StudentCreate
from models.user import User, verify_password
from seed_demo import DEMO_ADMIN_USERNAME, academic_session, build_demo_database
from services.academics import exam_trend
from services.ai_service import NOT_ENOUGH_DATA
from services.fee_ledger import paid_by_invoice, payment_status, school_totals
from services.risk_assessment import assess_students
from services.school_assistant_service import SchoolAssistantService

TODAY = date(2026, 11, 5)
PASSWORD = "demo-test-password-1"
# Names from the older seed that belong to real public figures.
PUBLIC_FIGURES = {"Babar Azam", "Wasim Akram", "Waqar Younis", "Shoaib Akhtar", "Maryam Nawaz", "Sana Mir", "Iqra Aziz", "Mian Mansha", "Yumna Zaidi", "Hania Amir"}


@pytest.fixture(scope="module")
def session(tmp_path_factory):
    path = tmp_path_factory.mktemp("demo") / "demo.db"
    build_demo_database(path, TODAY, PASSWORD)
    engine = create_engine(f"sqlite:///{path.as_posix()}")
    with Session(engine) as db:
        yield db
    engine.dispose()


def _by_roll(session, roll):
    return session.exec(select(Student).where(Student.roll_number == roll)).one()


def _ask(session, question, history=None):
    return SchoolAssistantService(session).answer(question, history=history)


# ── Safety ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("name", ["school.db", "production.db", "copy.db"])
def test_refuses_any_file_not_named_as_a_demo(tmp_path, name):
    with pytest.raises(ValueError, match="demo"):
        build_demo_database(tmp_path / name, TODAY, PASSWORD)
    assert not (tmp_path / name).exists()


def test_refuses_to_overwrite_without_being_asked(tmp_path):
    path = tmp_path / "demo.db"
    path.write_bytes(b"existing")

    with pytest.raises(FileExistsError):
        build_demo_database(path, TODAY, PASSWORD)

    assert path.read_bytes() == b"existing"


def test_replacing_a_demo_database_works(tmp_path):
    path = tmp_path / "demo.db"
    build_demo_database(path, TODAY, PASSWORD)

    assert build_demo_database(path, TODAY, PASSWORD, replace=True)["students"] == 120


def test_building_does_not_touch_the_apps_own_database(tmp_path):
    from database import engine

    def everything():
        with Session(engine) as app_session:
            return len(app_session.exec(select(Student)).all()), len(app_session.exec(select(Invoice)).all())

    before = everything()
    build_demo_database(tmp_path / "demo.db", TODAY, PASSWORD)

    assert everything() == before


def test_the_same_day_builds_the_same_data(tmp_path):
    first = build_demo_database(tmp_path / "demo_one.db", TODAY, PASSWORD)
    second = build_demo_database(tmp_path / "demo_two.db", TODAY, PASSWORD)

    assert first == second


def test_the_admin_password_is_the_one_given_and_not_in_the_database_as_text(session):
    admin = session.exec(select(User).where(User.username == DEMO_ADMIN_USERNAME)).one()

    assert verify_password(PASSWORD, admin.password_hash)
    assert PASSWORD not in admin.password_hash


# ── Fictional, and valid ──────────────────────────────────────────────────────

def test_enough_students_in_every_class(session):
    students = session.exec(select(Student)).all()
    per_class = Counter((student.grade, student.section) for student in students)

    assert len(students) == 120
    assert len(per_class) == 10
    assert set(per_class.values()) == {12}


def test_every_student_passes_the_apps_own_validation(session):
    for student in session.exec(select(Student)).all():
        StudentCreate(
            name=student.name, roll_number=student.roll_number, grade=student.grade, section=student.section,
            guardian_name=student.guardian_name, phone=student.phone, dob=student.dob,
        )


def test_no_public_figures(session):
    students = session.exec(select(Student)).all()
    names = {student.name for student in students} | {student.guardian_name for student in students}

    assert not names & PUBLIC_FIGURES


def test_phone_numbers_cannot_reach_a_real_person(session):
    # 0999 is not a Pakistani mobile or Khairpur prefix.
    assert all(student.phone.startswith("0999-") for student in session.exec(select(Student)).all())


def test_only_the_planned_pair_share_a_name(session):
    names = Counter(student.name for student in session.exec(select(Student)).all())

    assert {name for name, count in names.items() if count > 1} == {"Ali Junejo"}


# ── Current dates ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("today, label", [
    (date(2026, 11, 5), "2026-2027"),
    (date(2027, 3, 1), "2026-2027"),
    (date(2027, 8, 1), "2027-2028"),
])
def test_academic_session_follows_the_date(today, label):
    assert academic_session(today) == label


def test_current_session_and_months_follow_the_build_date(session):
    year = session.exec(select(AcademicYear).where(AcademicYear.is_current == True)).one()  # noqa: E712
    months = {invoice.month for invoice in session.exec(select(Invoice)).all()}

    assert year.label == "2026-2027"
    assert months == {"September 2026", "October 2026", "November 2026"}


def test_nothing_is_dated_after_the_build_date(session):
    assert all(payment.paid_at.date() <= TODAY for payment in session.exec(select(Payment)).all())
    assert all(student.created_at.date() <= TODAY for student in session.exec(select(Student)).all())


def test_a_build_early_in_a_year_rolls_back_across_it(tmp_path):
    build_demo_database(tmp_path / "demo.db", date(2027, 1, 15), PASSWORD)
    engine = create_engine(f"sqlite:///{(tmp_path / 'demo.db').as_posix()}")
    with Session(engine) as db:
        months = {invoice.month for invoice in db.exec(select(Invoice)).all()}
    engine.dispose()

    assert months == {"November 2026", "December 2026", "January 2027"}


# ── Money ─────────────────────────────────────────────────────────────────────

def test_every_status_matches_its_payments(session):
    paid = paid_by_invoice(session)

    for invoice in session.exec(select(Invoice)).all():
        assert invoice.status == payment_status(invoice.amount, paid.get(invoice.id, 0.0))


def test_fee_records_have_every_status_and_real_totals(session):
    statuses = Counter(invoice.status for invoice in session.exec(select(Invoice)).all())
    totals = school_totals(session, TODAY)

    assert statuses["paid"] > statuses["pending"] > 0
    assert statuses["partial"] > 0
    assert 0 < totals["collection_rate"] < 100
    assert totals["overdue"] > 0


def test_a_payment_can_come_in_more_than_one_part(session):
    per_invoice = Counter(payment.invoice_id for payment in session.exec(select(Payment)).all())

    assert max(per_invoice.values()) >= 2


def test_challan_numbers_are_unique(session):
    numbers = [invoice.challan_number for invoice in session.exec(select(Invoice)).all()]

    assert len(numbers) == len(set(numbers))


# ── Marks and estimates ───────────────────────────────────────────────────────

def test_two_exams_for_nearly_everyone(session):
    marks = session.exec(select(Result)).all()
    exams = Counter((mark.student_id, mark.exam_type) for mark in marks)

    assert {kind for _, kind in exams} == {"Midterm", "Final Term"}
    assert all(count == 6 for count in exams.values())


def test_a_realistic_spread_of_estimates(session):
    students = session.exec(select(Student).where(Student.archived_at == None)).all()  # noqa: E711
    bands = Counter(row["risk_category"] for row in assess_students(session, students).values())

    assert bands["Low"] > bands["Medium"] > 0
    assert bands["Low"] > bands["High"] > 0
    assert bands["Medium"] >= 5
    assert bands["High"] >= 5
    assert bands[NOT_ENOUGH_DATA] >= 1


def test_real_trends_exist_in_both_directions(session):
    marks = session.exec(select(Result)).all()
    by_student = {}
    for mark in marks:
        by_student.setdefault(mark.student_id, []).append(mark)
    trends = [exam_trend(rows) for rows in by_student.values()]

    assert any(trend is not None and trend < -10 for trend in trends)
    assert any(trend is not None and trend > 0 for trend in trends)


def test_fee_problems_are_not_tied_to_weak_marks(session):
    """Overdue fees appear among strong students too, so the demo shows the two are separate."""
    students = session.exec(select(Student).where(Student.archived_at == None)).all()  # noqa: E711
    rows = assess_students(session, students).values()

    assert any(row["risk_category"] == "Low" and row["fee_follow_up"]["needed"] for row in rows)
    assert any(row["risk_category"] == "High" and not row["fee_follow_up"]["needed"] for row in rows)


# ── What SAMPLE_DEMO_SCENARIO.md promises ─────────────────────────────────────

def test_scenario_part_paid_student_for_the_payment_step(session):
    student = _by_roll(session, "801")
    invoices = session.exec(select(Invoice).where(Invoice.student_id == student.id)).all()

    assert student.name == "Hina Soomro"
    assert (student.grade, student.section) == ("Grade 8", "A")
    assert any(invoice.status == "partial" for invoice in invoices)


def test_scenario_high_estimate_comes_from_a_real_fall(session):
    student = _by_roll(session, "901")
    row = assess_students(session, [student])[student.id]

    assert student.name == "Danish Memon"
    assert row["risk_category"] == "High"
    assert row["metrics"]["grade_trend"] < -10
    assert row["fee_follow_up"]["needed"] is False


def test_scenario_medium_estimate(session):
    student = _by_roll(session, "751")

    assert student.name == "Sara Abro"
    assert assess_students(session, [student])[student.id]["risk_category"] == "Medium"


def test_scenario_strong_student_with_overdue_fees(session):
    student = _by_roll(session, "1001")
    row = assess_students(session, [student])[student.id]

    assert student.name == "Maham Shaikh"
    assert row["risk_category"] == "Low"
    assert row["fee_follow_up"]["needed"] is True


def test_scenario_new_student_has_no_estimate(session):
    student = _by_roll(session, "651")

    assert student.name == "Kiran Mangi"
    assert assess_students(session, [student])[student.id]["risk_category"] == NOT_ENOUGH_DATA


def test_scenario_urdu_name_prints_and_archived_student_exists(session):
    from services.receipts import generate_receipt_pdf, receipt_details

    urdu = _by_roll(session, "701")
    archived = _by_roll(session, "852")
    invoice = session.exec(select(Invoice).where(Invoice.student_id == urdu.id)).first()
    payment = session.exec(select(Payment).where(Payment.invoice_id == invoice.id)).first()

    assert urdu.name == "محمد علی"
    assert generate_receipt_pdf(receipt_details(session, payment.id)).startswith(b"%PDF")
    assert archived.archived_at is not None
    assert session.exec(select(Invoice).where(Invoice.student_id == archived.id)).first()


def test_scenario_chatbot_questions(session):
    fees = _ask(session, "Fees for roll number 801")
    same_name = _ask(session, "Fees of Ali Junejo")
    count = _ask(session, "How many students are there?")
    at_risk = _ask(session, "Which students are at risk?")
    policy = _ask(session, "What is the fee refund policy?")
    outside = _ask(session, "What is the capital of France?")

    assert "Hina Soomro" in fees["answer"]
    assert "802" in same_name["answer"] and "1051" in same_name["answer"]
    assert "119 current" in count["answer"] and "1 archived" in count["answer"]
    assert at_risk["tools_used"] == ["get_at_risk_students"]
    assert policy["mode"] == "policy_rag" and policy["grounded"] is True
    assert outside["grounded"] is False


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-q"]))
