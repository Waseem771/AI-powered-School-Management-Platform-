"""Honest risk estimates: marks only, real SHAP explanations, no invented data, fees kept apart."""
from datetime import date

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine

from conftest import TEST_ADMIN_PASSWORD
from main import app
from models.fee import Invoice, Payment
from models.result import Result
from models.student import Student
from services import ai_service as ai_module
from services.academics import exam_trend
from services.ai_service import NOT_ENOUGH_DATA, ai_service
from services.fee_ledger import fee_follow_ups
from services.risk_assessment import assess_student, assess_students
from services.risk_features import MIN_SUBJECTS_FOR_ESTIMATE, compute_student_features

SUBJECTS = ["English", "Urdu", "Mathematics", "Science", "Islamiat", "Pakistan Studies"]


def _exam(student_id, marks, exam_type="Final Term", year=1, subjects=SUBJECTS):
    return [
        Result(student_id=student_id, subject=subject, marks_obtained=mark, total_marks=100, exam_type=exam_type, academic_year_id=year)
        for subject, mark in zip(subjects, marks)
    ]


def _features(avg, failing=0, trend=None):
    return {"avg_marks_pct": avg, "failing_subjects": failing, "grade_trend": trend, "subjects_counted": 6, "has_enough_marks": True}


@pytest.fixture()
def session():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        yield db


def _add_student(session, student_id, marks=()):
    session.add(Student(id=student_id, name=f"Student {student_id}", roll_number=str(student_id), grade="Grade 8", section="A", guardian_name="Guardian", phone="03001234567"))
    session.add_all(list(marks))
    session.commit()
    return session.get(Student, student_id)


def _add_invoice(session, invoice_id, student_id, due="10-Jan-2026", amount=3500, status="pending", paid=0):
    session.add(Invoice(id=invoice_id, student_id=student_id, amount=amount, month=f"Month {invoice_id}", due_date=due, challan_number=f"CHN-{invoice_id}", status=status))
    if paid:
        session.add(Payment(invoice_id=invoice_id, amount_paid=paid))
    session.commit()


# ── Fees never touch the academic estimate ────────────────────────────────────

def test_the_model_has_no_fee_input():
    for model in ai_service.models.values():
        assert not [name for name in model.features if "fee" in name]


def test_unpaid_fees_do_not_change_a_students_estimate(session):
    student = _add_student(session, 1, _exam(1, [85, 85, 85, 85, 85, 85]))
    before = assess_student(session, student)

    for invoice_id in range(1, 6):
        _add_invoice(session, invoice_id, 1)
    after = assess_student(session, student)

    assert after["risk_score"] == before["risk_score"]
    assert after["risk_category"] == before["risk_category"] == "Low"
    assert "fee" not in " ".join(after["top_reasons"]).lower()


def test_fee_follow_up_is_a_separate_flag(session):
    student = _add_student(session, 1, _exam(1, [85, 85, 85, 85, 85, 85]))
    _add_invoice(session, 1, 1, amount=3500, paid=1000, status="partial")
    _add_invoice(session, 2, 1, amount=4000)
    _add_invoice(session, 3, 1, due="10-Dec-2099", amount=9000)

    row = assess_students(session, [student])[1]

    assert row["fee_follow_up"] == {"needed": True, "overdue_invoices": 2, "overdue_amount": 6500}
    assert "fee_defaults" not in row["metrics"]


def test_no_overdue_invoices_means_no_follow_up(session):
    _add_student(session, 1)
    _add_invoice(session, 1, 1, due="10-Dec-2099")
    _add_invoice(session, 2, 1, status="paid", paid=3500)

    assert fee_follow_ups(session, [1], date(2026, 11, 5))[1] == {"needed": False, "overdue_invoices": 0, "overdue_amount": 0}


# ── Not enough data ───────────────────────────────────────────────────────────

def test_no_marks_gives_no_score_rather_than_an_invented_average(session):
    student = _add_student(session, 1)

    row = assess_student(session, student)

    assert row["risk_score"] is None
    assert row["risk_category"] == NOT_ENOUGH_DATA
    assert row["top_reasons"] == []
    assert row["metrics"]["avg_marks_pct"] is None


def test_too_few_subjects_gives_no_score(session):
    few = SUBJECTS[:MIN_SUBJECTS_FOR_ESTIMATE - 1]
    student = _add_student(session, 1, _exam(1, [100] * len(few), subjects=few))

    assert assess_student(session, student)["risk_category"] == NOT_ENOUGH_DATA


def test_enough_subjects_gives_a_score(session):
    some = SUBJECTS[:MIN_SUBJECTS_FOR_ESTIMATE]
    student = _add_student(session, 1, _exam(1, [80] * len(some), subjects=some))

    row = assess_student(session, student)

    assert row["risk_score"] is not None
    assert row["metrics"]["subjects_counted"] == MIN_SUBJECTS_FOR_ESTIMATE


# ── Trend is real or absent ───────────────────────────────────────────────────

def test_one_exam_has_no_trend():
    marks = _exam(1, [40, 40, 40, 40, 40, 40])

    assert exam_trend(marks) is None
    assert compute_student_features(marks)["grade_trend"] is None


def test_trend_compares_midterm_and_final_of_the_same_year():
    marks = _exam(1, [80] * 6, "Midterm") + _exam(1, [60] * 6, "Final Term")

    assert exam_trend(marks) == -20.0


def test_trend_uses_only_subjects_in_both_exams():
    midterm = _exam(1, [80, 80, 80], "Midterm", subjects=SUBJECTS[:3])
    final = _exam(1, [80, 80, 80, 10, 10, 10], "Final Term")

    assert exam_trend(midterm + final) == 0.0


def test_trend_needs_enough_shared_subjects():
    midterm = _exam(1, [80, 80], "Midterm", subjects=SUBJECTS[:2])
    final = _exam(1, [50] * 6, "Final Term")

    assert exam_trend(midterm + final) is None


def test_exams_of_different_years_are_not_a_trend():
    marks = _exam(1, [80] * 6, "Final Term", year=1) + _exam(1, [40] * 6, "Midterm", year=2)

    assert exam_trend(marks) is None


def test_a_midterm_before_any_final_has_no_trend():
    assert exam_trend(_exam(1, [80] * 6, "Midterm")) is None


def test_no_trend_is_never_described(session):
    student = _add_student(session, 1, _exam(1, [30, 30, 30, 30, 45, 45]))

    row = assess_student(session, student)

    assert row["metrics"]["grade_trend"] is None
    joined = " ".join(row["top_reasons"]).lower()
    assert "dropped" not in joined and "fell" not in joined and "trend" not in joined
    assert "grade_trend" not in {factor["feature"] for factor in row["factors"]}


def test_a_real_fall_can_be_explained(session):
    student = _add_student(session, 1, _exam(1, [85] * 6, "Midterm") + _exam(1, [50] * 6, "Final Term"))

    row = assess_student(session, student)

    assert row["metrics"]["grade_trend"] == -35.0
    assert any("35" in reason and "fell" in reason for reason in row["top_reasons"])


# ── Scores come from the model, and are not overstated ────────────────────────

def test_weak_marks_score_higher_than_strong_marks():
    weak = ai_service.predict_student_risk(_features(35, failing=4))
    middling = ai_service.predict_student_risk(_features(58, failing=1))
    strong = ai_service.predict_student_risk(_features(90))

    assert weak["risk_category"] == "High"
    assert strong["risk_category"] == "Low"
    assert weak["risk_score"] > middling["risk_score"] > strong["risk_score"]


@pytest.mark.parametrize("avg, failing", [(20, 6), (100, 0), (35, 5), (95, 0)])
def test_no_score_ever_claims_certainty(avg, failing):
    score = ai_service.predict_student_risk(_features(avg, failing=failing))["risk_score"]

    assert ai_module.MIN_SCORE <= score <= ai_module.MAX_SCORE
    assert 0 < score < 100


def test_score_is_the_models_output_with_no_hand_written_override():
    features = _features(45, failing=3)
    model = ai_service.models[False]
    probability = model.forest.predict_proba(np.array([[45.0, 3.0]]))[0][1]

    assert ai_service.predict_student_risk(features)["risk_score"] == ai_module._score(probability)


def test_the_same_student_scores_the_same_after_a_restart():
    assert ai_module.AtRiskModelService().predict_student_risk(_features(55, 2))["risk_score"] == ai_service.predict_student_risk(_features(55, 2))["risk_score"]


def test_bulk_scores_match_single_scores():
    features = [_features(35, 4), _features(58, 1), _features(90), _features(50, 1, trend=-20)]

    bulk = ai_service.predict_many(features)

    assert [row["risk_score"] for row in bulk] == [ai_service.predict_student_risk(item)["risk_score"] for item in features]


def test_training_does_not_disturb_other_random_numbers():
    np.random.seed(7)
    expected = np.random.random()
    np.random.seed(7)
    ai_module.AtRiskModelService()

    assert np.random.random() == expected


# ── Explanations are SHAP's ───────────────────────────────────────────────────

@pytest.fixture()
def explaining():
    if ai_service.models[False].explainer is None:
        pytest.skip("SHAP is not available here")


def test_shap_contributions_add_up_to_the_models_output(explaining):
    model = ai_service.models[True]
    row = np.array([[48.0, 2.0, -15.0]])

    contributions = model.contributions(row[0])
    probability = model.forest.predict_proba(row)[0][1]

    assert contributions.sum() + model.base_value == pytest.approx(probability, abs=1e-6)


def test_factors_carry_the_real_shap_impact(explaining):
    row = ai_service.predict_student_risk(_features(48, failing=2, trend=-15))
    contributions = ai_service.models[True].contributions(np.array([48.0, 2.0, -15.0]))

    by_feature = {factor["feature"]: factor for factor in row["factors"]}
    assert row["explanation_method"] == "shap"
    for name, value in zip(ai_service.models[True].features, contributions):
        if name in by_feature:
            assert by_feature[name]["impact"] == round(float(value) * 100)
            assert by_feature[name]["direction"] == ("raises" if value > 0 else "lowers")


def test_factors_are_ranked_by_size_of_effect(explaining):
    factors = ai_service.predict_student_risk(_features(48, failing=2, trend=-15))["factors"]

    sizes = [abs(factor["impact"]) for factor in factors]
    assert sizes == sorted(sizes, reverse=True)


def test_good_marks_are_explained_as_lowering_concern(explaining):
    row = ai_service.predict_student_risk(_features(92))

    assert all(factor["direction"] == "lowers" for factor in row["factors"])
    assert any("92" in reason for reason in row["top_reasons"])


def test_without_shap_it_states_facts_and_says_so(monkeypatch):
    service = ai_module.AtRiskModelService()
    monkeypatch.setattr(service.models[False], "explainer", None)

    row = service.predict_student_risk(_features(48, failing=2))

    assert row["explanation_method"] == "record"
    assert row["factors"] == []
    assert any("2 subjects" in reason for reason in row["top_reasons"])
    assert row["risk_score"] is not None


def test_bulk_does_not_run_shap(monkeypatch):
    service = ai_module.AtRiskModelService()

    def fail(*_args):
        raise AssertionError("SHAP ran during a bulk list")

    for model in service.models.values():
        monkeypatch.setattr(model, "contributions", fail)

    assert service.predict_many([_features(50)])[0]["top_reasons"] == []


# ── The API ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def headers(client):
    token = client.post("/auth/login", json={"username": "admin", "password": TEST_ADMIN_PASSWORD}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_the_list_gives_bands_flags_and_no_contact_details(client, headers):
    rows = client.get("/ai/at-risk", headers=headers).json()

    assert rows
    assert {row["risk_category"] for row in rows} <= {"High", "Medium", "Low", NOT_ENOUGH_DATA}
    for row in rows:
        assert "phone" not in row and "guardian_name" not in row
        assert "needed" in row["fee_follow_up"]
        assert "fee_defaults" not in row["metrics"]


def test_the_list_filters_by_band(client, headers):
    rows = client.get("/ai/at-risk", headers=headers, params={"risk_level": "high"}).json()

    assert all(row["risk_category"] == "High" for row in rows)


def test_the_detail_explains_and_keeps_fees_apart(client, headers):
    rows = client.get("/ai/at-risk", headers=headers).json()
    scored = next(row for row in rows if row["risk_score"] is not None)

    detail = client.get(f"/ai/at-risk/{scored['id']}", headers=headers).json()

    assert detail["risk_assessment"]["top_reasons"]
    assert "Synthetic" in detail["note"] or "synthetic" in detail["note"]
    assert "fee" not in " ".join(detail["recommended_interventions"]).lower()
    assert "needed" in detail["fee_follow_up"]
    assert detail["student"]["phone"]


def test_the_simulator_uses_the_real_model(client, headers):
    response = client.post("/ai/simulate", headers=headers, json={"avg_marks_pct": 45, "failing_subjects": 3, "grade_trend": None})

    assert response.status_code == 200
    assert response.json()["risk_score"] == ai_service.predict_student_risk(_features(45, failing=3))["risk_score"]


@pytest.mark.parametrize("payload", [
    {"avg_marks_pct": 101, "failing_subjects": 0},
    {"avg_marks_pct": -1, "failing_subjects": 0},
    {"avg_marks_pct": 50, "failing_subjects": 7},
    {"avg_marks_pct": 50, "failing_subjects": 0, "grade_trend": 101},
    {"avg_marks_pct": 50, "failing_subjects": 0, "fee_defaults": 3},
])
def test_the_simulator_refuses_bad_or_fee_input(client, headers, payload):
    assert client.post("/ai/simulate", headers=headers, json=payload).status_code == 422


def test_the_simulator_needs_a_login(client):
    assert client.post("/ai/simulate", json={"avg_marks_pct": 50, "failing_subjects": 0}).status_code == 401


def test_dashboard_counts_match_the_list(client, headers):
    kpis = client.get("/dashboard/stats", headers=headers).json()["kpis"]
    rows = client.get("/ai/at-risk", headers=headers).json()

    count = lambda band: sum(row["risk_category"] == band for row in rows)
    assert kpis["at_risk_students"] == count("High")
    assert kpis["medium_risk_students"] == count("Medium")
    assert kpis["low_risk_students"] == count("Low")
    assert kpis["not_enough_data_students"] == count(NOT_ENOUGH_DATA)
    assert kpis["fee_follow_up_students"] == sum(row["fee_follow_up"]["needed"] for row in rows)


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-q"]))
