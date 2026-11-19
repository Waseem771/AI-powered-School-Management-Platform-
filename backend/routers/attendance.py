"""Daily attendance: the teacher's own classes, and the administrator's monitoring and corrections.

A teacher reaches only the classes assigned to them (checked on every request). Administrators
see the whole school. Both save through the same rules in services/attendance.py.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from database import get_session
from models.attendance import TeacherClassAssignment
from models.fee import AcademicYear
from models.student import Student
from models.user import User
from routers.teachers import require_admin, require_teacher
from services import attendance as rules
from services.fee_ledger import school_today

teacher_router = APIRouter(prefix="/teacher/classes", tags=["Teacher classes and attendance"])
admin_router = APIRouter(prefix="/attendance", tags=["Attendance (administrator)"])


class Entry(BaseModel):
    student_id: int
    status: str


class SaveAttendance(BaseModel):
    date: str
    entries: List[Entry] = Field(max_length=500)
    reason: Optional[str] = None


class AdminSaveAttendance(SaveAttendance):
    grade: str
    section: str
    academic_year_id: Optional[int] = None


def _pairs(payload: SaveAttendance):
    return [(entry.student_id, entry.status) for entry in payload.entries]


# ── Teacher ─────────────────────────────────────────────────────────────────

def _own_assignment(session: Session, teacher: User, assignment_id: int) -> TeacherClassAssignment:
    """403 for a class that is not theirs, whether it exists or not, so ids cannot be probed."""
    row = session.get(TeacherClassAssignment, assignment_id)
    if row is None or row.teacher_id != teacher.id:
        raise HTTPException(status_code=403, detail="You are not assigned to this class.")
    return row


def _class_view(session: Session, row: TeacherClassAssignment, today) -> dict:
    year = session.get(AcademicYear, row.academic_year_id)
    day = rules.class_day(session, row.grade, row.section, today)
    return {
        "id": row.id, "grade": row.grade, "section": row.section,
        "academic_year_id": row.academic_year_id, "academic_year": year.label if year else None,
        "is_current_session": bool(year and year.is_current), "enrolled": day["enrolled"],
        "today_attendance": {"date": day["date"], "recorded": day["recorded"], "state": day["state"]},
    }


@teacher_router.get("")
def my_classes(session: Session = Depends(get_session), teacher: User = Depends(require_teacher)):
    today = school_today()
    rows = session.exec(select(TeacherClassAssignment).where(TeacherClassAssignment.teacher_id == teacher.id)
                        .order_by(TeacherClassAssignment.grade, TeacherClassAssignment.section)).all()
    return {"today": today.isoformat(), "classes": [_class_view(session, row, today) for row in rows]}


@teacher_router.get("/{assignment_id}")
def my_class(assignment_id: int, session: Session = Depends(get_session), teacher: User = Depends(require_teacher)):
    row = _own_assignment(session, teacher, assignment_id)
    today = school_today()
    return {"today": today.isoformat(), "edit_window_days": rules.TEACHER_EDIT_WINDOW_DAYS,
            **_class_view(session, row, today),
            "students": [rules.student_summary(s) for s in rules.roster(session, row.grade, row.section)]}


@teacher_router.get("/{assignment_id}/attendance")
def class_attendance(
    assignment_id: int,
    date: Optional[str] = None,
    session: Session = Depends(get_session),
    teacher: User = Depends(require_teacher),
):
    row = _own_assignment(session, teacher, assignment_id)
    day = rules.parse_date(date) if date else school_today()
    if day > school_today():
        raise rules.bad_request("Attendance cannot be recorded for a future date.")
    return {"today": school_today().isoformat(), "edit_window_days": rules.TEACHER_EDIT_WINDOW_DAYS,
            "can_edit": day >= school_today() - rules.timedelta(days=rules.TEACHER_EDIT_WINDOW_DAYS),
            **rules.class_day(session, row.grade, row.section, day)}


@teacher_router.put("/{assignment_id}/attendance")
def save_class_attendance(
    assignment_id: int,
    payload: SaveAttendance,
    session: Session = Depends(get_session),
    teacher: User = Depends(require_teacher),
):
    row = _own_assignment(session, teacher, assignment_id)
    year = session.get(AcademicYear, row.academic_year_id)
    if year is None or not year.is_current:
        raise rules.bad_request("This class belongs to a session that is not current, so attendance is closed.", 409)
    result = rules.save_attendance(
        session, grade=row.grade, section=row.section, year=year, day=rules.parse_date(payload.date),
        entries=_pairs(payload), user=teacher, reason=payload.reason, is_admin=False)
    return {**result, **rules.class_day(session, row.grade, row.section, rules.parse_date(payload.date))}


@teacher_router.get("/{assignment_id}/history")
def class_history(
    assignment_id: int,
    start: Optional[str] = None,
    end: Optional[str] = None,
    session: Session = Depends(get_session),
    teacher: User = Depends(require_teacher),
):
    row = _own_assignment(session, teacher, assignment_id)
    first, last = rules.date_range(start, end)
    return {"first": first.isoformat(), "last": last.isoformat(),
            "days": rules.class_history(session, row.grade, row.section, row.academic_year_id, first, last)}


# ── Administrator ───────────────────────────────────────────────────────────

def _class_filter(grade: Optional[str], section: Optional[str]) -> None:
    if grade and grade not in rules.GRADES or section and section not in rules.SECTIONS:
        raise rules.bad_request("That grade or section does not exist.")


@admin_router.get("/overview")
def overview(
    date: Optional[str] = None, grade: Optional[str] = None, section: Optional[str] = None,
    academic_year_id: Optional[int] = None,
    session: Session = Depends(get_session), _admin: User = Depends(require_admin),
):
    _class_filter(grade, section)
    day = rules.parse_date(date) if date else school_today()
    return rules.daily_overview(session, day, grade, section, academic_year_id)


@admin_router.get("/class-day")
def class_day(
    date: str, grade: str, section: str,
    session: Session = Depends(get_session), _admin: User = Depends(require_admin),
):
    rules.check_class(grade, section)
    return rules.class_day(session, grade, section, rules.parse_date(date))


@admin_router.put("/class-day")
def correct_class_day(
    payload: AdminSaveAttendance,
    session: Session = Depends(get_session), admin: User = Depends(require_admin),
):
    rules.check_class(payload.grade, payload.section)
    year = rules.get_year(session, payload.academic_year_id)
    day = rules.parse_date(payload.date)
    result = rules.save_attendance(
        session, grade=payload.grade, section=payload.section, year=year, day=day,
        entries=_pairs(payload), user=admin, reason=payload.reason, is_admin=True)
    return {**result, **rules.class_day(session, payload.grade, payload.section, day)}


@admin_router.get("/monthly")
def monthly(
    month: Optional[str] = None, grade: Optional[str] = None, section: Optional[str] = None,
    academic_year_id: Optional[int] = None,
    session: Session = Depends(get_session), _admin: User = Depends(require_admin),
):
    _class_filter(grade, section)
    return rules.monthly_summary(session, month, grade, section, academic_year_id)


@admin_router.get("/frequent-absentees")
def frequent_absentees(
    start: Optional[str] = None, end: Optional[str] = None, min_absences: int = 3,
    grade: Optional[str] = None, section: Optional[str] = None, academic_year_id: Optional[int] = None,
    session: Session = Depends(get_session), _admin: User = Depends(require_admin),
):
    _class_filter(grade, section)
    first, last = rules.date_range(start, end)
    return {"first": first.isoformat(), "last": last.isoformat(), "min_absences": max(min_absences, 1),
            "students": rules.frequent_absentees(session, first, last, grade, section, academic_year_id,
                                                 max(min_absences, 1))}


@admin_router.get("/students/{student_id}/history")
def student_history(
    student_id: int, start: Optional[str] = None, end: Optional[str] = None,
    session: Session = Depends(get_session), _admin: User = Depends(require_admin),
):
    student = session.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    first, last = rules.date_range(start, end, default_days=90)
    return rules.student_history(session, student, first, last)


@admin_router.get("/changes")
def changes(
    start: Optional[str] = None, end: Optional[str] = None,
    grade: Optional[str] = None, section: Optional[str] = None,
    session: Session = Depends(get_session), _admin: User = Depends(require_admin),
):
    _class_filter(grade, section)
    first, last = rules.date_range(start, end)
    return {"first": first.isoformat(), "last": last.isoformat(),
            "changes": rules.audit_trail(session, first, last, grade, section)}


@admin_router.get("/report")
def report(
    start: Optional[str] = None, end: Optional[str] = None,
    grade: Optional[str] = None, section: Optional[str] = None, academic_year_id: Optional[int] = None,
    session: Session = Depends(get_session), _admin: User = Depends(require_admin),
):
    _class_filter(grade, section)
    first, last = rules.date_range(start, end)
    return rules.report(session, first, last, grade, section, academic_year_id)


@admin_router.get("/export.csv")
def export(
    start: Optional[str] = None, end: Optional[str] = None,
    grade: Optional[str] = None, section: Optional[str] = None, academic_year_id: Optional[int] = None,
    session: Session = Depends(get_session), _admin: User = Depends(require_admin),
):
    _class_filter(grade, section)
    first, last = rules.date_range(start, end)
    body = "﻿" + rules.export_csv(session, first, last, grade, section, academic_year_id)
    return Response(content=body, media_type="text/csv; charset=utf-8", headers={
        "Content-Disposition": f'attachment; filename="attendance-{first.isoformat()}-to-{last.isoformat()}.csv"'})
