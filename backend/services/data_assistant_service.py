"""Read-only, allowlisted database tools for the school AI assistant."""

from typing import Any, Dict, List, Optional

from sqlmodel import Session, col, or_, select

from models.fee import Invoice
from models.result import Result, calculate_grade
from models.student import Student


class SchoolDataAssistant:
    """Provides safe, small record sets to an LLM without exposing SQL access."""

    def __init__(self, session: Session):
        self.session = session

    # ──────────────────────────────────────────────────────────────────────────
    # Tool schema definitions (sent to Groq)
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def tool_definitions() -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "find_students",
                    "description": (
                        "Search students by name, roll number, grade, guardian name, or phone. "
                        "Use when you need to identify a specific student before fetching their data."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Name, roll number, or keyword to search"},
                            "grade": {"type": ["string", "null"], "description": "Optional grade filter e.g. 'Grade 8'"},
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_students_with_pending_fees",
                    "description": (
                        "List ALL students who have one or more PENDING (unpaid) invoices. "
                        "Use this when the user asks 'which students have pending fees', "
                        "'list students with dues', 'show defaulters', or any bulk fee-status query. "
                        "Returns each student with their total pending amount."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "grade": {
                                "type": ["string", "null"],
                                "description": "Optional: filter by grade, e.g. 'Grade 8'",
                            },
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_students_by_grade",
                    "description": (
                        "List all students in a specific grade with their basic info. "
                        "Use when the user asks 'show all students in grade X' or 'list grade 9 students'."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "grade": {"type": "string", "description": "Grade to filter, e.g. 'Grade 8'"},
                        },
                        "required": ["grade"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_student_profile",
                    "description": "Get a single student's full enrollment record using their name, roll number, or ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "student_identifier": {
                                "type": "string",
                                "description": "Student name, roll number, or numeric ID",
                            }
                        },
                        "required": ["student_identifier"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_student_fee_summary",
                    "description": "Get a single student's invoice history, paid amount, and pending dues using their name, roll number, or ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "student_identifier": {
                                "type": "string",
                                "description": "Student name, roll number, or numeric ID",
                            }
                        },
                        "required": ["student_identifier"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_student_results",
                    "description": "Get a single student's subject marks, grades, and average percentage using their name, roll number, or ID.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "student_identifier": {
                                "type": "string",
                                "description": "Student name, roll number, or numeric ID",
                            }
                        },
                        "required": ["student_identifier"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_collection_summary",
                    "description": "Get school-wide fee collection totals: invoiced, paid, pending, and recovery rate.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]

    # ──────────────────────────────────────────────────────────────────────────
    # Tool implementations
    # ──────────────────────────────────────────────────────────────────────────

    def find_students(self, query: str, grade: Optional[str] = None) -> List[Dict[str, Any]]:
        query = (query or "").strip()[:80]
        if not query:
            return []
        match = f"%{query}%"
        stmt = select(Student).where(
            or_(
                Student.name.ilike(match),
                Student.roll_number.ilike(match),
                Student.guardian_name.ilike(match),
                Student.phone.ilike(match),
            )
        )
        if grade:
            stmt = stmt.where(Student.grade == grade.strip()[:32])
        students = self.session.exec(stmt.order_by(Student.name).limit(20)).all()
        return [self._student_brief(s) for s in students]

    def get_students_with_pending_fees(self, grade: Optional[str] = None) -> Dict[str, Any]:
        """Return all students who have at least one pending invoice."""
        # Get all pending invoices
        stmt = select(Invoice).where(Invoice.status == "pending")
        pending_invoices = self.session.exec(stmt).all()

        # Aggregate by student_id
        student_pending: Dict[int, float] = {}
        student_invoice_count: Dict[int, int] = {}
        for inv in pending_invoices:
            student_pending[inv.student_id] = student_pending.get(inv.student_id, 0.0) + inv.amount
            student_invoice_count[inv.student_id] = student_invoice_count.get(inv.student_id, 0) + 1

        if not student_pending:
            return {"count": 0, "students": [], "total_pending": 0.0}

        # Fetch all involved students
        student_ids = list(student_pending.keys())
        students_stmt = select(Student).where(col(Student.id).in_(student_ids)).order_by(Student.grade, Student.name)
        if grade:
            students_stmt = students_stmt.where(Student.grade == grade.strip()[:32])

        students = self.session.exec(students_stmt).all()

        rows = []
        for s in students:
            rows.append({
                **self._student_brief(s),
                "guardian_name": s.guardian_name,
                "phone": s.phone,
                "pending_amount": round(student_pending.get(s.id, 0.0), 2),
                "pending_invoices": student_invoice_count.get(s.id, 0),
            })

        # Sort by pending amount descending
        rows.sort(key=lambda x: x["pending_amount"], reverse=True)

        total_pending = round(sum(r["pending_amount"] for r in rows), 2)
        return {
            "count": len(rows),
            "students": rows,
            "total_pending": total_pending,
            "grade_filter": grade,
        }

    def get_students_by_grade(self, grade: str) -> Dict[str, Any]:
        """Return all students in a given grade."""
        grade = (grade or "").strip()[:32]
        if not grade:
            return {"count": 0, "students": [], "grade": grade}

        students = self.session.exec(
            select(Student).where(Student.grade == grade).order_by(Student.section, Student.name)
        ).all()

        rows = [
            {**self._student_brief(s), "guardian_name": s.guardian_name, "phone": s.phone}
            for s in students
        ]
        return {"count": len(rows), "students": rows, "grade": grade}

    def get_student_profile(self, student_identifier: str) -> Dict[str, Any]:
        student = self._find_student(student_identifier)
        if not student:
            return self._not_found(student_identifier)
        return {
            "found": True,
            "student": {
                **self._student_brief(student),
                "guardian_name": student.guardian_name,
                "phone": student.phone,
                "date_of_birth": student.dob,
            },
        }

    def get_student_fee_summary(self, student_identifier: str) -> Dict[str, Any]:
        student = self._find_student(student_identifier)
        if not student:
            return self._not_found(student_identifier)
        invoices = self.session.exec(
            select(Invoice).where(Invoice.student_id == student.id).order_by(Invoice.created_at.desc())
        ).all()
        invoiced = round(sum(i.amount for i in invoices), 2)
        paid = round(sum(i.amount for i in invoices if i.status == "paid"), 2)
        return {
            "found": True,
            "student": self._student_brief(student),
            "totals": {"invoiced": invoiced, "paid": paid, "pending": round(invoiced - paid, 2)},
            "invoices": [
                {
                    "challan_number": i.challan_number,
                    "month": i.month,
                    "amount": i.amount,
                    "due_date": i.due_date,
                    "status": i.status,
                }
                for i in invoices[:12]
            ],
        }

    def get_student_results(self, student_identifier: str) -> Dict[str, Any]:
        student = self._find_student(student_identifier)
        if not student:
            return self._not_found(student_identifier)
        results = self.session.exec(
            select(Result).where(Result.student_id == student.id).order_by(Result.subject)
        ).all()
        percentage = (
            round(sum((r.marks_obtained / r.total_marks) * 100 for r in results) / len(results), 1)
            if results
            else None
        )
        return {
            "found": True,
            "student": self._student_brief(student),
            "average_percentage": percentage,
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

    def get_collection_summary(self) -> Dict[str, Any]:
        invoices = self.session.exec(select(Invoice)).all()
        invoiced = round(sum(i.amount for i in invoices), 2)
        paid = round(sum(i.amount for i in invoices if i.status == "paid"), 2)
        pending = round(invoiced - paid, 2)
        return {
            "invoices": len(invoices),
            "invoiced": invoiced,
            "paid": paid,
            "pending": pending,
            "collection_rate": round((paid / invoiced) * 100, 1) if invoiced else 0.0,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # Tool dispatcher
    # ──────────────────────────────────────────────────────────────────────────

    def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        grade_arg = arguments.get("grade")
        if grade_arg in (None, "", "null"):
            grade_arg = None

        tools = {
            "find_students": lambda: self.find_students(
                arguments.get("query", ""), grade_arg
            ),
            "get_students_with_pending_fees": lambda: self.get_students_with_pending_fees(
                grade_arg
            ),
            "get_students_by_grade": lambda: self.get_students_by_grade(
                grade_arg or ""
            ),
            "get_student_profile": lambda: self.get_student_profile(
                arguments.get("student_identifier", "")
            ),
            "get_student_fee_summary": lambda: self.get_student_fee_summary(
                arguments.get("student_identifier", "")
            ),
            "get_student_results": lambda: self.get_student_results(
                arguments.get("student_identifier", "")
            ),
            "get_collection_summary": self.get_collection_summary,
        }
        if name not in tools:
            return {"error": "This data action is not allowed."}
        return tools[name]()

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _find_student(self, identifier: str) -> Optional[Student]:
        identifier = (identifier or "").strip()[:80]
        if not identifier:
            return None
        if identifier.isdigit():
            student = self.session.get(Student, int(identifier))
            if student:
                return student
        return self.session.exec(
            select(Student)
            .where(or_(Student.roll_number == identifier, Student.name.ilike(identifier)))
            .order_by(Student.id)
        ).first()

    @staticmethod
    def _student_brief(student: Student) -> Dict[str, Any]:
        return {
            "id": student.id,
            "name": student.name,
            "roll_number": student.roll_number,
            "grade": student.grade,
            "section": student.section,
        }

    @staticmethod
    def _not_found(identifier: str) -> Dict[str, Any]:
        return {"found": False, "message": f"No student matched '{(identifier or '').strip()[:80]}'."}
