"""Marks and report cards: nothing is stated that the recorded marks do not support."""
import uuid

import pytest
from fastapi.testclient import TestClient
from reportlab import rl_config
from sqlmodel import Session, select

from config import SUBJECTS
from database import engine
from main import app
from models.fee import AcademicYear
from models.result import Result
from services.academics import latest_exam_marks, promotion_decision
from services.data_assistant_service import SchoolDataAssistant
from services.pdf_service import generate_report_card_pdf
from services.risk_features import compute_student_features


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def headers(client, admin_password):
    response = client.post("/auth/login", json={"username": "admin", "password": admin_password})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def student_id(client, headers):
    response = client.post(
        "/students",
        headers=headers,
        json={
            "name": "Hina Soomro",
            "roll_number": f"R{uuid.uuid4().hex[:8]}",
            "grade": "Grade 8",
            "section": "A",
            "guardian_name": "Akbar Soomro",
            "phone": "0301-2345678",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _enter(client, headers, student_id, subject="English", marks=70, total=100, exam="Final Term"):
    return client.post(
        "/results",
        headers=headers,
        json={
            "student_id": student_id,
            "subject": subject,
            "marks_obtained": marks,
            "total_marks": total,
            "exam_type": exam,
        },
    )


def _enter_all(client, headers, student_id, marks, exam="Final Term"):
    for subject, value in zip(SUBJECTS, marks):
        assert _enter(client, headers, student_id, subject, value, exam=exam).status_code == 200


def _rows(*marks, exam="Final Term", year=1, subjects=SUBJECTS):
    return [
        Result(student_id=1, subject=subject, marks_obtained=value, exam_type=exam, academic_year_id=year)
        for subject, value in zip(subjects, marks)
    ]


# ── Marks validation ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "changes",
    [
        {"marks": 150},
        {"marks": 101},
        {"marks": -5},
        {"total": 0},
        {"total": -100},
        {"total": 1001},
        {"subject": "Basket Weaving"},
        {"subject": ""},
        {"exam": "Pizza Test"},
    ],
)
def test_invalid_marks_are_rejected_and_not_saved(client, headers, student_id, changes):
    response = _enter(client, headers, student_id, **changes)

    assert response.status_code == 422, response.text
    assert client.get(f"/results/{student_id}", headers=headers).json()["results"] == []


def test_non_finite_marks_are_rejected(client, headers, student_id):
    response = client.post(
        "/results",
        headers={**headers, "Content-Type": "application/json"},
        content=f'{{"student_id": {student_id}, "subject": "English", "marks_obtained": NaN}}',
    )

    assert response.status_code == 422


def test_marks_on_the_boundaries_are_accepted(client, headers, student_id):
    assert _enter(client, headers, student_id, "English", 0).status_code == 200
    assert _enter(client, headers, student_id, "Urdu", 100).status_code == 200
    assert _enter(client, headers, student_id, "Science", 37.5, total=50).status_code == 200


def test_unknown_student_is_404(client, headers):
    assert _enter(client, headers, 999999).status_code == 404


def test_archived_student_gets_no_new_marks_but_keeps_old_ones(client, headers, student_id):
    _enter(client, headers, student_id, "English", 70)
    client.post(f"/students/{student_id}/archive", headers=headers)

    response = _enter(client, headers, student_id, "Urdu", 70)

    assert response.status_code == 409
    assert "archived" in response.json()["detail"]
    assert len(client.get(f"/results/{student_id}", headers=headers).json()["results"]) == 1


def test_entering_marks_twice_updates_instead_of_duplicating(client, headers, student_id):
    _enter(client, headers, student_id, "English", 50)
    _enter(client, headers, student_id, "English", 75)

    rows = client.get(f"/results/{student_id}", headers=headers).json()["results"]

    assert [row["marks_obtained"] for row in rows] == [75]


def test_new_marks_are_stamped_with_the_current_year(client, headers, student_id):
    _enter(client, headers, student_id)

    with Session(engine) as session:
        current = session.exec(select(AcademicYear).where(AcademicYear.is_current == True)).first()  # noqa: E712
        row = session.exec(select(Result).where(Result.student_id == student_id)).first()

    assert row.academic_year_id == current.id


# ── Exam separation ──────────────────────────────────────────────────────────


def test_midterm_and_final_are_never_added_together(client, headers, student_id):
    _enter_all(client, headers, student_id, [60] * 6, exam="Midterm")
    _enter_all(client, headers, student_id, [80] * 6, exam="Final Term")

    final = client.get(f"/results/{student_id}", headers=headers, params={"exam_type": "Final Term"}).json()
    midterm = client.get(f"/results/{student_id}", headers=headers, params={"exam_type": "Midterm"}).json()

    assert final["summary"]["total_obtained"] == 480
    assert final["summary"]["total_max"] == 600
    assert final["summary"]["percentage"] == 80
    assert midterm["summary"]["total_obtained"] == 360
    assert midterm["summary"]["percentage"] == 60
    assert {row["exam_type"] for row in final["results"]} == {"Final Term"}


def test_default_view_is_the_latest_exam_and_lists_the_others(client, headers, student_id):
    _enter_all(client, headers, student_id, [60] * 6, exam="Midterm")
    only_midterm = client.get(f"/results/{student_id}", headers=headers).json()
    assert only_midterm["exam"]["exam_type"] == "Midterm"

    _enter_all(client, headers, student_id, [80] * 6, exam="Final Term")
    both = client.get(f"/results/{student_id}", headers=headers).json()

    assert both["exam"]["exam_type"] == "Final Term"
    assert both["exam"]["session"] == "2025-2026"
    assert [exam["exam_type"] for exam in both["available_exams"]] == ["Final Term", "Midterm"]


def test_academic_years_are_kept_apart(client, headers, student_id):
    _enter(client, headers, student_id, "English", 80)
    with Session(engine) as session:
        session.add(Result(student_id=student_id, subject="English", marks_obtained=30, academic_year_id=99))
        session.commit()

    current = client.get(f"/results/{student_id}", headers=headers, params={"academic_year_id": 1}).json()
    old = client.get(f"/results/{student_id}", headers=headers, params={"academic_year_id": 99}).json()

    assert [row["marks_obtained"] for row in current["results"]] == [80]
    assert [row["marks_obtained"] for row in old["results"]] == [30]
    assert len(current["available_exams"]) == 2


def test_invalid_exam_filter_is_rejected(client, headers, student_id):
    response = client.get(f"/results/{student_id}", headers=headers, params={"exam_type": "Pizza Test"})
    assert response.status_code == 422


def test_student_with_no_marks_has_no_grade_and_no_promotion(client, headers, student_id):
    body = client.get(f"/results/{student_id}", headers=headers).json()

    assert body["results"] == []
    assert body["summary"]["grade"] == "N/A"
    assert body["exam"] is None
    assert body["promotion"]["status"] == "no_marks"


# ── Promotion policy ─────────────────────────────────────────────────────────


def test_all_six_passed_with_50_percent_is_promoted():
    decision = promotion_decision(_rows(50, 50, 50, 50, 50, 50))
    assert decision["status"] == "promoted"
    assert decision["subjects_passed"] == 6


def test_one_failed_subject_is_still_promoted_when_aggregate_holds():
    decision = promotion_decision(_rows(30, 60, 60, 60, 60, 60))
    assert decision["status"] == "promoted"
    assert decision["subjects_passed"] == 5


def test_two_failed_subjects_are_not_promoted_even_with_a_high_aggregate():
    """The old rule promoted this student, because the overall grade was not F."""
    decision = promotion_decision(_rows(30, 30, 95, 95, 95, 95))
    assert decision["status"] == "not_promoted"
    assert decision["retake_eligible"] is True
    assert any("5 of 6" in reason for reason in decision["reasons"])


def test_three_failed_subjects_are_not_eligible_for_a_retake():
    decision = promotion_decision(_rows(30, 30, 30, 95, 95, 95))
    assert decision["status"] == "not_promoted"
    assert decision["retake_eligible"] is False


def test_all_passed_but_aggregate_below_50_is_not_promoted():
    decision = promotion_decision(_rows(45, 45, 45, 45, 45, 45))
    assert decision["status"] == "not_promoted"
    assert decision["subjects_passed"] == 6
    assert decision["retake_eligible"] is False
    assert any("50%" in reason for reason in decision["reasons"])


def test_aggregate_just_under_50_is_not_rounded_up():
    decision = promotion_decision(_rows(49.9, 50, 50, 50, 50, 50))
    assert decision["status"] == "not_promoted"


def test_missing_subject_means_no_decision():
    decision = promotion_decision(_rows(90, 90, 90, 90, 90))
    assert decision["status"] == "incomplete"
    assert "Pakistan Studies" in decision["label"]


def test_midterm_never_decides_promotion():
    decision = promotion_decision(_rows(90, 90, 90, 90, 90, 90, exam="Midterm"))
    assert decision["status"] == "not_applicable"


def test_no_marks_means_no_decision():
    assert promotion_decision([])["status"] == "no_marks"


def test_subject_pass_uses_percentage_not_raw_marks(client, headers, student_id):
    _enter(client, headers, student_id, "English", 30, total=50)
    _enter(client, headers, student_id, "Urdu", 45, total=200)

    rows = {r["subject"]: r for r in client.get(f"/results/{student_id}", headers=headers).json()["results"]}

    assert rows["English"]["passed"] is True  # 60%, though 30 is below 40
    assert rows["Urdu"]["passed"] is False  # 22.5%, though 45 is above 40


def test_api_returns_the_promotion_decision(client, headers, student_id):
    _enter_all(client, headers, student_id, [30, 30, 95, 95, 95, 95])

    body = client.get(f"/results/{student_id}", headers=headers).json()

    assert body["promotion"]["status"] == "not_promoted"


# ── Report card ──────────────────────────────────────────────────────────────


def _pdf_text(monkeypatch, *args):
    """Without page compression, the text can be searched in the PDF bytes."""
    monkeypatch.setattr(rl_config, "pageCompression", 0)
    return generate_report_card_pdf(*args)


def _capture_report_card(client, headers, monkeypatch, student_id, **params):
    import routers.results as results_router

    captured = {}

    def fake_pdf(student, results, summary, exam, promotion):
        captured.update(student=student, results=results, summary=summary, exam=exam, promotion=promotion)
        return b"%PDF-fake"

    monkeypatch.setattr(results_router, "generate_report_card_pdf", fake_pdf)
    response = client.get(f"/results/{student_id}/report-card/pdf", headers=headers, params=params)
    return response, captured


def test_report_card_with_no_marks_is_refused(client, headers, student_id):
    response = client.get(f"/results/{student_id}/report-card/pdf", headers=headers)

    assert response.status_code == 404
    assert "No marks" in response.json()["detail"]


def test_report_card_covers_one_exam_only(client, headers, monkeypatch, student_id):
    _enter_all(client, headers, student_id, [60] * 6, exam="Midterm")
    _enter_all(client, headers, student_id, [80] * 6, exam="Final Term")

    _, final = _capture_report_card(client, headers, monkeypatch, student_id)
    _, midterm = _capture_report_card(client, headers, monkeypatch, student_id, exam_type="Midterm")

    assert final["exam"]["exam_type"] == "Final Term"
    assert len(final["results"]) == 6
    assert final["summary"]["total_max"] == 600
    assert final["promotion"]["status"] == "promoted"
    assert midterm["exam"]["exam_type"] == "Midterm"
    assert midterm["summary"]["percentage"] == 60
    assert midterm["promotion"]["status"] == "not_applicable"


def test_report_card_does_not_invent_a_date_of_birth(client, headers, monkeypatch, student_id):
    _enter(client, headers, student_id)

    _, captured = _capture_report_card(client, headers, monkeypatch, student_id)

    assert captured["student"]["dob"] == "Not recorded"


def test_report_card_for_an_unknown_exam_is_refused(client, headers, student_id):
    _enter(client, headers, student_id)

    response = client.get(f"/results/{student_id}/report-card/pdf", headers=headers, params={"exam_type": "Midterm"})

    assert response.status_code == 404


def _sample_pdf(monkeypatch, marks, exam_type="Final Term"):
    rows = _rows(*marks, exam=exam_type)
    decision = promotion_decision(rows)
    return _pdf_text(
        monkeypatch,
        {"name": "Hina Soomro", "roll_number": "1", "grade": "Grade 8", "section": "A", "dob": "Not recorded"},
        [{"subject": r.subject, "marks_obtained": r.marks_obtained, "total_marks": 100, "grade": "A"} for r in rows],
        {"total_obtained": sum(marks), "total_max": 100 * len(marks), "percentage": 50.0, "grade": "D"},
        {"exam_type": exam_type, "session": "2025-2026"},
        decision,
    )


def test_pdf_says_not_promoted_when_policy_says_so(monkeypatch):
    pdf = _sample_pdf(monkeypatch, [30, 30, 95, 95, 95, 95])

    assert b"NOT PROMOTED" in pdf
    assert b"PROMOTED TO NEXT" not in pdf


def test_pdf_says_promoted_only_when_policy_says_so(monkeypatch):
    assert b"PROMOTED TO NEXT" in _sample_pdf(monkeypatch, [60] * 6)


def test_pdf_makes_no_promotion_statement_at_midterm(monkeypatch):
    pdf = _sample_pdf(monkeypatch, [60] * 6, exam_type="Midterm")

    assert b"PROMOTED" not in pdf
    assert b"Midterm" in pdf


def test_pdf_has_no_prewritten_teacher_remark(monkeypatch):
    assert b"Consistent effort" not in _sample_pdf(monkeypatch, [60] * 6)


# ── Other readers of marks ───────────────────────────────────────────────────


def test_latest_exam_marks_prefers_newest_year_then_final():
    old_final = _rows(10, exam="Final Term", year=1)
    new_midterm = _rows(20, exam="Midterm", year=2)
    new_final = _rows(30, exam="Final Term", year=2)

    assert latest_exam_marks(old_final + new_midterm) == new_midterm
    assert latest_exam_marks(old_final + new_midterm + new_final) == new_final
    assert latest_exam_marks([]) == []


def test_risk_features_do_not_double_count_two_exams():
    midterm = _rows(30, 30, 30, 30, 30, 30, exam="Midterm")
    final = _rows(90, 90, 90, 90, 90, 90, exam="Final Term")

    features = compute_student_features(midterm + final, [])

    assert features["failing_subjects"] == 0
    assert features["avg_marks_pct"] == 90


def test_chatbot_reports_one_exam_with_the_same_percentage_as_the_results_page(client, headers, student_id):
    _enter(client, headers, student_id, "English", 30, total=50, exam="Final Term")
    _enter(client, headers, student_id, "Urdu", 90, total=100, exam="Final Term")
    _enter(client, headers, student_id, "English", 10, total=100, exam="Midterm")
    page = client.get(f"/results/{student_id}", headers=headers).json()

    with Session(engine) as session:
        roll = client.get(f"/students/{student_id}", headers=headers).json()["roll_number"]
        answer = SchoolDataAssistant(session).get_student_results(roll)

    assert answer["average_percentage"] == page["summary"]["percentage"] == 80
    assert answer["exam_type"] == "Final Term"
    assert len(answer["results"]) == 2


def test_dashboard_leaves_out_subjects_with_no_marks_rather_than_inventing_an_average(client, headers):
    subjects = client.get("/dashboard/stats", headers=headers).json()["subject_performance"]

    assert subjects
    with Session(engine) as session:
        recorded = {row.subject for row in session.exec(select(Result)).all()}
    assert {row["subject"] for row in subjects} <= recorded


def test_marks_table_has_no_duplicates_after_seeding():
    with Session(engine) as session:
        rows = session.exec(select(Result)).all()
    keys = [(r.student_id, r.subject, r.exam_type, r.academic_year_id) for r in rows]
    assert len(keys) == len(set(keys))


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-q"]))
