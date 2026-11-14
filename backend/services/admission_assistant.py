"""Help for admissions staff. It never decides anything and never scores an applicant.

Everything here is built from the application on our own server, so no applicant details leave it.
Only a policy question, typed by staff, goes to the existing policy search, which may use Groq.
Staff must read every draft before using it.
"""
from typing import Dict, List

from config import SCHOOL_NAME
from models.admission import AdmissionApplication, AdmissionAssessment, AdmissionDocumentChecklist, STATUS_LABELS
from services.admissions import percentage

REVIEW_NOTICE = "Drafted automatically. Please read and correct it before using it."

DOCUMENT_NAMES_UR = {
    "Birth certificate or B-Form": "برتھ سرٹیفکیٹ یا ب فارم",
    "Guardian CNIC copy": "سرپرست کے شناختی کارڈ کی کاپی",
    "Previous school leaving certificate": "سابقہ اسکول کا لیونگ سرٹیفکیٹ",
    "Previous result card": "سابقہ نتیجے کا کارڈ",
    "Passport-size photographs": "پاسپورٹ سائز تصاویر",
}

POLICY_UNAVAILABLE = "The policy assistant is not available right now. Admissions work is not affected. Please check the school's written policy."


def missing_documents(checklist: List[AdmissionDocumentChecklist]) -> List[str]:
    return [item.name for item in checklist if not item.received]


def draft_reminder(application: AdmissionApplication, missing: List[str], language: str) -> Dict:
    if not missing:
        return {"draft": None, "message": "All required documents have been received.", "missing_documents": []}

    if language == "ur":
        lines = "\n".join(f"- {DOCUMENT_NAMES_UR.get(name, name)}" for name in missing)
        body = (
            f"محترم {application.guardian_name}،\n\n"
            f"السلام علیکم۔ {SCHOOL_NAME} میں {application.student_name} کے داخلے کی درخواست "
            f"(نمبر {application.application_number}) موصول ہو چکی ہے۔ درخواست مکمل کرنے کے لیے "
            f"براہ کرم درج ذیل کاغذات جمع کروائیں:\n\n{lines}\n\n"
            f"شکریہ۔\n{SCHOOL_NAME} داخلہ دفتر"
        )
    else:
        lines = "\n".join(f"- {name}" for name in missing)
        body = (
            f"Dear {application.guardian_name},\n\n"
            f"Assalam-o-Alaikum. We have received the admission application for {application.student_name} "
            f"(application number {application.application_number}) at {SCHOOL_NAME}. "
            f"To complete it, please submit the following documents:\n\n{lines}\n\n"
            f"Thank you.\n{SCHOOL_NAME} Admissions Office"
        )
    return {"draft": body, "language": language, "missing_documents": missing, "review_required": True, "notice": REVIEW_NOTICE}


def summarize_application(
    application: AdmissionApplication,
    checklist: List[AdmissionDocumentChecklist],
    assessments: List[AdmissionAssessment],
) -> Dict:
    """Plain facts from the record, in reading order. No opinion on whether to admit."""
    missing = missing_documents(checklist)
    lines = [
        f"Application {application.application_number}, received {application.application_date.isoformat()}. "
        f"Status: {STATUS_LABELS[application.status]}.",
        f"Applicant: {application.student_name}, applying for {application.applying_grade}.",
    ]
    if application.previous_school or application.previous_class:
        previous = ", ".join(part for part in (application.previous_class, application.previous_school) if part)
        lines.append(f"Previous school: {previous}.")
    if application.previous_performance:
        lines.append(f"Previous performance (as reported): {application.previous_performance}.")
    lines.append(f"Guardian: {application.guardian_name} ({application.guardian_relationship}).")
    lines.append(f"Documents: {len(checklist) - len(missing)} of {len(checklist)} received." + (f" Missing: {', '.join(missing)}." if missing else ""))
    if assessments:
        for item in assessments:
            lines.append(
                f"{item.subject} on {item.test_date.isoformat()}: {item.obtained_marks:g} of {item.max_marks:g} "
                f"({percentage(item.obtained_marks, item.max_marks):g}%)."
            )
    else:
        lines.append("No entry test or interview recorded yet.")
    if application.staff_notes:
        lines.append(f"Staff notes: {application.staff_notes}")
    return {"summary": "\n".join(lines), "review_required": True, "notice": REVIEW_NOTICE}


def explain_policy(question: str, rag) -> Dict:
    """Answers only from the school's policy files. Anything weak or broken says so and moves on."""
    try:
        result = rag.answer_query(question)
    except Exception as error:
        print(f"[Admissions] Policy assistant failed: {type(error).__name__}")
        return {"available": False, "answer": None, "sources": [], "grounded": False, "message": POLICY_UNAVAILABLE}
    grounded = bool(result.get("grounded"))
    return {
        "available": True,
        "answer": result.get("answer") if grounded else None,
        "sources": result.get("sources", []) if grounded else [],
        "grounded": grounded,
        "message": None if grounded else "No school policy covers this question, so there is no answer to give.",
        "notice": REVIEW_NOTICE,
    }
