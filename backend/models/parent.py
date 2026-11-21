"""Parent Portal tables. New tables only: create_all adds them and no existing table changes.

A parent is an ordinary row in `users` with role "parent". `parent_student_links` says which
students (children) that account may see. `published_exams` says which exams the school has
released to parents; marks of any other exam stay hidden from the portal.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ParentStudentLink(SQLModel, table=True):
    """One parent account may see one student. A parent may have many children."""

    __tablename__ = "parent_student_links"
    __table_args__ = (UniqueConstraint("parent_id", "student_id", name="uq_parent_student"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    parent_id: int = Field(foreign_key="users.id", index=True)
    student_id: int = Field(foreign_key="students.id", index=True)
    relationship: Optional[str] = Field(default=None)  # Father, Mother or Guardian, as the office records it
    created_by: Optional[int] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=_now)


class PublishedExam(SQLModel, table=True):
    """An exam (one session, one exam type) whose results parents may see."""

    __tablename__ = "published_exams"
    __table_args__ = (UniqueConstraint("academic_year_id", "exam_type", name="uq_published_exam"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    academic_year_id: int = Field(index=True)
    exam_type: str
    published_by: Optional[int] = Field(default=None, foreign_key="users.id")
    published_at: datetime = Field(default_factory=_now)
