"""Teacher-class assignments and daily student attendance.

New tables only: create_all adds them to an existing database and no existing table changes.
A class is a grade and a section, exactly as students already record it, so nothing about
students, roll numbers or sessions is duplicated here.
"""
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import CheckConstraint, Index, UniqueConstraint
from sqlmodel import Field, SQLModel

PRESENT, ABSENT, LATE, LEAVE = "present", "absent", "late", "leave"
STATUSES = (PRESENT, ABSENT, LATE, LEAVE)
STATUS_LABELS = {PRESENT: "Present", ABSENT: "Absent", LATE: "Late", LEAVE: "Leave"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TeacherClassAssignment(SQLModel, table=True):
    """One teacher teaching one class (grade and section) in one academic session."""

    __tablename__ = "teacher_class_assignments"
    __table_args__ = (
        UniqueConstraint("teacher_id", "grade", "section", "academic_year_id", name="uq_assignment_teacher_class_year"),
        Index("ix_assignment_class", "grade", "section", "academic_year_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    teacher_id: int = Field(foreign_key="users.id", index=True)
    grade: str
    section: str
    academic_year_id: int = Field(foreign_key="academic_years.id", index=True)
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=_now)


class StudentAttendance(SQLModel, table=True):
    """One student's attendance on one day. A student with no row that day has not been recorded,
    which is different from being absent."""

    __tablename__ = "student_attendance"
    __table_args__ = (
        UniqueConstraint("student_id", "attendance_date", name="uq_attendance_student_date"),
        CheckConstraint("status IN ('present', 'absent', 'late', 'leave')", name="ck_attendance_status"),
        Index("ix_attendance_class_date", "grade", "section", "attendance_date"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="students.id", index=True)
    # The class the student was in on that day, so later moves do not rewrite old records.
    grade: str
    section: str
    academic_year_id: int = Field(foreign_key="academic_years.id", index=True)
    attendance_date: date = Field(index=True)
    status: str
    marked_by: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=_now)
    updated_at: datetime = Field(default_factory=_now)


class AttendanceChangeHistory(SQLModel, table=True):
    """Every correction to a submitted record: who, when, from what to what, and why."""

    __tablename__ = "attendance_change_history"

    id: Optional[int] = Field(default=None, primary_key=True)
    attendance_id: int = Field(foreign_key="student_attendance.id", index=True)
    student_id: int = Field(index=True)
    attendance_date: date = Field(index=True)
    old_status: str
    new_status: str
    reason: str
    changed_by: int = Field(foreign_key="users.id")
    changed_at: datetime = Field(default_factory=_now)
