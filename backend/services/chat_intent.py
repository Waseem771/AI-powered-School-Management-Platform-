"""Reads what a chatbot question is about. Pure text work: no database and no AI.

Everything matches whole words, so "the" is never "he" and "enrollment" is never "roll".
"""
import re
from typing import Optional, Tuple

from config import GRADES, SECTIONS

TOPIC_FEES = "fees"
TOPIC_RESULTS = "results"
TOPIC_RISK = "risk"

MONTH_NAMES = (
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
)
_MONTH_ABBREVIATIONS = {name[:3]: name for name in MONTH_NAMES}
_MAX_TOP_STUDENTS = 50
DEFAULT_TOP_STUDENTS = 5

_ROLL = re.compile(
    r"(?:\broll(?:\s*(?:number|num|no\.?))?\s*(?:is|of)?\s*[#:.]?\s*|#)"
    r"([A-Za-z0-9/-]*\d[A-Za-z0-9/-]*)",
    re.IGNORECASE,
)
_BARE_ROLL = re.compile(r"^\s*#?([A-Za-z0-9/-]*\d[A-Za-z0-9/-]*)\s*[.?!]?\s*$")
_STUDENT_ID = re.compile(r"\b(?:student\s+)?id\s*[#:.]?\s*(\d{1,9})\b", re.IGNORECASE)
_GRADE = re.compile(
    r"\b(?:grade|class)\s*-?\s*(\d{1,2})\b|\b(\d{1,2})(?:st|nd|rd|th)\s+(?:grade|class)\b",
    re.IGNORECASE,
)
_SECTION_WORD = re.compile(r"\bsection\s*-?\s*([A-Za-z])\b", re.IGNORECASE)
_SECTION_AFTER_GRADE = re.compile(r"\b(?i:grade|class)\s*-?\s*\d{1,2}\s*-?\s*([A-Z])\b")
_MONTH = re.compile(
    r"\b(" + "|".join(MONTH_NAMES) + r"|" + "|".join(_MONTH_ABBREVIATIONS) + r")\b\.?\s*(?:,\s*)?(\d{4})?",
    re.IGNORECASE,
)
_TOP_COUNT = re.compile(r"\btop\s+(\d{1,3})\b", re.IGNORECASE)


def _pattern(*alternatives: str) -> re.Pattern:
    return re.compile(r"\b(?:" + "|".join(alternatives) + r")\b", re.IGNORECASE)


# Words that always mean the policy documents, whoever is named.
_POLICY_WORDS = _pattern(
    "polic(?:y|ies)", "refunds?", "uniforms?", "conduct", "calendar", "surcharges?", "discounts?",
    "concessions?", "scholarships?", "attendance rules?", "holidays?", "vacations?", "admissions?",
    "late fees?", "fee structure", "what is the fee", "how (?:do|can) i pay", "rules?",
)
# Words that mean the policy documents unless a student is named: "Is Zoya passing?"
_SOFT_POLICY_WORDS = _pattern("passing", "criteria", "retakes?", "grading", "grade scale", "promotion rule")

_PENDING = re.compile(
    r"\bdefaulters?\b"
    r"|\b(?:pending|unpaid|outstanding)\b.*\b(?:fees?|students?|challans?|invoices?|dues|list|who)\b"
    r"|\b(?:fees?|students?|challans?|invoices?|dues|who|whose)\b.*\b(?:pending|unpaid|outstanding|not paid)\b"
    r"|\bwho(?:se)?\b.*\b(?:owes?|dues)\b",
    re.IGNORECASE,
)
_GRADE_LIST = re.compile(
    r"\b(?:list|show|all|who are|names? of)\b.*\bstudents?\b"
    r"|\bstudents?\s+(?:in|of|from)\b"
    r"|\b(?:grade|class)\s*\d{1,2}\s*-?\s*[A-Za-z]?\s+students?\b",
    re.IGNORECASE,
)
_COUNT = re.compile(
    r"\bhow many\s+(?:\w+\s+)?students?\b|\b(?:total|number of|count of)\s+students?\b|\bstudent (?:count|strength)\b",
    re.IGNORECASE,
)
# A count of "students who failed" is a different number from a count of students.
_COUNT_CONDITION = _pattern(
    "fail\\w*", "pass\\w*", "absent", "present", "boys?", "girls?", "male", "female", "paid", "promoted",
    "scored?", "got", "above", "below", "over", "under", "named", "called",
)
_TOP = re.compile(
    r"\btop(?:\s+\d{1,3})?\s+(?:students?|performers?|scorers?|rankers?)\b"
    r"|\btoppers?\b|\bposition holders?\b|\bbest students?\b|\bhighest (?:marks|scor\w+|percentage)\b",
    re.IGNORECASE,
)
_SUBJECT_AVERAGE = re.compile(
    r"\bsubject(?:s|-wise| wise)?\s+(?:averages?|performance)\b|\baverages?\b.*\bsubjects?\b"
    r"|\b(?:weakest|strongest|best|worst)\s+subjects?\b|\b(?:class|school)\s+averages?\b|\baverage marks\b",
    re.IGNORECASE,
)
_AT_RISK = re.compile(
    r"\bat[- ]risk\b|\b(?:high|medium|low)[- ]risk\b|\brisk\s+(?:list|students?|report)\b|\bstruggling\b",
    re.IGNORECASE,
)
_RISK_LEVEL = re.compile(r"\b(high|medium|low)[- ]risk\b", re.IGNORECASE)
_MONTHLY = re.compile(r"\b(?:monthly|month[- ]wise|by month|each month|per month)\b", re.IGNORECASE)
_MONEY_WORD = _pattern("collect\\w*", "fees?", "invoice\\w*", "paid", "payments?", "pending", "outstanding", "recovery")
_COLLECTION = re.compile(
    r"\bcollect(?:ion|ed)\b|\brecovery\b|\btotal (?:fees?|pending|outstanding|overdue)\b"
    r"|\bfees? summary\b|\boverall fees?\b",
    re.IGNORECASE,
)
_RISK_TOPIC = re.compile(r"\bat[- ]risk\b|\brisk\b", re.IGNORECASE)
_FEE_TOPIC = _pattern("fees?", "dues", "challans?", "invoices?", "payments?", "paid", "pay", "balance", "owes?")
_RESULT_TOPIC = re.compile(
    r"\b(?:results?|marks?|scores?|scored|performance|percentage|average|report card|exams?)\b"
    r"|\bgrades?\b(?!\s*-?\s*\d)",
    re.IGNORECASE,
)
_PROFILE_TOPIC = _pattern("profile", "phone", "guardian", "father", "contact", "details", "dob", "birth", "address", "record")
_DATA_REQUEST = _pattern(
    "find", "search", "look ?up", "show", "list", "who is", "how many", "marks?", "results?", "dues",
    "invoices?", "profile", "records?", "challans?", "roll", "payments?",
)
_FOLLOW_UP = _pattern(
    "his", "her", "hers", "he", "she", "him", "their", "them", "that student", "this student",
    "same student", "what about",
)
_ONLY_A_TOPIC = re.compile(
    r"^\W*(?:and\s+|also\s+)?(?:the\s+)?"
    r"(?:fees?|dues|marks?|results?|profile|phone(?: number)?|guardian|details|risk)\W*$",
    re.IGNORECASE,
)


def explicit_student_id(text: str) -> Optional[int]:
    match = _STUDENT_ID.search(text)
    return int(match.group(1)) if match else None


def explicit_roll(text: str) -> Optional[str]:
    match = _ROLL.search(text)
    return match.group(1) if match else None


def all_explicit_rolls(text: str) -> list:
    return _ROLL.findall(text)


def bare_roll(text: str) -> Optional[str]:
    """A reply that is nothing but a roll number, such as "045"."""
    match = _BARE_ROLL.match(text)
    return match.group(1) if match else None


def normalise_grade(value: object) -> Optional[str]:
    """Accepts "8", "grade 8", or "Class 8" and returns "Grade 8"."""
    text = str(value or "").strip()
    match = re.fullmatch(r"(?:(?:grade|class)\s*-?\s*)?(\d{1,2})", text, re.IGNORECASE)
    if match:
        return f"Grade {int(match.group(1))}"
    return text[:32] or None


def extract_grade(text: str) -> Optional[str]:
    match = _GRADE.search(text)
    return f"Grade {int(match.group(1) or match.group(2))}" if match else None


def extract_section(text: str) -> Optional[str]:
    match = _SECTION_WORD.search(text) or _SECTION_AFTER_GRADE.search(text)
    letter = match.group(1).upper() if match else None
    return letter if letter in SECTIONS else None


def is_known_grade(grade: str) -> bool:
    return grade in GRADES


def extract_exam(text: str) -> Optional[str]:
    if re.search(r"\bmid[- ]?terms?\b", text, re.IGNORECASE):
        return "Midterm"
    if re.search(r"\bfinals?(?:[- ]term)?\b", text, re.IGNORECASE):
        return "Final Term"
    return None


def extract_month(text: str) -> Optional[str]:
    """"October 2026", or "October" when no year was given. "may" alone is too common a word."""
    for match in _MONTH.finditer(text):
        word, year = match.group(1).lower(), match.group(2)
        name = _MONTH_ABBREVIATIONS.get(word, word)
        if word == "may" and not year and match.group(1) != "May":
            continue
        return f"{name.capitalize()} {year}" if year else name.capitalize()
    return None


def extract_top_count(text: str) -> int:
    match = _TOP_COUNT.search(text)
    return max(1, min(int(match.group(1)), _MAX_TOP_STUDENTS)) if match else DEFAULT_TOP_STUDENTS


def extract_risk_level(text: str) -> Optional[str]:
    match = _RISK_LEVEL.search(text)
    return match.group(1).capitalize() if match else None


def topic_of(text: str) -> Optional[str]:
    if _RISK_TOPIC.search(text):
        return TOPIC_RISK
    if _FEE_TOPIC.search(text):
        return TOPIC_FEES
    if _RESULT_TOPIC.search(text):
        return TOPIC_RESULTS
    return None


def asks_for_a_record(text: str) -> bool:
    """Wants something about one student, even though nobody has been named yet."""
    return bool(topic_of(text) or _PROFILE_TOPIC.search(text))


def has_policy_words(text: str) -> bool:
    return bool(_POLICY_WORDS.search(text))


def has_soft_policy_words(text: str) -> bool:
    return bool(_SOFT_POLICY_WORDS.search(text))


def is_follow_up(text: str) -> bool:
    return bool(_FOLLOW_UP.search(text) or _ONLY_A_TOPIC.match(text))


def is_pending_list(text: str) -> bool:
    return bool(_PENDING.search(text))


def is_grade_list(text: str) -> bool:
    return bool(_GRADE_LIST.search(text))


def is_count(text: str) -> bool:
    return bool(_COUNT.search(text)) and not _COUNT_CONDITION.search(text)


def is_unanswerable_count(text: str) -> bool:
    """"How many students failed?" needs a figure the tools do not give."""
    return bool(_COUNT.search(text)) and not is_count(text) and not is_pending_list(text)


def is_top_students(text: str) -> bool:
    return bool(_TOP.search(text))


def is_subject_average(text: str) -> bool:
    return bool(_SUBJECT_AVERAGE.search(text))


def is_at_risk(text: str) -> bool:
    return bool(_AT_RISK.search(text))


def is_monthly_collection(text: str) -> bool:
    if _MONTHLY.search(text):
        return bool(_MONEY_WORD.search(text))
    return bool(extract_month(text) and _MONEY_WORD.search(text))


def is_collection(text: str) -> bool:
    return bool(_COLLECTION.search(text))


def is_school_wide(text: str) -> bool:
    return any(
        check(text)
        for check in (
            is_pending_list, is_grade_list, is_count, is_top_students, is_subject_average,
            is_at_risk, is_monthly_collection, is_collection,
        )
    )


def is_data_request(text: str) -> bool:
    return is_school_wide(text) or bool(_DATA_REQUEST.search(text))


def month_and_year(month: str) -> Tuple[str, Optional[str]]:
    name, _, year = month.partition(" ")
    return name, year or None
