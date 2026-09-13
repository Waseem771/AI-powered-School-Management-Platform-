from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Dict, Any, Optional
from functools import lru_cache
from database import get_session
from models.student import Student
from models.result import Result
from models.fee import Invoice
from routers.auth import get_current_user

router = APIRouter(prefix="/ai", tags=["AI - At Risk"])

@lru_cache
def get_ai_service():
    from services.ai_service import ai_service
    return ai_service

def _calculate_student_features(student_id: int, session: Session) -> Dict[str, Any]:
    marks = session.exec(select(Result).where(Result.student_id == student_id)).all()
    invoices = session.exec(select(Invoice).where(Invoice.student_id == student_id)).all()

    if marks:
        total_obtained = sum(m.marks_obtained for m in marks)
        total_possible = sum(m.total_marks for m in marks)
        avg_pct = (total_obtained / total_possible) * 100.0 if total_possible > 0 else 70.0
        failing = sum(1 for m in marks if (m.marks_obtained / m.total_marks) < 0.40)
    else:
        avg_pct = 70.0
        failing = 0

    fee_defaults = sum(1 for inv in invoices if inv.status == "pending")

    # Historical trend heuristic
    if failing >= 2:
        grade_trend = -21.0
    elif avg_pct < 55:
        grade_trend = -14.5
    elif avg_pct > 80:
        grade_trend = 6.5
    else:
        grade_trend = 1.0

    return {
        "avg_marks_pct": avg_pct,
        "fee_defaults": fee_defaults,
        "failing_subjects": failing,
        "grade_trend": grade_trend
    }

@router.get("/at-risk")
def get_all_at_risk_students(
    grade: Optional[str] = None,
    risk_level: Optional[str] = None,
    session: Session = Depends(get_session),
    _user = Depends(get_current_user)
):
    query = select(Student)
    if grade:
        query = query.where(Student.grade == grade)

    students = session.exec(query.order_by(Student.roll_number)).all()
    results = []

    for s in students:
        features = _calculate_student_features(s.id, session)
        prediction = get_ai_service().predict_student_risk(features)

        if risk_level and prediction["risk_category"].lower() != risk_level.lower():
            continue

        results.append({
            "id": s.id,
            "name": s.name,
            "roll_number": s.roll_number,
            "grade": s.grade,
            "section": s.section,
            "guardian_name": s.guardian_name,
            "phone": s.phone,
            "risk_score": prediction["risk_score"],
            "risk_category": prediction["risk_category"],
            "badge_color": prediction["badge_color"],
            "top_reasons": prediction["top_reasons"],
            "metrics": prediction["metrics"]
        })

    # Sort primarily by risk_score descending (most at-risk first)
    results.sort(key=lambda x: x["risk_score"], reverse=True)
    return results

@router.get("/at-risk/{student_id}")
def get_student_risk_detail(
    student_id: int,
    session: Session = Depends(get_session),
    _user = Depends(get_current_user)
):
    student = session.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    features = _calculate_student_features(student.id, session)
    prediction = get_ai_service().predict_student_risk(features)

    # Interventions recommendations
    interventions = []
    if features["failing_subjects"] > 0:
        interventions.append("Enroll in after-school remedial tutoring for core subjects.")
    if features["avg_marks_pct"] < 60:
        interventions.append("Schedule bi-weekly academic progress reviews with subject teachers.")
    if features["grade_trend"] < -10:
        interventions.append("Conduct a student-counselor meeting to explore personal or study habit changes.")
    if features["fee_defaults"] > 0:
        interventions.append("Reach out to guardian regarding fee installment schedule or need-based fee concession.")
    if not interventions:
        interventions.append("Maintain current academic pace and consider for honors mentoring program.")

    return {
        "student": {
            "id": student.id,
            "name": student.name,
            "roll_number": student.roll_number,
            "grade": student.grade,
            "section": student.section,
            "guardian_name": student.guardian_name,
            "phone": student.phone
        },
        "risk_assessment": prediction,
        "recommended_interventions": interventions
    }
