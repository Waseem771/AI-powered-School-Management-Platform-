"""School-wide figures for the chatbot: counts, rankings, subject averages, and risk lists.

Current students only. Rankings and averages use one exam, so marks from different exams are
never compared or added together.
"""
from collections import Counter
from typing import Any, Dict, List, Optional

from sqlmodel import Session, col, select

from config import GRADES, SUBJECTS
from models.result import Result
from models.student import Student
from services.academics import academic_year_labels, exam_summary, percentage, select_exam
from services.ai_service import MODEL_NOTE
from services.risk_assessment import assess_student, assess_students
from services.student_lookup import student_brief

_LISTED_RISK_LEVELS = ("High", "Medium")


def _current_students(session: Session, grade: Optional[str] = None, section: Optional[str] = None) -> List[Student]:
    query = select(Student).where(col(Student.archived_at).is_(None))
    if grade:
        query = query.where(Student.grade == grade)
    if section:
        query = query.where(Student.section == section)
    return list(session.exec(query.order_by(Student.grade, Student.section, Student.name)).all())


def student_counts(session: Session, grade: Optional[str] = None, section: Optional[str] = None) -> Dict[str, Any]:
    students = _current_students(session, grade, section)
    per_class = Counter((student.grade, student.section) for student in students)
    grade_order = {name: index for index, name in enumerate(GRADES)}
    archived = session.exec(select(Student).where(col(Student.archived_at).is_not(None))).all()
    return {
        "total": len(students),
        "grade": grade,
        "section": section,
        "archived": len(archived),
        "classes": [
            {"grade": class_grade, "section": class_section, "students": count}
            for (class_grade, class_section), count in sorted(
                per_class.items(), key=lambda item: (grade_order.get(item[0][0], len(GRADES)), item[0][1])
            )
        ],
    }


def _exam_marks(session: Session, students: List[Student], exam_type: Optional[str]) -> List[Result]:
    ids = [student.id for student in students]
    if not ids:
        return []
    return select_exam(session.exec(select(Result).where(col(Result.student_id).in_(ids))).all(), exam_type)


def _exam_label(session: Session, marks: List[Result]) -> Dict[str, Any]:
    if not marks:
        return {"exam_type": None, "academic_year": None}
    return {
        "exam_type": marks[0].exam_type,
        "academic_year": academic_year_labels(session).get(marks[0].academic_year_id),
    }


def top_students(
    session: Session,
    grade: Optional[str] = None,
    limit: int = 5,
    exam_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Ranks only students with every subject's marks: one subject at 100% is not a top result."""
    students = _current_students(session, grade)
    marks = _exam_marks(session, students, exam_type)

    by_student: Dict[int, List[Result]] = {}
    for mark in marks:
        by_student.setdefault(mark.student_id, []).append(mark)
    complete = {
        student_id: rows for student_id, rows in by_student.items()
        if set(SUBJECTS) <= {row.subject for row in rows}
    }

    rows = [
        {**student_brief(student), **_student_score(complete[student.id])}
        for student in students if student.id in complete
    ]
    rows.sort(key=lambda row: (-row["percentage"], row["name"]))
    return {
        "grade": grade,
        **_exam_label(session, marks),
        "left_out_incomplete": len(by_student) - len(complete),
        "students": _ranked(rows)[:limit],
    }


def _student_score(marks: List[Result]) -> Dict[str, Any]:
    summary = exam_summary(marks)
    return {"percentage": summary["percentage"], "overall_grade": summary["grade"]}


def _ranked(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Equal percentages share a rank."""
    ranked = []
    for position, row in enumerate(rows, start=1):
        tied = bool(ranked) and ranked[-1]["percentage"] == row["percentage"]
        ranked.append({**row, "rank": ranked[-1]["rank"] if tied else position})
    return ranked


def subject_averages(session: Session, grade: Optional[str] = None, exam_type: Optional[str] = None) -> Dict[str, Any]:
    marks = _exam_marks(session, _current_students(session, grade), exam_type)
    by_subject: Dict[str, List[Result]] = {}
    for mark in marks:
        by_subject.setdefault(mark.subject, []).append(mark)
    subjects = [
        {
            "subject": subject,
            "students": len(rows),
            "average_percentage": round(
                percentage(sum(row.marks_obtained for row in rows), sum(row.total_marks for row in rows)), 1
            ),
        }
        for subject, rows in by_subject.items()
    ]
    subjects.sort(key=lambda row: row["average_percentage"], reverse=True)
    return {"grade": grade, **_exam_label(session, marks), "subjects": subjects}


def student_risk_estimate(session: Session, student: Student) -> Optional[Dict[str, Any]]:
    """None when there are not enough marks: a score built on a default would be invented."""
    assessment = assess_student(session, student)
    if assessment["risk_score"] is None:
        return None
    return {
        "risk_score": assessment["risk_score"],
        "risk_category": assessment["risk_category"],
        "top_reasons": assessment["top_reasons"],
    }


def at_risk_students(
    session: Session, grade: Optional[str] = None, risk_level: Optional[str] = None
) -> Dict[str, Any]:
    levels = (risk_level.strip().capitalize(),) if risk_level else _LISTED_RISK_LEVELS
    students = _current_students(session, grade)
    assessments = assess_students(session, students)
    rows = [
        {
            **student_brief(student),
            "risk_score": assessments[student.id]["risk_score"],
            "risk_category": assessments[student.id]["risk_category"],
        }
        for student in students
        if assessments[student.id]["risk_category"] in levels
    ]
    rows.sort(key=lambda row: row["risk_score"], reverse=True)
    return {
        "count": len(rows),
        "grade": grade,
        "levels": list(levels),
        "not_scored": sum(row["risk_score"] is None for row in assessments.values()),
        "note": MODEL_NOTE,
        "students": rows,
    }
