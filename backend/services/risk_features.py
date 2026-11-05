from typing import Any, Dict, Iterable

from models.result import Result
from services.academics import exam_trend, latest_exam_marks, percentage, subject_passed

MIN_SUBJECTS_FOR_ESTIMATE = 3


def compute_student_features(marks: Iterable[Result]) -> Dict[str, Any]:
    """Single source of truth for the at-risk model's inputs. Marks only: fees are never read here.

    Uses the student's latest exam, so a subject is never counted twice. `grade_trend` is None
    unless a real comparison exists, and `has_enough_marks` is False rather than a made-up average.
    """
    marks = list(marks)
    latest = latest_exam_marks(marks)
    obtained = sum(mark.marks_obtained for mark in latest)
    possible = sum(mark.total_marks for mark in latest)

    return {
        "avg_marks_pct": percentage(obtained, possible) if possible > 0 else None,
        "failing_subjects": sum(1 for mark in latest if not subject_passed(mark)),
        "grade_trend": exam_trend(marks),
        "subjects_counted": len(latest),
        "has_enough_marks": possible > 0 and len(latest) >= MIN_SUBJECTS_FOR_ESTIMATE,
    }
