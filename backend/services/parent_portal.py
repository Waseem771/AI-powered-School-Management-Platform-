"""What a parent may see about their own children. Read-only, and built from the same rules as the
staff screens (attendance, academics, fee_ledger), so the numbers cannot disagree with the school's.

Everything here starts from `linked_student` or `linked_students`: a student that is not linked to
the signed-in parent is never loaded, so there is no way to leak one by forgetting a filter.
"""
from datetime import date
from typing import Dict, List, Optional

from fastapi import HTTPException
from sqlmodel import Session, col, select

from config import SUBJECTS
from models.attendance import PRESENT, LATE, StudentAttendance
from models.fee import AcademicYear, Invoice, Payment
from models.parent import ParentStudentLink, PublishedExam
from models.result import Result, calculate_grade
from models.student import Student
from models.user import User
from services import attendance as attendance_rules
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
from services.fee_ledger import (
    invoice_money,
    paid_by_invoice,
    school_today,
    student_totals,
    utc_iso,
)
from services.receipts import receipt_number

MAX_CHILDREN_PER_PARENT = 10


# ── Who is linked to whom ───────────────────────────────────────────────────

def not_found() -> HTTPException:
    """The same answer for a student that does not exist and one that is someone else's child."""
    return HTTPException(status_code=404, detail="Student not found")


def linked_students(session: Session, parent: User) -> List[Student]:
    rows = session.exec(
        select(Student, ParentStudentLink)
        .join(ParentStudentLink, ParentStudentLink.student_id == Student.id)
        .where(ParentStudentLink.parent_id == parent.id)
        .order_by(Student.grade, Student.section, Student.roll_number)
    ).all()
    return [student for student, _ in rows]


def linked_student(session: Session, parent: User, student_id: int) -> Student:
    link = session.exec(
        select(ParentStudentLink).where(
            ParentStudentLink.parent_id == parent.id, ParentStudentLink.student_id == student_id
        )
    ).first()
    student = session.get(Student, student_id) if link else None
    if student is None:
        raise not_found()
    return student


def relationship_of(session: Session, parent: User, student_id: int) -> Optional[str]:
    link = session.exec(
        select(ParentStudentLink).where(
            ParentStudentLink.parent_id == parent.id, ParentStudentLink.student_id == student_id
        )
    ).first()
    return link.relationship if link else None


def basic_info(student: Student, relationship: Optional[str] = None) -> dict:
    """What a parent sees of their child. No phone number or date of birth is needed on screen."""
    return {
        "id": student.id,
        "name": student.name,
        "roll_number": student.roll_number,
        "grade": student.grade,
        "section": student.section,
        "guardian_name": student.guardian_name,
        "relationship": relationship,
        "enrolled": student.archived_at is None,
    }


# ── Attendance ──────────────────────────────────────────────────────────────

def _attendance_block(records: List[StudentAttendance]) -> dict:
    counts = attendance_rules.counts_by_status(records)
    return {
        "recorded": len(records),
        **counts,
        "attendance_rate": attendance_rules.rate(counts[PRESENT], counts[LATE], len(records)),
    }


def attendance_view(session: Session, student: Student, month: Optional[str]) -> dict:
    """One month, day by day, and the whole current session. Only recorded days are counted; a day with
    no record is not recorded, never absent. Who marked it and why it was corrected stay with the school."""
    first, last = attendance_rules.month_range(month)
    month_records = session.exec(
        select(StudentAttendance)
        .where(
            StudentAttendance.student_id == student.id,
            StudentAttendance.attendance_date >= first,
            StudentAttendance.attendance_date <= last,
        )
        .order_by(StudentAttendance.attendance_date)
    ).all()
    year_id = current_academic_year_id(session)
    session_records = session.exec(
        select(StudentAttendance).where(
            StudentAttendance.student_id == student.id, StudentAttendance.academic_year_id == year_id
        )
    ).all()
    year = session.get(AcademicYear, year_id)
    return {
        "student": basic_info(student),
        "month": first.strftime("%Y-%m"),
        "first": first.isoformat(),
        "last": last.isoformat(),
        "today": school_today().isoformat(),
        "days": [{"date": record.attendance_date.isoformat(), "status": record.status} for record in month_records],
        "month_summary": _attendance_block(list(month_records)),
        "session_label": year.label if year else None,
        "session_summary": _attendance_block(list(session_records)),
    }


# ── Results ─────────────────────────────────────────────────────────────────

def published_exam_keys(session: Session) -> set:
    return {(row.academic_year_id, row.exam_type) for row in session.exec(select(PublishedExam)).all()}


def published_marks(session: Session, student_id: int) -> List[Result]:
    """This student's marks, limited to exams the school has released to parents."""
    keys = published_exam_keys(session)
    if not keys:
        return []
    marks = session.exec(select(Result).where(Result.student_id == student_id)).all()
    return [
        mark for mark in marks
        if mark.academic_year_id is not None and (mark.academic_year_id, mark.exam_type) in keys
    ]


def _subject_order(mark: Result) -> int:
    return SUBJECTS.index(mark.subject) if mark.subject in SUBJECTS else len(SUBJECTS)


def _exam_info(exam_type: str, year_id: Optional[int], labels: Dict[int, str]) -> dict:
    return {"exam_type": exam_type, "academic_year_id": year_id, "session": labels.get(year_id)}


def results_view(
    session: Session, student: Student, exam_type: Optional[str], academic_year_id: Optional[int]
) -> dict:
    marks = published_marks(session, student.id)
    labels = academic_year_labels(session)
    chosen = sorted(select_exam(marks, exam_type, academic_year_id), key=_subject_order)
    exams = []
    for year_id, kind in exams_recorded(marks):
        summary = exam_summary([mark for mark in marks if (mark.academic_year_id, mark.exam_type) == (year_id, kind)])
        exams.append({**_exam_info(kind, year_id, labels), "percentage": summary["percentage"], "grade": summary["grade"]})
    return {
        "student": basic_info(student),
        "exam": _exam_info(chosen[0].exam_type, chosen[0].academic_year_id, labels) if chosen else None,
        "available_exams": exams,
        "results": [
            {
                "subject": mark.subject,
                "marks_obtained": mark.marks_obtained,
                "total_marks": mark.total_marks,
                "percentage": round(percentage(mark.marks_obtained, mark.total_marks), 1),
                "grade": calculate_grade(mark.marks_obtained, mark.total_marks),
                "passed": subject_passed(mark),
            }
            for mark in chosen
        ],
        "summary": exam_summary(chosen),
        "promotion": promotion_decision(chosen),
    }


def latest_published_exam(session: Session, student_id: int) -> Optional[dict]:
    marks = published_marks(session, student_id)
    latest = select_exam(marks)
    if not latest:
        return None
    labels = academic_year_labels(session)
    summary = exam_summary(latest)
    return {
        **_exam_info(latest[0].exam_type, latest[0].academic_year_id, labels),
        "percentage": summary["percentage"],
        "grade": summary["grade"],
    }


# ── Fees ────────────────────────────────────────────────────────────────────

def fees_view(session: Session, student: Student) -> dict:
    today = school_today()
    invoices = session.exec(select(Invoice).where(Invoice.student_id == student.id).order_by(col(Invoice.id).desc())).all()
    paid = paid_by_invoice(session, [invoice.id for invoice in invoices])
    payments = session.exec(
        select(Payment).where(col(Payment.invoice_id).in_([invoice.id for invoice in invoices] or [0])).order_by(Payment.id)
    ).all()
    by_invoice: Dict[int, List[Payment]] = {}
    for payment in payments:
        by_invoice.setdefault(payment.invoice_id, []).append(payment)
    return {
        "student": basic_info(student),
        "totals": student_totals(session, student.id, today),
        "invoices": [
            {
                "id": invoice.id,
                "month": invoice.month,
                "due_date": invoice.due_date,
                "amount": invoice.amount,
                "status": invoice.status,
                "challan_number": invoice.challan_number,
                **invoice_money(invoice, paid.get(invoice.id, 0.0), today),
                "payments": [
                    {
                        "id": payment.id,
                        "receipt_number": receipt_number(payment.id),
                        "amount_paid": payment.amount_paid,
                        "payment_mode": payment.payment_mode,
                        "paid_at": utc_iso(payment.paid_at),
                    }
                    for payment in by_invoice.get(invoice.id, [])
                ],
            }
            for invoice in invoices
        ],
    }


# ── Dashboard card for one child ────────────────────────────────────────────

def child_summary(session: Session, parent: User, student: Student, month: str) -> dict:
    first, last = attendance_rules.month_range(month)
    month_records = session.exec(
        select(StudentAttendance).where(
            StudentAttendance.student_id == student.id,
            StudentAttendance.attendance_date >= first,
            StudentAttendance.attendance_date <= last,
        )
    ).all()
    year_id = current_academic_year_id(session)
    session_records = session.exec(
        select(StudentAttendance).where(
            StudentAttendance.student_id == student.id, StudentAttendance.academic_year_id == year_id
        )
    ).all()
    return {
        **basic_info(student, relationship_of(session, parent, student.id)),
        "attendance": {
            "month": first.strftime("%Y-%m"),
            "month_summary": _attendance_block(list(month_records)),
            "session_summary": _attendance_block(list(session_records)),
        },
        "latest_result": latest_published_exam(session, student.id),
        "fees": student_totals(session, student.id),
    }


def current_month() -> str:
    today: date = school_today()
    return today.strftime("%Y-%m")
