"""Read-only, allowlisted database tools for the school AI assistant."""

from typing import Any, Dict, List, Optional, Tuple

from sqlmodel import Session, col, or_, select

from config import GRADES
from models.fee import Invoice
from models.result import Result, calculate_grade
from models.student import Student
from services import chat_intent, school_reports
from services.academics import exam_summary, select_exam
from services.assistant_tools import TOOL_DEFINITIONS
from services.fee_ledger import STATUS_PAID, monthly_totals, outstanding_balance, paid_by_invoice, school_totals
from services.student_lookup import find_matching_students, student_brief

_MAX_QUERY_LENGTH = 80
_MAX_AMBIGUOUS_MATCHES = 10
_MAX_TOP_STUDENTS = 50


def _like_pattern(text: str) -> str:
    """A % or _ typed by a person is a character to find, not a wildcard."""
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _optional_text(value: Any) -> Optional[str]:
    text = str(value).strip() if value is not None else ""
    return None if text.lower() in ("", "null", "none") else text


def _optional_exam(value: Any) -> Optional[str]:
    text = _optional_text(value)
    return chat_intent.extract_exam(text) if text else None


def _clamped_limit(value: Any) -> int:
    try:
        return max(1, min(int(value), _MAX_TOP_STUDENTS))
    except (TypeError, ValueError):
        return chat_intent.DEFAULT_TOP_STUDENTS


class SchoolDataAssistant:
    """Provides safe, small record sets to an LLM without exposing SQL access."""

    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def tool_definitions() -> List[Dict[str, Any]]:
        return TOOL_DEFINITIONS

    # ── Finding students ──────────────────────────────────────────────────────

    def find_students(self, query: str, grade: Optional[str] = None) -> List[Dict[str, Any]]:
        query = str(query or "").strip()[:_MAX_QUERY_LENGTH]
        if not query:
            return []
        match = _like_pattern(query)
        stmt = select(Student).where(
            or_(
                col(Student.name).ilike(match, escape="\\"),
                col(Student.roll_number).ilike(match, escape="\\"),
                col(Student.guardian_name).ilike(match, escape="\\"),
                col(Student.phone).ilike(match, escape="\\"),
            )
        )
        grade = chat_intent.normalise_grade(grade)
        if grade:
            stmt = stmt.where(Student.grade == grade)
        return [student_brief(s) for s in self.session.exec(stmt.order_by(Student.name).limit(20)).all()]

    def _one_student(self, identifier: Any) -> Tuple[Optional[Student], Optional[Dict[str, Any]]]:
        """The student, or else a result saying none or several matched. Never picks among several."""
        matches = find_matching_students(self.session, identifier)
        if len(matches) == 1:
            return matches[0], None
        searched = str(identifier or "").strip()[:_MAX_QUERY_LENGTH]
        if not matches:
            return None, {"found": False, "message": f"No student matched '{searched}'."}
        return None, {
            "found": False,
            "ambiguous": True,
            "message": f"{len(matches)} students match '{searched}'. Ask which one is meant, by roll number.",
            "matches": [student_brief(s) for s in matches[:_MAX_AMBIGUOUS_MATCHES]],
        }

    # ── School-wide lists ─────────────────────────────────────────────────────

    def get_students_with_pending_fees(self, grade: Optional[str] = None) -> Dict[str, Any]:
        """Return all students who still owe money on at least one invoice."""
        grade = chat_intent.normalise_grade(grade)
        open_invoices = self.session.exec(select(Invoice).where(Invoice.status != STATUS_PAID)).all()
        paid = paid_by_invoice(self.session)

        student_pending: Dict[int, float] = {}
        student_invoice_count: Dict[int, int] = {}
        for inv in open_invoices:
            balance = outstanding_balance(inv.amount, paid.get(inv.id, 0.0))
            student_pending[inv.student_id] = student_pending.get(inv.student_id, 0.0) + balance
            student_invoice_count[inv.student_id] = student_invoice_count.get(inv.student_id, 0) + 1

        if not student_pending:
            return {"count": 0, "students": [], "total_pending": 0.0, "grade_filter": grade}

        students_stmt = select(Student).where(col(Student.id).in_(list(student_pending)))
        if grade:
            students_stmt = students_stmt.where(Student.grade == grade)

        rows = [
            {
                **student_brief(s),
                "guardian_name": s.guardian_name,
                "phone": s.phone,
                "pending_amount": round(student_pending.get(s.id, 0.0), 2),
                "pending_invoices": student_invoice_count.get(s.id, 0),
            }
            for s in self.session.exec(students_stmt).all()
        ]
        rows.sort(key=lambda row: (-row["pending_amount"], row["name"]))
        return {
            "count": len(rows),
            "students": rows,
            "total_pending": round(sum(r["pending_amount"] for r in rows), 2),
            "grade_filter": grade,
        }

    def get_students_by_grade(self, grade: str, section: Optional[str] = None) -> Dict[str, Any]:
        """Return the current students in a given grade, optionally one section."""
        grade = chat_intent.normalise_grade(grade)
        if not grade:
            return {"count": 0, "students": [], "grade": grade, "section": section}
        if grade not in GRADES:
            return {
                "count": 0, "students": [], "grade": grade, "section": section,
                "message": f"{grade} is not a grade at this school. Grades are {GRADES[0]} to {GRADES[-1]}.",
            }

        stmt = select(Student).where(Student.grade == grade, col(Student.archived_at).is_(None))
        if section:
            stmt = stmt.where(Student.section == section.strip().upper()[:4])
        rows = [
            {**student_brief(s), "guardian_name": s.guardian_name, "phone": s.phone}
            for s in self.session.exec(stmt.order_by(Student.section, Student.name)).all()
        ]
        return {"count": len(rows), "students": rows, "grade": grade, "section": section}

    # ── One student ───────────────────────────────────────────────────────────

    def get_student_profile(self, student_identifier: str) -> Dict[str, Any]:
        student, problem = self._one_student(student_identifier)
        if problem:
            return problem
        return {
            "found": True,
            "student": {
                **student_brief(student),
                "guardian_name": student.guardian_name,
                "phone": student.phone,
                "date_of_birth": student.dob,
            },
        }

    def get_student_fee_summary(self, student_identifier: str) -> Dict[str, Any]:
        student, problem = self._one_student(student_identifier)
        if problem:
            return problem
        invoices = self.session.exec(
            select(Invoice).where(Invoice.student_id == student.id).order_by(Invoice.created_at.desc())
        ).all()
        paid_amounts = paid_by_invoice(self.session, [i.id for i in invoices])
        return {
            "found": True,
            "student": student_brief(student),
            "totals": {
                "invoiced": round(sum(i.amount for i in invoices), 2),
                "paid": round(sum(paid_amounts.values()), 2),
                "pending": round(sum(outstanding_balance(i.amount, paid_amounts.get(i.id, 0.0)) for i in invoices), 2),
            },
            "invoices": [
                {
                    "challan_number": i.challan_number,
                    "month": i.month,
                    "amount": i.amount,
                    "amount_paid": paid_amounts.get(i.id, 0.0),
                    "balance": outstanding_balance(i.amount, paid_amounts.get(i.id, 0.0)),
                    "due_date": i.due_date,
                    "status": i.status,
                }
                for i in invoices[:12]
            ],
        }

    def get_student_results(self, student_identifier: str, exam_type: Optional[str] = None) -> Dict[str, Any]:
        student, problem = self._one_student(student_identifier)
        if problem:
            return problem
        results = select_exam(
            self.session.exec(select(Result).where(Result.student_id == student.id).order_by(Result.subject)).all(),
            exam_type,
        )
        return {
            "found": True,
            "student": student_brief(student),
            "exam_type": results[0].exam_type if results else exam_type,
            "average_percentage": exam_summary(results)["percentage"] if results else None,
            "results": [
                {
                    "subject": r.subject,
                    "marks_obtained": r.marks_obtained,
                    "total_marks": r.total_marks,
                    "grade": calculate_grade(r.marks_obtained, r.total_marks),
                    "exam_type": r.exam_type,
                }
                for r in results
            ],
        }

    def get_student_risk(self, student_identifier: str) -> Dict[str, Any]:
        student, problem = self._one_student(student_identifier)
        if problem:
            return problem
        brief = student_brief(student)
        if student.archived_at is not None:
            return {"found": True, "student": brief, "estimate": None, "message": "Archived students are not estimated."}
        estimate = school_reports.student_risk_estimate(self.session, student)
        if estimate is None:
            return {"found": True, "student": brief, "estimate": None, "message": "No marks are recorded, so there is no estimate."}
        return {"found": True, "student": brief, "estimate": estimate, "note": school_reports.RISK_NOTE}

    # ── School-wide figures ───────────────────────────────────────────────────

    def get_collection_summary(self) -> Dict[str, Any]:
        totals = school_totals(self.session)
        return {
            "invoices": totals["invoice_count"],
            "invoiced": totals["invoiced"],
            "paid": totals["collected"],
            "pending": totals["outstanding"],
            "overdue": totals["overdue"],
            "collection_rate": totals["collection_rate"],
        }

    def get_monthly_collection(self, month: Optional[str] = None) -> Dict[str, Any]:
        return {"month": month, "months": monthly_totals(self.session, month)}

    def get_student_counts(self, grade: Optional[str] = None, section: Optional[str] = None) -> Dict[str, Any]:
        return school_reports.student_counts(self.session, chat_intent.normalise_grade(grade), section)

    def get_top_students(self, grade: Optional[str] = None, limit: Any = None, exam_type: Optional[str] = None) -> Dict[str, Any]:
        return school_reports.top_students(self.session, chat_intent.normalise_grade(grade), _clamped_limit(limit), exam_type)

    def get_subject_averages(self, grade: Optional[str] = None, exam_type: Optional[str] = None) -> Dict[str, Any]:
        return school_reports.subject_averages(self.session, chat_intent.normalise_grade(grade), exam_type)

    def get_at_risk_students(self, grade: Optional[str] = None, risk_level: Optional[str] = None) -> Dict[str, Any]:
        return school_reports.at_risk_students(self.session, chat_intent.normalise_grade(grade), risk_level)

    # ── Tool dispatcher ───────────────────────────────────────────────────────

    def execute_tool(self, name: str, arguments: Any) -> Any:
        """Runs an allowlisted tool. A model's bad arguments give an error result, never a crash."""
        args = arguments if isinstance(arguments, dict) else {}
        grade = _optional_text(args.get("grade"))
        section = _optional_text(args.get("section"))
        exam = _optional_exam(args.get("exam_type"))
        identifier = args.get("student_identifier", "")

        tools = {
            "find_students": lambda: self.find_students(args.get("query", ""), grade),
            "get_students_with_pending_fees": lambda: self.get_students_with_pending_fees(grade),
            "get_students_by_grade": lambda: self.get_students_by_grade(grade or "", section),
            "get_student_profile": lambda: self.get_student_profile(identifier),
            "get_student_fee_summary": lambda: self.get_student_fee_summary(identifier),
            "get_student_results": lambda: self.get_student_results(identifier, exam),
            "get_student_risk": lambda: self.get_student_risk(identifier),
            "get_collection_summary": self.get_collection_summary,
            "get_monthly_collection": lambda: self.get_monthly_collection(_optional_text(args.get("month"))),
            "get_student_counts": lambda: self.get_student_counts(grade, section),
            "get_top_students": lambda: self.get_top_students(grade, args.get("limit"), exam),
            "get_subject_averages": lambda: self.get_subject_averages(grade, exam),
            "get_at_risk_students": lambda: self.get_at_risk_students(grade, _optional_text(args.get("risk_level"))),
        }
        if name not in tools:
            return {"error": "This data action is not allowed."}
        try:
            return tools[name]()
        except Exception as error:
            print(f"[School Assistant] Tool {name} failed: {type(error).__name__}")
            return {"error": "This data could not be read."}
