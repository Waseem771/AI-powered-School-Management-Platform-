"""All exam calculations: one exam at a time, and promotion as the exam policy states it.

Every reader of marks goes through here, so the results page, report card, at-risk features,
and chatbot agree. Marks from different exams or years are never added together.
"""
import math
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from sqlmodel import Session, select

from config import SUBJECTS
from models.fee import AcademicYear
from models.result import FINAL_TERM, MIDTERM, Result, calculate_grade

SUBJECT_PASS_PERCENT = 40.0  # knowledge_base/exam_policy.txt, section 3
PROMOTION_AGGREGATE_PERCENT = 50.0
PROMOTION_MIN_SUBJECTS_PASSED = 5
RETAKE_MAX_FAILED_SUBJECTS = 2
DEFAULT_ACADEMIC_YEAR_ID = 1
MIN_SHARED_SUBJECTS_FOR_TREND = 3

ExamKey = Tuple[int, str]


def percentage(obtained: float, total: float) -> float:
    return (obtained / total) * 100.0 if total > 0 else 0.0


def subject_passed(mark: Result) -> bool:
    return percentage(mark.marks_obtained, mark.total_marks) >= SUBJECT_PASS_PERCENT


def _exam_key(mark: Result) -> ExamKey:
    return (mark.academic_year_id or 0, mark.exam_type)


def _recency(key: ExamKey) -> Tuple[int, bool]:
    """Newest year first and, within a year, the final after the midterm."""
    year, exam_type = key
    return (year, exam_type == FINAL_TERM)


def exams_recorded(marks: Iterable[Result]) -> List[ExamKey]:
    return sorted({_exam_key(mark) for mark in marks}, key=_recency, reverse=True)


def latest_exam_marks(marks: Iterable[Result]) -> List[Result]:
    marks = list(marks)
    exams = exams_recorded(marks)
    return [mark for mark in marks if _exam_key(mark) == exams[0]] if exams else []


def select_exam(
    marks: Iterable[Result], exam_type: Optional[str] = None, academic_year_id: Optional[int] = None
) -> List[Result]:
    """The marks of one exam: the latest one that fits the filters."""
    return latest_exam_marks(
        mark
        for mark in marks
        if (exam_type is None or mark.exam_type == exam_type)
        and (academic_year_id is None or mark.academic_year_id == academic_year_id)
    )


def exam_trend(marks: Iterable[Result]) -> Optional[float]:
    """Points gained or lost from the midterm to the final of the same year, or None.

    Compares only subjects in both exams, so a subject missing from one cannot look like a change.
    """
    marks = list(marks)
    exams = exams_recorded(marks)
    if not exams or exams[0][1] != FINAL_TERM:
        return None
    year = exams[0][0]
    final = {mark.subject: mark for mark in marks if _exam_key(mark) == (year, FINAL_TERM)}
    midterm = {mark.subject: mark for mark in marks if _exam_key(mark) == (year, MIDTERM)}
    shared = set(final) & set(midterm)
    if len(shared) < MIN_SHARED_SUBJECTS_FOR_TREND:
        return None

    def shared_percentage(exam: Dict[str, Result]) -> float:
        rows = [exam[subject] for subject in shared]
        return percentage(sum(row.marks_obtained for row in rows), sum(row.total_marks for row in rows))

    return round(shared_percentage(final) - shared_percentage(midterm), 1)


def exam_summary(marks: Sequence[Result]) -> Dict[str, Any]:
    obtained = sum(mark.marks_obtained for mark in marks)
    possible = sum(mark.total_marks for mark in marks)
    return {
        "total_obtained": obtained,
        "total_max": possible,
        "percentage": round(percentage(obtained, possible), 1),
        "grade": calculate_grade(obtained, possible) if possible > 0 else "N/A",
    }


def _decision(status: str, label: str, **details: Any) -> Dict[str, Any]:
    return {
        "status": status,
        "label": label,
        "reasons": [],
        "subjects_passed": None,
        "subjects_required": PROMOTION_MIN_SUBJECTS_PASSED,
        "retake_eligible": False,
        **details,
    }


def promotion_decision(marks: Sequence[Result]) -> Dict[str, Any]:
    """The policy's rule, applied to the marks of a single exam. Says so when it cannot decide."""
    if not marks:
        return _decision("no_marks", "No marks recorded")
    if marks[0].exam_type != FINAL_TERM:
        return _decision("not_applicable", "Promotion is decided on Final Term marks")

    by_subject = {mark.subject: mark for mark in marks if mark.subject in SUBJECTS}
    missing = [subject for subject in SUBJECTS if subject not in by_subject]
    if missing:
        return _decision("incomplete", f"Not decided: marks missing for {', '.join(missing)}")

    core_marks = list(by_subject.values())
    passed = sum(subject_passed(mark) for mark in core_marks)
    failed = len(core_marks) - passed
    obtained = sum(mark.marks_obtained for mark in core_marks)
    possible = sum(mark.total_marks for mark in core_marks)
    aggregate = percentage(obtained, possible)

    reasons = []
    if passed < PROMOTION_MIN_SUBJECTS_PASSED:
        reasons.append(f"Passed {passed} of {len(SUBJECTS)} subjects; at least {PROMOTION_MIN_SUBJECTS_PASSED} of {len(SUBJECTS)} are needed.")
    if aggregate < PROMOTION_AGGREGATE_PERCENT:
        # Rounded down, so a shortfall never reads as if the requirement was met.
        shown = math.floor(aggregate * 10) / 10
        reasons.append(f"Aggregate is {shown:.1f}%; at least {PROMOTION_AGGREGATE_PERCENT:.0f}% is needed.")

    if not reasons:
        return _decision("promoted", "Promoted", subjects_passed=passed)
    return _decision(
        "not_promoted",
        "Not promoted",
        reasons=reasons,
        subjects_passed=passed,
        retake_eligible=1 <= failed <= RETAKE_MAX_FAILED_SUBJECTS,
    )


def current_academic_year_id(session: Session) -> int:
    year = session.exec(select(AcademicYear).where(AcademicYear.is_current == True)).first()  # noqa: E712
    return year.id if year else DEFAULT_ACADEMIC_YEAR_ID


def academic_year_labels(session: Session) -> Dict[int, str]:
    return {year.id: year.label for year in session.exec(select(AcademicYear)).all()}
