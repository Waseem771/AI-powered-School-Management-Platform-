from typing import Literal, Optional, get_args

from sqlalchemy import Index
from sqlmodel import SQLModel, Field

RESULT_UNIQUE_INDEX = "uq_results_student_subject_exam_year"

ExamType = Literal["Final Term", "Midterm"]
FINAL_TERM, MIDTERM = get_args(ExamType)


class Result(SQLModel, table=True):
    __tablename__ = "results"
    __table_args__ = (
        Index(RESULT_UNIQUE_INDEX, "student_id", "subject", "exam_type", "academic_year_id", unique=True),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(index=True, foreign_key="students.id")
    subject: str = Field(index=True)
    marks_obtained: float
    total_marks: float = Field(default=100.0)
    exam_type: str = Field(default=FINAL_TERM)
    academic_year_id: Optional[int] = Field(default=1)


def calculate_grade(marks: float, total: float = 100.0) -> str:
    if total <= 0:
        return "N/A"
    pct = (marks / total) * 100.0
    if pct >= 90:
        return "A+"
    elif pct >= 80:
        return "A"
    elif pct >= 70:
        return "B"
    elif pct >= 60:
        return "C"
    elif pct >= 50:
        return "D"
    else:
        return "F"
