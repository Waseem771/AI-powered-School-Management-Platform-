"""Read-only, allowlisted database tools for the school AI assistant."""

from typing import Any, Dict, List

from sqlmodel import Session, or_, select

from models.fee import Invoice
from models.result import Result, calculate_grade
from models.student import Student


class SchoolDataAssistant:
    """Provides safe, small record sets to an LLM without exposing SQL access."""

    def __init__(self, session: Session):
        self.session = session

    @staticmethod
    def tool_definitions() -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "find_students",
                    "description": "Find students by name, roll number, grade, guardian, or phone. Use before requesting a specific student's data when their identity is unclear.",
                    "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "grade": {"type": "string"}}, "required": ["query"]},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_student_profile",
                    "description": "Get a student's enrollment record using their name, roll number, or ID.",
                    "parameters": {"type": "object", "properties": {"student_identifier": {"type": "string"}}, "required": ["student_identifier"]},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_student_fee_summary",
                    "description": "Get a student's invoice history, paid amount, and pending dues using their name, roll number, or ID.",
                    "parameters": {"type": "object", "properties": {"student_identifier": {"type": "string"}}, "required": ["student_identifier"]},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_student_results",
                    "description": "Get a student's subject marks and average using their name, roll number, or ID.",
                    "parameters": {"type": "object", "properties": {"student_identifier": {"type": "string"}}, "required": ["student_identifier"]},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_collection_summary",
                    "description": "Get school-wide fee collection, paid, pending, and recovery-rate totals.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
        ]

    def find_students(self, query: str, grade: str | None = None) -> List[Dict[str, Any]]:
        query = (query or "").strip()[:80]
        if not query:
            return []
        match = f"%{query}%"
        statement = select(Student).where(or_(
            Student.name.ilike(match), Student.roll_number.ilike(match),
            Student.guardian_name.ilike(match), Student.phone.ilike(match),
        ))
        if grade:
            statement = statement.where(Student.grade == grade.strip()[:32])
        students = self.session.exec(statement.order_by(Student.name).limit(10)).all()
        return [self._student_brief(student) for student in students]

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
        invoices = self.session.exec(select(Invoice).where(Invoice.student_id == student.id).order_by(Invoice.created_at.desc())).all()
        invoiced = round(sum(invoice.amount for invoice in invoices), 2)
        paid = round(sum(invoice.amount for invoice in invoices if invoice.status == "paid"), 2)
        return {
            "found": True,
            "student": self._student_brief(student),
            "totals": {"invoiced": invoiced, "paid": paid, "pending": round(invoiced - paid, 2)},
            "invoices": [{"challan_number": invoice.challan_number, "month": invoice.month, "amount": invoice.amount, "due_date": invoice.due_date, "status": invoice.status} for invoice in invoices[:12]],
        }

    def get_student_results(self, student_identifier: str) -> Dict[str, Any]:
        student = self._find_student(student_identifier)
        if not student:
            return self._not_found(student_identifier)
        results = self.session.exec(select(Result).where(Result.student_id == student.id).order_by(Result.subject)).all()
        percentage = round(sum((result.marks_obtained / result.total_marks) * 100 for result in results) / len(results), 1) if results else None
        return {
            "found": True,
            "student": self._student_brief(student),
            "average_percentage": percentage,
            "results": [{"subject": result.subject, "marks_obtained": result.marks_obtained, "total_marks": result.total_marks, "grade": calculate_grade(result.marks_obtained, result.total_marks), "exam_type": result.exam_type} for result in results],
        }

    def get_collection_summary(self) -> Dict[str, Any]:
        invoices = self.session.exec(select(Invoice)).all()
        invoiced = round(sum(invoice.amount for invoice in invoices), 2)
        paid = round(sum(invoice.amount for invoice in invoices if invoice.status == "paid"), 2)
        pending = round(invoiced - paid, 2)
        return {"invoices": len(invoices), "invoiced": invoiced, "paid": paid, "pending": pending, "collection_rate": round((paid / invoiced) * 100, 1) if invoiced else 0.0}

    def execute_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any] | List[Dict[str, Any]]:
        tools = {
            "find_students": lambda: self.find_students(arguments.get("query", ""), arguments.get("grade")),
            "get_student_profile": lambda: self.get_student_profile(arguments.get("student_identifier", "")),
            "get_student_fee_summary": lambda: self.get_student_fee_summary(arguments.get("student_identifier", "")),
            "get_student_results": lambda: self.get_student_results(arguments.get("student_identifier", "")),
            "get_collection_summary": self.get_collection_summary,
        }
        if name not in tools:
            return {"error": "This data action is not allowed."}
        return tools[name]()

    def _find_student(self, identifier: str) -> Student | None:
        identifier = (identifier or "").strip()[:80]
        if not identifier:
            return None
        if identifier.isdigit():
            student = self.session.get(Student, int(identifier))
            if student:
                return student
        return self.session.exec(select(Student).where(or_(Student.roll_number == identifier, Student.name.ilike(identifier))).order_by(Student.id)).first()

    @staticmethod
    def _student_brief(student: Student) -> Dict[str, Any]:
        return {"id": student.id, "name": student.name, "roll_number": student.roll_number, "grade": student.grade, "section": student.section}

    @staticmethod
    def _not_found(identifier: str) -> Dict[str, Any]:
        return {"found": False, "message": f"No student matched '{(identifier or '').strip()[:80]}'."}
