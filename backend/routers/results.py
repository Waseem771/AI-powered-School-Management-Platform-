from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status as http_status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from config import SUBJECTS
from database import get_session
from models.result import ExamType, FINAL_TERM, Result, calculate_grade
from models.student import Student
from routers.auth import get_current_user
from services.academics import (
    academic_year_labels,
    current_academic_year_id,
    exam_summary,
    exams_recorded,
    percentage,
    promotion_decision,
    select_exam,
    subject_passed,
)
from services.pdf_service import generate_report_card_pdf, pdf_content_disposition

router = APIRouter(prefix="/results", tags=["Results"])

MAX_TOTAL_MARKS = 1000.0


class MarkEntryRequest(BaseModel):
    student_id: int
    subject: str
    marks_obtained: float = Field(ge=0, allow_inf_nan=False)
    total_marks: float = Field(default=100.0, gt=0, le=MAX_TOTAL_MARKS, allow_inf_nan=False)
    exam_type: ExamType = FINAL_TERM

    @field_validator("subject")
    @classmethod
    def subject_is_known(cls, value: str) -> str:
        if value not in SUBJECTS:
            raise ValueError(f"Subject must be one of: {', '.join(SUBJECTS)}.")
        return value

    @model_validator(mode="after")
    def marks_fit_the_total(self) -> "MarkEntryRequest":
        if self.marks_obtained > self.total_marks:
            raise ValueError(f"Marks obtained cannot be more than the total of {self.total_marks:g}.")
        return self


def _get_student_or_404(session: Session, student_id: int) -> Student:
    student = session.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


def _subject_order(mark: Result) -> int:
    return SUBJECTS.index(mark.subject) if mark.subject in SUBJECTS else len(SUBJECTS)


def _exam_info(exam_type: str, year_id: Optional[int], year_labels: Dict[int, str]) -> Dict[str, Any]:
    return {"exam_type": exam_type, "academic_year_id": year_id, "session": year_labels.get(year_id)}


def _exam_report(
    session: Session, student_id: int, exam_type: Optional[str], academic_year_id: Optional[int]
) -> Dict[str, Any]:
    """Everything shown about one exam. The results page and the report card both use this."""
    all_marks = session.exec(select(Result).where(Result.student_id == student_id)).all()
    marks = sorted(select_exam(all_marks, exam_type, academic_year_id), key=_subject_order)
    labels = academic_year_labels(session)
    return {
        "marks": marks,
        "exam": _exam_info(marks[0].exam_type, marks[0].academic_year_id, labels) if marks else None,
        "available_exams": [_exam_info(kind, year, labels) for year, kind in exams_recorded(all_marks)],
        "summary": exam_summary(marks),
        "promotion": promotion_decision(marks),
    }


def _mark_rows(marks: List[Result]) -> List[Dict[str, Any]]:
    return [
        {
            "id": mark.id,
            "subject": mark.subject,
            "marks_obtained": mark.marks_obtained,
            "total_marks": mark.total_marks,
            "percentage": round(percentage(mark.marks_obtained, mark.total_marks), 1),
            "grade": calculate_grade(mark.marks_obtained, mark.total_marks),
            "passed": subject_passed(mark),
            "exam_type": mark.exam_type,
        }
        for mark in marks
    ]


@router.get("/{student_id}")
def get_student_results(
    student_id: int,
    exam_type: Optional[ExamType] = None,
    academic_year_id: Optional[int] = None,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    student = _get_student_or_404(session, student_id)
    report = _exam_report(session, student_id, exam_type, academic_year_id)
    return {
        "student": {
            "id": student.id,
            "name": student.name,
            "roll_number": student.roll_number,
            "grade": student.grade,
            "section": student.section,
            "guardian_name": student.guardian_name,
            "dob": student.dob,
            "archived_at": student.archived_at,
        },
        "exam": report["exam"],
        "available_exams": report["available_exams"],
        "results": _mark_rows(report["marks"]),
        "summary": report["summary"],
        "promotion": report["promotion"],
    }


@router.post("")
def enter_or_update_marks(
    req: MarkEntryRequest,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    student = _get_student_or_404(session, req.student_id)
    if student.archived_at:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="This student is archived. Restore the student before entering marks.",
        )

    year_id = current_academic_year_id(session)
    target = session.exec(
        select(Result).where(
            Result.student_id == req.student_id,
            Result.subject == req.subject,
            Result.exam_type == req.exam_type,
            Result.academic_year_id == year_id,
        )
    ).first()

    if target:
        target.marks_obtained = req.marks_obtained
        target.total_marks = req.total_marks
    else:
        target = Result(
            student_id=req.student_id,
            subject=req.subject,
            marks_obtained=req.marks_obtained,
            total_marks=req.total_marks,
            exam_type=req.exam_type,
            academic_year_id=year_id,
        )
    session.add(target)
    try:
        session.commit()
    except IntegrityError:
        # An identical request arrived at the same moment, and the database index caught it.
        session.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT, detail="These marks were just saved by another request."
        )
    session.refresh(target)

    return {
        "message": "Marks recorded successfully",
        "result_id": target.id,
        "subject": target.subject,
        "marks_obtained": target.marks_obtained,
        "exam_type": target.exam_type,
        "grade": calculate_grade(target.marks_obtained, target.total_marks),
    }


@router.get("/{student_id}/report-card/pdf")
def download_report_card(
    student_id: int,
    exam_type: Optional[ExamType] = None,
    academic_year_id: Optional[int] = None,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    student = _get_student_or_404(session, student_id)
    report = _exam_report(session, student_id, exam_type, academic_year_id)
    if not report["marks"]:
        raise HTTPException(status_code=404, detail="No marks recorded for this exam, so there is no report card yet.")

    student_data = {
        "name": student.name,
        "roll_number": student.roll_number,
        "grade": student.grade,
        "section": student.section,
        "guardian_name": student.guardian_name,
        "phone": student.phone,
        "dob": student.dob or "Not recorded",
    }
    pdf_content = generate_report_card_pdf(
        student_data, _mark_rows(report["marks"]), report["summary"], report["exam"], report["promotion"]
    )
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": pdf_content_disposition("ReportCard", student.roll_number)},
    )
