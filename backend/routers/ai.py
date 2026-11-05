from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session, col, select

from config import SUBJECTS
from database import get_session
from models.student import Student
from routers.auth import get_current_user
from services.ai_service import MODEL_NOTE, ai_service
from services.risk_assessment import assess_student, assess_students, suggested_steps

router = APIRouter(prefix="/ai", tags=["AI - At Risk"])


class SimulatedStudent(BaseModel):
    """Made-up numbers for trying the model. It takes nothing about fees, so anything extra is refused."""
    model_config = ConfigDict(extra="forbid")

    avg_marks_pct: float = Field(ge=0, le=100, allow_inf_nan=False)
    failing_subjects: int = Field(ge=0, le=len(SUBJECTS))
    grade_trend: Optional[float] = Field(default=None, ge=-100, le=100, allow_inf_nan=False)


def _same_band(category: str, wanted: str) -> bool:
    return category.lower() == wanted.strip().lower().replace("_", " ")


@router.get("/at-risk")
def get_all_at_risk_students(
    grade: Optional[str] = None,
    risk_level: Optional[str] = None,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    query = select(Student).where(col(Student.archived_at).is_(None))
    if grade:
        query = query.where(Student.grade == grade)
    students = session.exec(query.order_by(Student.roll_number)).all()
    assessments = assess_students(session, students)

    rows = [
        {
            "id": student.id,
            "name": student.name,
            "roll_number": student.roll_number,
            "grade": student.grade,
            "section": student.section,
            **assessments[student.id],
        }
        for student in students
        if not risk_level or _same_band(assessments[student.id]["risk_category"], risk_level)
    ]
    # Highest estimate first, and students with no estimate last.
    rows.sort(key=lambda row: (row["risk_score"] is None, -(row["risk_score"] or 0)))
    return rows


@router.get("/at-risk/{student_id}")
def get_student_risk_detail(
    student_id: int,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    student = session.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    assessment = assess_student(session, student)
    fee_follow_up = assessment.pop("fee_follow_up")
    return {
        "student": {
            "id": student.id,
            "name": student.name,
            "roll_number": student.roll_number,
            "grade": student.grade,
            "section": student.section,
            "guardian_name": student.guardian_name,
            "phone": student.phone,
        },
        "risk_assessment": assessment,
        "recommended_interventions": suggested_steps(assessment["metrics"]),
        "fee_follow_up": fee_follow_up,
        "note": MODEL_NOTE,
    }


@router.post("/simulate")
def simulate_student(student: SimulatedStudent, _user=Depends(get_current_user)):
    """Runs the real model on made-up numbers. Nothing is read from or saved to any record."""
    return ai_service.predict_student_risk(student.model_dump())
