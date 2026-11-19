"""Attendance rules: who may mark what and when, saving with an audit trail, and reports.

Everything reported comes from rows in student_attendance. A student with no row on a day has
not been recorded, and is never counted as absent.
"""
import csv
import io
from datetime import date, datetime, timedelta, timezone  # noqa: F401
from typing import Dict, Iterable, List, Optional, Sequence

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, func, select

from config import GRADES, SECTIONS
from models.attendance import (
    ABSENT,
    LATE,
    PRESENT,
    STATUSES,
    AttendanceChangeHistory,
    StudentAttendance,
    TeacherClassAssignment,
)
from models.fee import AcademicYear
from models.student import Student
from models.user import ROLE_TEACHER, User
from services.fee_ledger import school_today, utc_iso

# A teacher can record or correct a day for this many days back. Administrators have no limit.
TEACHER_EDIT_WINDOW_DAYS = 7
REASON_MIN = 3
REASON_MAX = 300
MAX_REPORT_DAYS = 366
NOT_SUBMITTED, PARTIAL, COMPLETE = "not_submitted", "partial", "complete"


def bad_request(detail: str, status_code: int = 422) -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail)


# ── Dates ───────────────────────────────────────────────────────────────────

def parse_date(value: Optional[str], label: str = "date") -> date:
    try:
        return date.fromisoformat((value or "").strip())
    except ValueError:
        raise bad_request(f"The {label} must be a real date, written YYYY-MM-DD.")


def check_attendance_date(day: date, is_admin: bool) -> None:
    today = school_today()
    if day > today:
        raise bad_request("Attendance cannot be recorded for a future date.")
    if not is_admin and day < today - timedelta(days=TEACHER_EDIT_WINDOW_DAYS):
        raise bad_request(
            f"Teachers can record or correct attendance for the last {TEACHER_EDIT_WINDOW_DAYS} days. "
            "Ask the school office for older dates.",
            status_code=403,
        )


def date_range(start: Optional[str], end: Optional[str], default_days: int = 30) -> tuple[date, date]:
    last = parse_date(end, "end date") if end else school_today()
    first = parse_date(start, "start date") if start else last - timedelta(days=default_days - 1)
    if first > last:
        raise bad_request("The start date must not be after the end date.")
    if (last - first).days >= MAX_REPORT_DAYS:
        raise bad_request(f"Choose a range of at most {MAX_REPORT_DAYS} days.")
    return first, last


def month_range(month: Optional[str]) -> tuple[date, date]:
    try:
        first = date.fromisoformat(f"{(month or school_today().strftime('%Y-%m')).strip()}-01")
    except ValueError:
        raise bad_request("The month must be written YYYY-MM.")
    following = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
    return first, following - timedelta(days=1)


# ── Classes, sessions and rosters ───────────────────────────────────────────

def check_class(grade: str, section: str) -> None:
    if grade not in GRADES or section not in SECTIONS:
        raise bad_request(f"Choose a grade from {', '.join(GRADES)} and a section from {', '.join(SECTIONS)}.")


def get_year(session: Session, year_id: Optional[int]) -> AcademicYear:
    year = session.get(AcademicYear, year_id) if year_id else session.exec(
        select(AcademicYear).where(AcademicYear.is_current == True)  # noqa: E712
    ).first()
    if year is None:
        raise bad_request("That academic session does not exist.")
    return year


def roster(session: Session, grade: str, section: str) -> List[Student]:
    """Current students of the class. Archived students have left, so they are not listed."""
    return list(session.exec(
        select(Student)
        .where(Student.grade == grade, Student.section == section, col(Student.archived_at).is_(None))
        .order_by(Student.roll_number)
    ).all())


def roster_counts(session: Session) -> Dict[tuple, int]:
    rows = session.exec(
        select(Student.grade, Student.section, func.count())
        .where(col(Student.archived_at).is_(None))
        .group_by(Student.grade, Student.section)
    ).all()
    return {(grade, section): count for grade, section, count in rows}


def student_summary(student: Student) -> dict:
    """What a teacher may see of a student: no guardian, phone or date of birth."""
    return {"id": student.id, "name": student.name, "roll_number": student.roll_number,
            "grade": student.grade, "section": student.section}


# ── Saving ──────────────────────────────────────────────────────────────────

def save_attendance(
    session: Session,
    *,
    grade: str,
    section: str,
    year: AcademicYear,
    day: date,
    entries: Sequence[tuple[int, str]],
    user: User,
    reason: Optional[str],
    is_admin: bool,
) -> dict:
    """Records a class's attendance for a day, all or nothing.

    New students get a record. A student who already has one and whose status differs is a
    correction, which needs a reason and is written to the change history. Unchanged students
    are left alone. Students not listed stay unrecorded.
    """
    check_attendance_date(day, is_admin)
    if not entries:
        raise bad_request("Mark at least one student before saving.")
    reason = (reason or "").strip()
    if len(reason) > REASON_MAX:
        raise bad_request(f"The reason must be at most {REASON_MAX} characters.")

    students = {student.id: student for student in roster(session, grade, section)}
    seen = set()
    for student_id, status in entries:
        if status not in STATUSES:
            raise bad_request(f"Status must be one of: {', '.join(STATUSES)}.")
        if student_id in seen:
            raise bad_request("A student appears more than once in this submission.")
        seen.add(student_id)
        if student_id not in students:
            # Also covers students of other classes, so a teacher cannot mark outside the class.
            raise bad_request("One or more students are not in this class.", status_code=403)

    existing = {
        record.student_id: record
        for record in session.exec(
            select(StudentAttendance).where(
                StudentAttendance.attendance_date == day, col(StudentAttendance.student_id).in_(seen)
            )
        ).all()
    }
    changes = [(student_id, status) for student_id, status in entries
               if student_id in existing and existing[student_id].status != status]
    if changes and len(reason) < REASON_MIN:
        raise bad_request("Say why attendance is being corrected (at least 3 characters).")

    now = datetime.now(timezone.utc)
    created = corrected = unchanged = 0
    try:
        for student_id, status in entries:
            record = existing.get(student_id)
            if record is None:
                session.add(StudentAttendance(
                    student_id=student_id, grade=grade, section=section, academic_year_id=year.id,
                    attendance_date=day, status=status, marked_by=user.id, created_at=now, updated_at=now,
                ))
                created += 1
            elif record.status != status:
                session.add(AttendanceChangeHistory(
                    attendance_id=record.id, student_id=student_id, attendance_date=day,
                    old_status=record.status, new_status=status, reason=reason, changed_by=user.id, changed_at=now,
                ))
                record.status, record.updated_at = status, now
                session.add(record)
                corrected += 1
            else:
                unchanged += 1
        session.commit()
    except IntegrityError:
        session.rollback()
        raise bad_request("Attendance for one of these students was just saved by someone else. Reload and try again.",
                          status_code=409)
    return {"date": day.isoformat(), "created": created, "corrected": corrected, "unchanged": unchanged}


# ── Reading a class's day ───────────────────────────────────────────────────

def submission_state(recorded: int, enrolled: int) -> str:
    if recorded == 0:
        return NOT_SUBMITTED
    return COMPLETE if recorded >= enrolled else PARTIAL


def _names(session: Session, user_ids: Iterable[int]) -> Dict[int, str]:
    ids = {user_id for user_id in user_ids if user_id}
    if not ids:
        return {}
    users = session.exec(select(User).where(col(User.id).in_(ids))).all()
    return {user.id: user.full_name or user.username for user in users}


def class_day(session: Session, grade: str, section: str, day: date) -> dict:
    """The roster with each student's recorded status, or null when not recorded, plus the day's audit trail."""
    students = roster(session, grade, section)
    records = {
        record.student_id: record
        for record in session.exec(
            select(StudentAttendance).where(
                StudentAttendance.attendance_date == day,
                col(StudentAttendance.student_id).in_([student.id for student in students] or [0]),
            )
        ).all()
    }
    changes = session.exec(
        select(AttendanceChangeHistory)
        .where(AttendanceChangeHistory.attendance_date == day,
               col(AttendanceChangeHistory.student_id).in_([student.id for student in students] or [0]))
        .order_by(col(AttendanceChangeHistory.changed_at).desc())
    ).all()
    names = _names(session, [r.marked_by for r in records.values()] + [c.changed_by for c in changes])
    by_id = {student.id: student for student in students}
    return {
        "date": day.isoformat(),
        "grade": grade,
        "section": section,
        "enrolled": len(students),
        "recorded": len(records),
        "state": submission_state(len(records), len(students)),
        "students": [
            {**student_summary(student),
             "status": records[student.id].status if student.id in records else None,
             "marked_by": names.get(records[student.id].marked_by) if student.id in records else None}
            for student in students
        ],
        "changes": [
            {"student_id": change.student_id, "student_name": by_id[change.student_id].name
             if change.student_id in by_id else None,
             "old_status": change.old_status, "new_status": change.new_status, "reason": change.reason,
             "changed_by": names.get(change.changed_by), "changed_at": utc_iso(change.changed_at)}
            for change in changes
        ],
    }


def counts_by_status(records: Iterable[StudentAttendance]) -> Dict[str, int]:
    counts = {status: 0 for status in STATUSES}
    for record in records:
        counts[record.status] += 1
    return counts


def class_history(session: Session, grade: str, section: str, year_id: int, first: date, last: date) -> List[dict]:
    """One line per day that has any record, newest first. Days with no records are not listed."""
    enrolled = len(roster(session, grade, section))
    rows = session.exec(
        select(StudentAttendance).where(
            StudentAttendance.grade == grade, StudentAttendance.section == section,
            StudentAttendance.academic_year_id == year_id,
            StudentAttendance.attendance_date >= first, StudentAttendance.attendance_date <= last,
        )
    ).all()
    corrected = set(session.exec(
        select(AttendanceChangeHistory.attendance_date).where(
            col(AttendanceChangeHistory.attendance_id).in_([row.id for row in rows] or [0])
        )
    ).all()) if rows else set()
    days: Dict[date, List[StudentAttendance]] = {}
    for row in rows:
        days.setdefault(row.attendance_date, []).append(row)
    return [
        {"date": day.isoformat(), "recorded": len(records), "enrolled": enrolled,
         "state": submission_state(len(records), enrolled), "corrected": day in corrected,
         **counts_by_status(records)}
        for day, records in sorted(days.items(), reverse=True)
    ]


# ── Admin reports ───────────────────────────────────────────────────────────

def _filters(grade: Optional[str], section: Optional[str], year_id: Optional[int]) -> list:
    conditions = []
    if grade:
        conditions.append(StudentAttendance.grade == grade)
    if section:
        conditions.append(StudentAttendance.section == section)
    if year_id:
        conditions.append(StudentAttendance.academic_year_id == year_id)
    return conditions


def all_classes(grade: Optional[str] = None, section: Optional[str] = None) -> List[tuple]:
    return [(g, s) for g in GRADES for s in SECTIONS if (not grade or g == grade) and (not section or s == section)]


def daily_overview(session: Session, day: date, grade=None, section=None, year_id=None) -> dict:
    """Each class for one day, with 'not submitted' kept apart from recorded absences."""
    enrolled = roster_counts(session)
    records = session.exec(
        select(StudentAttendance).where(StudentAttendance.attendance_date == day, *_filters(grade, section, year_id))
    ).all()
    by_class: Dict[tuple, List[StudentAttendance]] = {}
    for record in records:
        by_class.setdefault((record.grade, record.section), []).append(record)
    teachers = _assigned_teachers(session, year_id)
    rows = []
    for class_grade, class_section in all_classes(grade, section):
        class_records = by_class.get((class_grade, class_section), [])
        total = enrolled.get((class_grade, class_section), 0)
        rows.append({
            "grade": class_grade, "section": class_section, "enrolled": total, "recorded": len(class_records),
            "not_recorded": max(total - len(class_records), 0),
            "state": submission_state(len(class_records), total),
            "teachers": teachers.get((class_grade, class_section), []),
            **counts_by_status(class_records),
        })
    totals = counts_by_status(records)
    return {
        "date": day.isoformat(), "classes": rows,
        "totals": {"enrolled": sum(r["enrolled"] for r in rows), "recorded": len(records),
                   "not_recorded": sum(r["not_recorded"] for r in rows), **totals},
        "classes_not_submitted": sum(1 for r in rows if r["state"] == NOT_SUBMITTED),
    }


def _assigned_teachers(session: Session, year_id: Optional[int]) -> Dict[tuple, List[str]]:
    year = get_year(session, year_id)
    rows = session.exec(select(TeacherClassAssignment).where(TeacherClassAssignment.academic_year_id == year.id)).all()
    names = _names(session, [row.teacher_id for row in rows])
    result: Dict[tuple, List[str]] = {}
    for row in rows:
        result.setdefault((row.grade, row.section), []).append(names.get(row.teacher_id, "Unknown"))
    return result


def rate(present: int, late: int, recorded: int) -> Optional[float]:
    """Share of recorded students who attended (present or late). None when nothing is recorded."""
    return round((present + late) * 100 / recorded, 1) if recorded else None


def monthly_summary(session: Session, month: Optional[str], grade=None, section=None, year_id=None) -> dict:
    first, last = month_range(month)
    records = session.exec(
        select(StudentAttendance).where(
            StudentAttendance.attendance_date >= first, StudentAttendance.attendance_date <= last,
            *_filters(grade, section, year_id))
    ).all()
    by_class: Dict[tuple, List[StudentAttendance]] = {}
    for record in records:
        by_class.setdefault((record.grade, record.section), []).append(record)
    rows = []
    for class_grade, class_section in all_classes(grade, section):
        class_records = by_class.get((class_grade, class_section), [])
        counts = counts_by_status(class_records)
        rows.append({
            "grade": class_grade, "section": class_section,
            "days_recorded": len({record.attendance_date for record in class_records}),
            "recorded": len(class_records), **counts,
            "attendance_rate": rate(counts[PRESENT], counts[LATE], len(class_records)),
        })
    totals = counts_by_status(records)
    return {"month": first.strftime("%Y-%m"), "first": first.isoformat(), "last": last.isoformat(), "classes": rows,
            "totals": {"recorded": len(records), **totals,
                       "attendance_rate": rate(totals[PRESENT], totals[LATE], len(records))}}


def frequent_absentees(session: Session, first: date, last: date, grade=None, section=None, year_id=None,
                       min_absences: int = 3) -> List[dict]:
    """Students with the most recorded absences. Rates use only the days recorded for that student."""
    records = session.exec(
        select(StudentAttendance).where(
            StudentAttendance.attendance_date >= first, StudentAttendance.attendance_date <= last,
            *_filters(grade, section, year_id))
    ).all()
    per_student: Dict[int, List[StudentAttendance]] = {}
    for record in records:
        per_student.setdefault(record.student_id, []).append(record)
    students = {s.id: s for s in session.exec(
        select(Student).where(col(Student.id).in_(list(per_student) or [0]))).all()}
    rows = []
    for student_id, student_records in per_student.items():
        counts = counts_by_status(student_records)
        if counts[ABSENT] >= min_absences and student_id in students:
            student = students[student_id]
            rows.append({**student_summary(student), "archived": student.archived_at is not None,
                         "days_recorded": len(student_records), **counts,
                         "absence_rate": round(counts[ABSENT] * 100 / len(student_records), 1)})
    return sorted(rows, key=lambda row: (-row[ABSENT], -row["absence_rate"], row["roll_number"]))


def student_history(session: Session, student: Student, first: date, last: date) -> dict:
    records = session.exec(
        select(StudentAttendance).where(
            StudentAttendance.student_id == student.id,
            StudentAttendance.attendance_date >= first, StudentAttendance.attendance_date <= last,
        ).order_by(col(StudentAttendance.attendance_date).desc())
    ).all()
    changes = session.exec(
        select(AttendanceChangeHistory).where(
            AttendanceChangeHistory.student_id == student.id,
            AttendanceChangeHistory.attendance_date >= first, AttendanceChangeHistory.attendance_date <= last,
        ).order_by(col(AttendanceChangeHistory.changed_at).desc())
    ).all()
    names = _names(session, [r.marked_by for r in records] + [c.changed_by for c in changes])
    counts = counts_by_status(records)
    return {
        "student": student_summary(student), "first": first.isoformat(), "last": last.isoformat(),
        "days_recorded": len(records), **counts, "attendance_rate": rate(counts[PRESENT], counts[LATE], len(records)),
        "records": [{"date": r.attendance_date.isoformat(), "status": r.status, "marked_by": names.get(r.marked_by)}
                    for r in records],
        "changes": [{"date": c.attendance_date.isoformat(), "old_status": c.old_status, "new_status": c.new_status,
                     "reason": c.reason, "changed_by": names.get(c.changed_by),
                     "changed_at": utc_iso(c.changed_at)} for c in changes],
    }


def audit_trail(session: Session, first: date, last: date, grade=None, section=None, limit: int = 200) -> List[dict]:
    query = (
        select(AttendanceChangeHistory, StudentAttendance, Student)
        .join(StudentAttendance, StudentAttendance.id == AttendanceChangeHistory.attendance_id)
        .join(Student, Student.id == AttendanceChangeHistory.student_id)
        .where(AttendanceChangeHistory.attendance_date >= first, AttendanceChangeHistory.attendance_date <= last)
        .order_by(col(AttendanceChangeHistory.changed_at).desc())
        .limit(limit)
    )
    if grade:
        query = query.where(StudentAttendance.grade == grade)
    if section:
        query = query.where(StudentAttendance.section == section)
    rows = session.exec(query).all()
    names = _names(session, [change.changed_by for change, _, _ in rows])
    return [{"date": change.attendance_date.isoformat(), "student": student.name, "roll_number": student.roll_number,
             "grade": record.grade, "section": record.section, "old_status": change.old_status,
             "new_status": change.new_status, "reason": change.reason, "changed_by": names.get(change.changed_by),
             "changed_at": utc_iso(change.changed_at)} for change, record, student in rows]


# ── CSV ─────────────────────────────────────────────────────────────────────

def _safe_cell(value) -> str:
    """Spreadsheets run text that starts with = + - @ as a formula, so such text is made plain."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def export_csv(session: Session, first: date, last: date, grade=None, section=None, year_id=None) -> str:
    rows = session.exec(
        select(StudentAttendance, Student)
        .join(Student, Student.id == StudentAttendance.student_id)
        .where(StudentAttendance.attendance_date >= first, StudentAttendance.attendance_date <= last,
               *_filters(grade, section, year_id))
        .order_by(StudentAttendance.attendance_date, StudentAttendance.grade, StudentAttendance.section,
                  Student.roll_number)
    ).all()
    names = _names(session, [record.marked_by for record, _ in rows])
    corrected = set(session.exec(select(AttendanceChangeHistory.attendance_id).distinct()).all())
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Date", "Grade", "Section", "Roll number", "Student", "Status", "Marked by", "Corrected"])
    for record, student in rows:
        writer.writerow([_safe_cell(value) for value in (
            record.attendance_date.isoformat(), record.grade, record.section, student.roll_number, student.name,
            record.status, names.get(record.marked_by), "Yes" if record.id in corrected else "No")])
    return buffer.getvalue()


def report(session: Session, first: date, last: date, grade=None, section=None, year_id=None) -> dict:
    """Everything the printable report shows, over a date range, from recorded attendance only."""
    records = session.exec(
        select(StudentAttendance).where(
            StudentAttendance.attendance_date >= first, StudentAttendance.attendance_date <= last,
            *_filters(grade, section, year_id))
    ).all()
    by_class: Dict[tuple, List[StudentAttendance]] = {}
    for record in records:
        by_class.setdefault((record.grade, record.section), []).append(record)
    enrolled = roster_counts(session)
    classes = []
    for class_grade, class_section in all_classes(grade, section):
        class_records = by_class.get((class_grade, class_section), [])
        counts = counts_by_status(class_records)
        classes.append({"grade": class_grade, "section": class_section,
                        "enrolled": enrolled.get((class_grade, class_section), 0),
                        "days_recorded": len({r.attendance_date for r in class_records}),
                        "recorded": len(class_records), **counts,
                        "attendance_rate": rate(counts[PRESENT], counts[LATE], len(class_records))})
    totals = counts_by_status(records)
    return {"first": first.isoformat(), "last": last.isoformat(), "grade": grade, "section": section,
            "generated_on": school_today().isoformat(), "classes": classes,
            "totals": {"recorded": len(records), **totals,
                       "attendance_rate": rate(totals[PRESENT], totals[LATE], len(records))},
            "frequent_absentees": frequent_absentees(session, first, last, grade, section, year_id)}
