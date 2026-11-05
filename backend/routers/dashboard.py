from collections import Counter

from fastapi import APIRouter, Depends
from sqlmodel import Session, col, select
from typing import Dict
from database import get_session
from models.student import Student
from models.result import Result
from services.academics import latest_exam_marks, percentage
from services.ai_service import CATEGORY_HIGH, CATEGORY_LOW, CATEGORY_MEDIUM, NOT_ENOUGH_DATA
from routers.auth import get_current_user
from services.fee_ledger import school_totals
from services.risk_assessment import assess_students
from config import GRADES, SUBJECTS

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/stats")
def get_dashboard_stats(
    session: Session = Depends(get_session),
    _user = Depends(get_current_user)
):
    # Total students. Archived students leave these counts, but their fee money still counts below.
    students = session.exec(select(Student).where(col(Student.archived_at).is_(None))).all()
    total_students = len(students)
    active_ids = {s.id for s in students}

    # Invoices & Fees
    fee_totals = school_totals(session)
    total_paid = fee_totals["collected"]
    total_pending = fee_totals["outstanding"]

    # Grade distribution
    grade_counts = {}
    for g in GRADES:
        grade_counts[g] = 0
    for s in students:
        if s.grade in grade_counts:
            grade_counts[s.grade] += 1
        else:
            grade_counts[s.grade] = 1

    grade_distribution = [{"grade": k, "count": v} for k, v in grade_counts.items()]

    # Each active student's marks, from which their latest exam is taken.
    student_results_map = {}
    for r in session.exec(select(Result)).all():
        if r.student_id in active_ids:
            student_results_map.setdefault(r.student_id, []).append(r)

    # Subject performance averages, over each student's latest exam
    subject_marks: Dict[str, list] = {subj: [] for subj in SUBJECTS}
    for student_marks in student_results_map.values():
        for r in latest_exam_marks(student_marks):
            if r.subject in subject_marks:
                subject_marks[r.subject].append(percentage(r.marks_obtained, r.total_marks))

    # A subject with no marks is left out rather than given an invented average.
    subject_performance = [
        {"subject": subj, "average": round(sum(marks) / len(marks), 1)}
        for subj, marks in subject_marks.items()
        if marks
    ]

    # Academic estimates, from the same source as the At-Risk page. Fee follow-up is counted apart.
    assessments = assess_students(session, students).values()
    bands = Counter(row["risk_category"] for row in assessments)
    high_risk_count = bands[CATEGORY_HIGH]
    medium_risk_count = bands[CATEGORY_MEDIUM]
    low_risk_count = bands[CATEGORY_LOW]
    not_enough_data_count = bands[NOT_ENOUGH_DATA]

    return {
        "kpis": {
            "total_students": total_students,
            "total_collected": total_paid,
            "total_pending": total_pending,
            "at_risk_students": high_risk_count,
            "medium_risk_students": medium_risk_count,
            "low_risk_students": low_risk_count,
            "not_enough_data_students": not_enough_data_count,
            "fee_follow_up_students": sum(row["fee_follow_up"]["needed"] for row in assessments),
            "total_overdue": fee_totals["overdue"],
            "collection_rate": fee_totals["collection_rate"]
        },
        "grade_distribution": grade_distribution,
        "fee_summary": [
            {"name": "Collected", "value": total_paid, "color": "#10B981"},
            {"name": "Pending Dues", "value": total_pending, "color": "#EF4444"}
        ],
        "risk_breakdown": [
            {"category": CATEGORY_HIGH, "count": high_risk_count, "fill": "#EF4444"},
            {"category": CATEGORY_MEDIUM, "count": medium_risk_count, "fill": "#F59E0B"},
            {"category": CATEGORY_LOW, "count": low_risk_count, "fill": "#10B981"},
            {"category": NOT_ENOUGH_DATA, "count": not_enough_data_count, "fill": "#94A3B8"}
        ],
        "subject_performance": subject_performance
    }
