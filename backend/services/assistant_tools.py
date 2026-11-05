"""The read-only tools the language model may call. Implementations are in data_assistant_service."""
from typing import Any, Dict, List


def _tool(name: str, description: str, properties: Dict[str, Any] = None, required: List[str] = None) -> Dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": properties or {}, "required": required or []},
        },
    }


_STUDENT = {
    "student_identifier": {
        "type": "string",
        "description": (
            "The student's roll number or full name. A bare number is always a roll number. "
            "To use an id returned by another tool, write it as id:12."
        ),
    }
}
_GRADE = {"grade": {"type": ["string", "null"], "description": "Optional grade, e.g. 'Grade 8'"}}
_EXAM = {"exam_type": {"type": ["string", "null"], "enum": ["Final Term", "Midterm", None], "description": "Optional. Defaults to the latest exam."}}

TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    _tool(
        "find_students",
        "Search students by name, roll number, guardian name, or phone. Use it to identify a student before fetching their data.",
        {"query": {"type": "string", "description": "Name, roll number, or keyword"}, **_GRADE},
        ["query"],
    ),
    _tool(
        "get_students_with_pending_fees",
        "List every student who still owes money, with their total pending amount. For 'who has dues', 'defaulters', 'pending fees'.",
        _GRADE,
    ),
    _tool(
        "get_students_by_grade",
        "List the current students in one grade, optionally one section.",
        {
            "grade": {"type": "string", "description": "e.g. 'Grade 8'"},
            "section": {"type": ["string", "null"], "description": "Optional section, e.g. 'A'"},
        },
        ["grade"],
    ),
    _tool("get_student_profile", "One student's enrollment record.", _STUDENT, ["student_identifier"]),
    _tool("get_student_fee_summary", "One student's invoices, paid amount, and pending dues.", _STUDENT, ["student_identifier"]),
    _tool(
        "get_student_results",
        "One student's subject marks, grades, and percentage for one exam.",
        {**_STUDENT, **_EXAM},
        ["student_identifier"],
    ),
    _tool(
        "get_student_risk",
        "One student's estimated academic risk. It is an estimate for staff review, never a judgement.",
        _STUDENT,
        ["student_identifier"],
    ),
    _tool("get_collection_summary", "Whole-school fee totals: invoiced, paid, pending, overdue, and recovery rate."),
    _tool(
        "get_monthly_collection",
        "Fee totals for each billing month. A payment counts towards the month of its invoice.",
        {"month": {"type": ["string", "null"], "description": "Optional, e.g. 'October 2026' or 'October'"}},
    ),
    _tool(
        "get_student_counts",
        "How many current students there are, per class, and how many are archived.",
        {**_GRADE, "section": {"type": ["string", "null"], "description": "Optional section, e.g. 'A'"}},
    ),
    _tool(
        "get_top_students",
        "The highest-scoring students in one exam. Only students with marks in every subject are ranked.",
        {**_GRADE, **_EXAM, "limit": {"type": ["integer", "null"], "description": "How many, default 5, at most 50"}},
    ),
    _tool("get_subject_averages", "The average percentage in each subject for one exam.", {**_GRADE, **_EXAM}),
    _tool(
        "get_at_risk_students",
        "Students with a High or Medium estimated academic risk. An estimate for staff review, never a judgement.",
        {**_GRADE, "risk_level": {"type": ["string", "null"], "enum": ["High", "Medium", "Low", None], "description": "Optional"}},
    ),
]
