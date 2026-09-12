from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select
from typing import List, Optional
from pydantic import BaseModel
from database import get_session
from models.result import Result, calculate_grade
from models.student import Student
from services.pdf_service import generate_report_card_pdf
from routers.auth import get_current_user

router = APIRouter(prefix="/results", tags=["Results"])

class MarkEntryRequest(BaseModel):
    student_id: int
    subject: str
    marks_obtained: float
    total_marks: float = 100.0
    exam_type: str = "Final Term"

@router.get("/{student_id}")
def get_student_results(
    student_id: int,
    session: Session = Depends(get_session),
    _user = Depends(get_current_user)
):
    student = session.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    marks = session.exec(select(Result).where(Result.student_id == student_id)).all()
    results_list = []
    total_obtained = 0.0
    total_possible = 0.0

    for m in marks:
        grade = calculate_grade(m.marks_obtained, m.total_marks)
        total_obtained += m.marks_obtained
        total_possible += m.total_marks
        results_list.append({
            "id": m.id,
            "subject": m.subject,
            "marks_obtained": m.marks_obtained,
            "total_marks": m.total_marks,
            "percentage": round((m.marks_obtained / m.total_marks) * 100, 1) if m.total_marks > 0 else 0,
            "grade": grade,
            "exam_type": m.exam_type
        })

    pct = round((total_obtained / total_possible) * 100, 1) if total_possible > 0 else 0
    overall_grade = calculate_grade(total_obtained, total_possible) if total_possible > 0 else "N/A"

    return {
        "student": {
            "id": student.id,
            "name": student.name,
            "roll_number": student.roll_number,
            "grade": student.grade,
            "section": student.section,
            "guardian_name": student.guardian_name,
            "dob": student.dob
        },
        "results": results_list,
        "summary": {
            "total_obtained": total_obtained,
            "total_max": total_possible,
            "percentage": pct,
            "grade": overall_grade
        }
    }

@router.post("")
def enter_or_update_marks(
    req: MarkEntryRequest,
    session: Session = Depends(get_session),
    _user = Depends(get_current_user)
):
    student = session.get(Student, req.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    existing = session.exec(
        select(Result).where(
            Result.student_id == req.student_id,
            Result.subject == req.subject,
            Result.exam_type == req.exam_type
        )
    ).first()

    if existing:
        existing.marks_obtained = req.marks_obtained
        existing.total_marks = req.total_marks
        session.add(existing)
        session.commit()
        session.refresh(existing)
        target = existing
    else:
        new_result = Result(
            student_id=req.student_id,
            subject=req.subject,
            marks_obtained=req.marks_obtained,
            total_marks=req.total_marks,
            exam_type=req.exam_type
        )
        session.add(new_result)
        session.commit()
        session.refresh(new_result)
        target = new_result

    return {
        "message": "Marks recorded successfully",
        "result_id": target.id,
        "subject": target.subject,
        "marks_obtained": target.marks_obtained,
        "grade": calculate_grade(target.marks_obtained, target.total_marks)
    }

@router.get("/{student_id}/report-card/pdf")
def download_report_card(
    student_id: int,
    session: Session = Depends(get_session)
):
    student = session.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    marks = session.exec(select(Result).where(Result.student_id == student_id)).all()
    results_list = []
    total_obtained = 0.0
    total_max = 0.0

    for m in marks:
        grade = calculate_grade(m.marks_obtained, m.total_marks)
        total_obtained += m.marks_obtained
        total_max += m.total_marks
        results_list.append({
            "subject": m.subject,
            "marks_obtained": m.marks_obtained,
            "total_marks": m.total_marks,
            "grade": grade
        })

    pct = round((total_obtained / total_max) * 100, 1) if total_max > 0 else 0
    overall_grade = calculate_grade(total_obtained, total_max) if total_max > 0 else "N/A"

    student_data = {
        "name": student.name,
        "roll_number": student.roll_number,
        "grade": student.grade,
        "section": student.section,
        "guardian_name": student.guardian_name,
        "phone": student.phone,
        "dob": student.dob or "15-Aug-2011"
    }
    summary_stats = {
        "total_obtained": total_obtained,
        "total_max": total_max,
        "percentage": pct,
        "grade": overall_grade
    }

    pdf_content = generate_report_card_pdf(student_data, results_list, summary_stats)
    filename = f"ReportCard_{student.roll_number}_{student.name.replace(' ', '_')}.pdf"

    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )
