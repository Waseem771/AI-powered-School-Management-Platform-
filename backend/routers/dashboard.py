from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func
from typing import Dict, Any
from database import get_session
from models.student import Student
from models.fee import Invoice, Payment
from models.result import Result
from services.ai_service import ai_service
from routers.auth import get_current_user
from config import GRADES, SUBJECTS

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/stats")
def get_dashboard_stats(
    session: Session = Depends(get_session),
    _user = Depends(get_current_user)
):
    # Total students
    students = session.exec(select(Student)).all()
    total_students = len(students)

    # Invoices & Fees
    invoices = session.exec(select(Invoice)).all()
    total_invoiced = sum(inv.amount for inv in invoices)
    total_paid = sum(inv.amount for inv in invoices if inv.status == "paid")
    total_pending = sum(inv.amount for inv in invoices if inv.status == "pending")

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

    # Subject performance averages
    results = session.exec(select(Result)).all()
    subject_marks: Dict[str, list] = {subj: [] for subj in SUBJECTS}
    for r in results:
        if r.subject in subject_marks:
            subject_marks[r.subject].append((r.marks_obtained / r.total_marks) * 100 if r.total_marks > 0 else 0)

    subject_performance = []
    for subj, marks in subject_marks.items():
        avg_score = round(sum(marks) / len(marks), 1) if marks else 70.0
        subject_performance.append({
            "subject": subj,
            "average": avg_score
        })

    # At-risk students count calculation
    high_risk_count = 0
    medium_risk_count = 0
    low_risk_count = 0

    student_results_map = {}
    for r in results:
        student_results_map.setdefault(r.student_id, []).append(r)

    student_invoices_map = {}
    for inv in invoices:
        student_invoices_map.setdefault(inv.student_id, []).append(inv)

    for s in students:
        s_res = student_results_map.get(s.id, [])
        s_inv = student_invoices_map.get(s.id, [])

        avg_marks = (sum(r.marks_obtained for r in s_res) / (len(s_res) * 100) * 100) if s_res else 70.0
        failing = sum(1 for r in s_res if r.marks_obtained < 40)
        fee_defs = sum(1 for inv in s_inv if inv.status == "pending")
        trend = -15.0 if failing >= 2 else (5.0 if avg_marks > 80 else 0.0)

        risk_data = ai_service.predict_student_risk({
            "avg_marks_pct": avg_marks,
            "fee_defaults": fee_defs,
            "failing_subjects": failing,
            "grade_trend": trend
        })

        cat = risk_data.get("risk_category")
        if cat == "High":
            high_risk_count += 1
        elif cat == "Medium":
            medium_risk_count += 1
        else:
            low_risk_count += 1

    return {
        "kpis": {
            "total_students": total_students,
            "total_collected": total_paid,
            "total_pending": total_pending,
            "at_risk_students": high_risk_count,
            "medium_risk_students": medium_risk_count,
            "low_risk_students": low_risk_count,
            "collection_rate": round((total_paid / total_invoiced * 100), 1) if total_invoiced > 0 else 0
        },
        "grade_distribution": grade_distribution,
        "fee_summary": [
            {"name": "Collected", "value": total_paid, "color": "#10B981"},
            {"name": "Pending Dues", "value": total_pending, "color": "#EF4444"}
        ],
        "risk_breakdown": [
            {"category": "High Risk (>70%)", "count": high_risk_count, "fill": "#EF4444"},
            {"category": "Medium Risk (40-70%)", "count": medium_risk_count, "fill": "#F59E0B"},
            {"category": "Low Risk (<40%)", "count": low_risk_count, "fill": "#10B981"}
        ],
        "subject_performance": subject_performance
    }
