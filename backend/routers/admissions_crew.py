import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from database import get_session
from models.student import Student
from routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admissions-crew", tags=["Admissions CrewAI"])

SERVICE_UNAVAILABLE_MESSAGE = (
    "AI admissions is not available right now. All other school functions are unaffected."
)


class AdmissionRequest(BaseModel):
    student_roll_number: str
    desired_program: str


@router.post("/evaluate")
def evaluate_admission(
    req: AdmissionRequest,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    student = session.exec(select(Student).where(Student.roll_number == req.student_roll_number)).first()
    if not student:
        raise HTTPException(
            status_code=404,
            detail=f"Student with roll number {req.student_roll_number} not found in Database.",
        )

    # Sent to an external AI service, so guardian and phone details stay out.
    student_profile = (
        f"Name: {student.name}\n"
        f"Roll Number: {student.roll_number}\n"
        f"Grade: {student.grade}\n"
        f"Section: {student.section}"
    )

    try:
        # Imported here because CrewAI is heavy and optional: the rest of the app
        # must start and work without it.
        from school_crew.crew import run_admissions_crew

        final_recommendation = run_admissions_crew(student_profile, req.desired_program)
    except Exception as error:
        logger.exception("Admissions crew failed: %s", type(error).__name__)
        raise HTTPException(status_code=503, detail=SERVICE_UNAVAILABLE_MESSAGE) from error

    return {
        "status": "success",
        "recommendation": final_recommendation,
        "student_name": student.name,
    }
