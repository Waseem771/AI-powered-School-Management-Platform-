"""Risk estimates for real students, shared by the At-Risk page, dashboard, and chatbot.

The academic estimate and the fee follow-up flag sit side by side here. Neither feeds the other.
"""
from typing import Any, Dict, List, Sequence

from sqlmodel import Session, col, select

from models.result import Result
from models.student import Student
from services.ai_service import ai_service
from services.fee_ledger import fee_follow_ups
from services.risk_features import compute_student_features

_REVIEW_AVERAGE_BELOW = 60
_REVIEW_FALL_OVER = 10


def _marks_by_student(session: Session, student_ids: Sequence[int]) -> Dict[int, List[Result]]:
    grouped: Dict[int, List[Result]] = {student_id: [] for student_id in student_ids}
    for mark in session.exec(select(Result).where(col(Result.student_id).in_(list(student_ids)))).all():
        grouped[mark.student_id].append(mark)
    return grouped


def assess_students(session: Session, students: Sequence[Student]) -> Dict[int, Dict[str, Any]]:
    """Each student's score and fee flag, without explanations, which belong to the one-student view."""
    ids = [student.id for student in students]
    if not ids:
        return {}
    marks = _marks_by_student(session, ids)
    follow_ups = fee_follow_ups(session, ids)
    scores = ai_service.predict_many([compute_student_features(marks[student_id]) for student_id in ids])
    return {
        student_id: {**score, "fee_follow_up": follow_ups[student_id]}
        for student_id, score in zip(ids, scores)
    }


def assess_student(session: Session, student: Student) -> Dict[str, Any]:
    """One student's score with its explanation, and their fee flag."""
    marks = _marks_by_student(session, [student.id])[student.id]
    return {
        **ai_service.predict_student_risk(compute_student_features(marks)),
        "fee_follow_up": fee_follow_ups(session, [student.id])[student.id],
    }


def suggested_steps(metrics: Dict[str, Any]) -> List[str]:
    """Steps for staff to consider, each following from a fact in the student's marks."""
    if metrics["avg_marks_pct"] is None or metrics["subjects_counted"] is None:
        return ["Enter this student's exam marks to get an estimate."]
    steps = []
    if metrics["failing_subjects"] > 0:
        steps.append("Consider extra teaching support in the failed subjects.")
    if metrics["avg_marks_pct"] < _REVIEW_AVERAGE_BELOW:
        steps.append("Consider a progress review with the subject teachers.")
    if metrics["grade_trend"] is not None and metrics["grade_trend"] < -_REVIEW_FALL_OVER:
        steps.append("Consider talking with the student about what changed since the midterm.")
    return steps or ["No extra step is suggested by these marks."]
