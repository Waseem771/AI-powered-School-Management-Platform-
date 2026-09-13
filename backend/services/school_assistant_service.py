"""Orchestrates policy RAG and read-only school-record tools."""

import json
import re
from typing import Any, Dict

from sqlmodel import Session, select

from config import GROQ_API_KEY, GROQ_MODEL, SCHOOL_NAME
from models.student import Student
from services.data_assistant_service import SchoolDataAssistant


class SchoolAssistantService:
    """Answers policy questions with RAG and record questions through approved tools."""

    def __init__(self, session: Session):
        self.data = SchoolDataAssistant(session)
        self.session = session

    def answer(self, question: str) -> Dict[str, Any]:
        question = question.strip()
        if self._is_data_question(question):
            groq_response = self._answer_with_groq_tools(question)
            return groq_response or self._answer_with_local_tools(question)

        from services.rag_service import rag_service

        result = rag_service.answer_query(question)
        return {**result, "mode": "policy_rag"}

    def _answer_with_groq_tools(self, question: str) -> Dict[str, Any] | None:
        if not GROQ_API_KEY.strip():
            return None
        try:
            from groq import Groq

            client = Groq(api_key=GROQ_API_KEY.strip())
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"You are the internal, authenticated data assistant for {SCHOOL_NAME}. "
                        "For student, fee, results, or collection questions, call only the provided tools. "
                        "Never invent database facts, never generate SQL, and only summarize returned tool data. "
                        "If a student cannot be identified, ask for their name or roll number."
                    ),
                },
                {"role": "user", "content": question},
            ]
            first = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                tools=self.data.tool_definitions(),
                tool_choice="auto",
                temperature=0.1,
                max_tokens=500,
            )
            assistant_message = first.choices[0].message
            tool_calls = assistant_message.tool_calls or []
            if not tool_calls:
                return None

            messages.append(assistant_message.model_dump(exclude_none=True))
            executed = []
            for tool_call in tool_calls[:3]:
                try:
                    arguments = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    arguments = {}
                result = self.data.execute_tool(tool_call.function.name, arguments)
                executed.append(tool_call.function.name)
                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(result, default=str)})

            final = client.chat.completions.create(model=GROQ_MODEL, messages=messages, temperature=0.1, max_tokens=500)
            answer = final.choices[0].message.content or "I found the requested school records."
            return {"answer": answer, "sources": ["School database"], "grounded": True, "mode": "groq_tool_calling", "tools_used": executed}
        except Exception as error:
            print(f"[School Assistant] Groq tool call fallback: {error}")
            return None

    def _answer_with_local_tools(self, question: str) -> Dict[str, Any]:
        lower_question = question.lower()
        if self._is_collection_question(lower_question):
            data = self.data.get_collection_summary()
            answer = (
                f"Fee collection summary: Rs. {data['paid']:,.0f} collected from Rs. {data['invoiced']:,.0f} invoiced "
                f"({data['collection_rate']}% recovery). Pending dues are Rs. {data['pending']:,.0f} across {data['invoices']} invoices."
            )
            return self._response(answer, "get_collection_summary")

        identifier = self._student_identifier(question)
        if not identifier:
            return self._response("Please provide the student's full name or roll number so I can retrieve the correct school record.", "find_students")

        if any(word in lower_question for word in ("fee", "fees", "dues", "challan", "invoice", "payment")):
            data = self.data.get_student_fee_summary(identifier)
            if not data.get("found"):
                return self._response(data["message"], "get_student_fee_summary")
            totals = data["totals"]
            return self._response(
                f"{data['student']['name']} (roll #{data['student']['roll_number']}) has Rs. {totals['paid']:,.0f} paid and Rs. {totals['pending']:,.0f} pending out of Rs. {totals['invoiced']:,.0f} invoiced.",
                "get_student_fee_summary",
            )

        if any(word in lower_question for word in ("result", "marks", "grade", "performance", "score")):
            data = self.data.get_student_results(identifier)
            if not data.get("found"):
                return self._response(data["message"], "get_student_results")
            if not data["results"]:
                return self._response(f"No exam results are recorded yet for {data['student']['name']}.", "get_student_results")
            marks = "; ".join(f"{item['subject']}: {item['marks_obtained']}/{item['total_marks']} ({item['grade']})" for item in data["results"])
            return self._response(f"{data['student']['name']}'s average is {data['average_percentage']}%. {marks}.", "get_student_results")

        data = self.data.get_student_profile(identifier)
        if not data.get("found"):
            return self._response(data["message"], "get_student_profile")
        student = data["student"]
        return self._response(f"Student record: {student['name']} (roll #{student['roll_number']}), {student['grade']} section {student['section']}. Guardian: {student['guardian_name']}; contact: {student['phone']}.", "get_student_profile")

    def _student_identifier(self, question: str) -> str | None:
        roll_match = re.search(r"(?:roll(?:\s*(?:number|no\.?))?\s*#?\s*|#)(\d{1,8})\b", question, re.IGNORECASE)
        if roll_match:
            return roll_match.group(1)
        students = self.session.exec(select(Student)).all()
        normalized_question = question.lower()
        for student in students:
            if student.name.lower() in normalized_question:
                return student.roll_number
        return None

    @staticmethod
    def _is_collection_question(question: str) -> bool:
        return any(phrase in question for phrase in ("collection", "total fees", "fee summary", "overall fees", "school fees", "fees collected"))

    @staticmethod
    def _is_data_question(question: str) -> bool:
        lower_question = question.lower()
        return any(word in lower_question for word in ("student", "roll", "fee", "dues", "challan", "invoice", "payment", "collection", "marks", "result", "grade", "record"))

    @staticmethod
    def _response(answer: str, tool: str) -> Dict[str, Any]:
        return {"answer": answer, "sources": ["School database"], "grounded": True, "mode": "school_data", "tools_used": [tool]}
