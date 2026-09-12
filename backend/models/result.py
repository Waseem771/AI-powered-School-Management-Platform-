from typing import Optional
from sqlmodel import SQLModel, Field

class Result(SQLModel, table=True):
    __tablename__ = "results"

    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(index=True, foreign_key="students.id")
    subject: str = Field(index=True)
    marks_obtained: float
    total_marks: float = Field(default=100.0)
    exam_type: str = Field(default="Final Term")  # Midterm, Final Term
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
