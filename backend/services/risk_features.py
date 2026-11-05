from typing import Any, Dict, Iterable

from models.fee import Invoice
from models.result import Result
from services.academics import latest_exam_marks, subject_passed

DEFAULT_AVG_PCT = 70.0


def compute_student_features(
    marks: Iterable[Result], invoices: Iterable[Invoice]
) -> Dict[str, Any]:
    """Single source of truth for the at-risk model's four input features.

    Uses the student's latest exam only, so a subject is never counted twice.
    """
    marks = latest_exam_marks(marks)
    invoices = list(invoices)

    if marks:
        total_obtained = sum(m.marks_obtained for m in marks)
        total_possible = sum(m.total_marks for m in marks)
        avg_pct = (
            (total_obtained / total_possible) * 100.0
            if total_possible > 0
            else DEFAULT_AVG_PCT
        )
        failing = sum(1 for m in marks if not subject_passed(m))
    else:
        avg_pct = DEFAULT_AVG_PCT
        failing = 0

    fee_defaults = sum(1 for inv in invoices if inv.status != "paid")

    # Heuristic: no historical marks are stored, so trend is inferred from current marks.
    if failing >= 2:
        grade_trend = -21.0
    elif avg_pct < 55:
        grade_trend = -14.5
    elif avg_pct > 80:
        grade_trend = 6.5
    else:
        grade_trend = 1.0

    return {
        "avg_marks_pct": avg_pct,
        "fee_defaults": fee_defaults,
        "failing_subjects": failing,
        "grade_trend": grade_trend,
    }
