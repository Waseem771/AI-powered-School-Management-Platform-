"""Orchestrates policy RAG and read-only school-record tools with structured data output and conversation memory."""

import json
import re
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from config import GROQ_API_KEY, GROQ_MODEL, SCHOOL_NAME
from models.student import Student
from services.data_assistant_service import SchoolDataAssistant


class SchoolAssistantService:
    """Answers policy questions with RAG and record questions through approved tools, with conversation memory."""

    def __init__(self, session: Session):
        self.data = SchoolDataAssistant(session)
        self.session = session

    # ──────────────────────────────────────────────────────────────────────────
    # Public entry point
    # ──────────────────────────────────────────────────────────────────────────

    def answer(self, question: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        question = question.strip()
        history = history or []

        if self._is_data_question(question, history):
            groq_response = self._answer_with_groq_tools(question, history)
            return groq_response or self._answer_with_local_tools(question, history)

        from services.rag_service import rag_service
        result = rag_service.answer_query(question, history=history)
        return {**result, "mode": "policy_rag"}

    # ──────────────────────────────────────────────────────────────────────────
    # Groq function-calling path (with conversation memory)
    # ──────────────────────────────────────────────────────────────────────────

    def _answer_with_groq_tools(
        self, question: str, history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any] | None:
        if not GROQ_API_KEY.strip():
            return None
        try:
            from groq import Groq

            client = Groq(api_key=GROQ_API_KEY.strip())
            system_prompt = (
                f"You are the internal, authenticated data assistant for {SCHOOL_NAME}.\n"
                "You maintain conversational context across turns. If the user refers to pronouns like 'he', 'she', 'his', 'her', 'them', or 'that student', identify the student referenced in previous conversation turns.\n"
                "Use the provided tools to answer questions about students, fees, results, and collections.\n"
                "Key rules:\n"
                "- For 'list students with pending fees', 'who has dues', 'defaulters', ALWAYS call get_students_with_pending_fees.\n"
                "- For 'list all students in grade X', call get_students_by_grade.\n"
                "- For a single student's data, call get_student_profile, get_student_fee_summary, or get_student_results.\n"
                "- Never invent data or write SQL. Summarize what the tools return.\n"
                "- Keep summaries concise — the UI already shows the full table."
            )

            messages = [{"role": "system", "content": system_prompt}]

            # Add recent conversation memory (up to last 10 messages)
            if history:
                for msg in history[-10:]:
                    role = msg.get("role")
                    content = msg.get("content")
                    if role in ("user", "assistant") and content:
                        messages.append({"role": role, "content": str(content)[:1000]})

            messages.append({"role": "user", "content": question})

            first = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                tools=self.data.tool_definitions(),
                tool_choice="auto",
                temperature=0.1,
                max_tokens=600,
            )
            assistant_message = first.choices[0].message
            tool_calls = assistant_message.tool_calls or []
            if not tool_calls:
                return None

            messages.append(assistant_message.model_dump(exclude_none=True))
            executed = []
            tool_results: Dict[str, Any] = {}

            for tool_call in tool_calls[:3]:
                try:
                    arguments = json.loads(tool_call.function.arguments or "{}")
                except json.JSONDecodeError:
                    arguments = {}
                result = self.data.execute_tool(tool_call.function.name, arguments)
                executed.append(tool_call.function.name)
                tool_results[tool_call.function.name] = result
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, default=str),
                })

            final = client.chat.completions.create(
                model=GROQ_MODEL, messages=messages, temperature=0.1, max_tokens=700
            )
            answer = final.choices[0].message.content or "I found the requested school records."
            return {
                "answer": answer,
                "sources": ["School database"],
                "grounded": True,
                "mode": "groq_tool_calling",
                "tools_used": executed,
                "structured_data": self._build_structured_data(executed, tool_results),
            }
        except Exception as error:
            print(f"[School Assistant] Groq tool call error: {error}")
            return None

    # ──────────────────────────────────────────────────────────────────────────
    # Local (no-Groq) fallback path (with conversation memory)
    # ──────────────────────────────────────────────────────────────────────────

    def _answer_with_local_tools(
        self, question: str, history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        lower = question.lower()

        # ── Bulk: pending fees list ─────────────────────────────────────────
        if self._is_pending_list_question(lower):
            grade = self._extract_grade(question)
            data = self.data.get_students_with_pending_fees(grade)
            count = data["count"]
            total = data["total_pending"]
            grade_str = f" in {grade}" if grade else ""
            answer = (
                f"There are {count} student(s){grade_str} with pending fees totalling Rs. {total:,.0f}. "
                "See the table below for full details."
            )
            return self._response(answer, "get_students_with_pending_fees", {"pending_students": data})

        # ── Bulk: students by grade ─────────────────────────────────────────
        grade = self._extract_grade(question)
        if grade and any(w in lower for w in ("list", "all students", "show students", "students in")):
            data = self.data.get_students_by_grade(grade)
            answer = f"Found {data['count']} student(s) in {grade}. See the table below."
            return self._response(answer, "get_students_by_grade", {"grade_students": data})

        # ── School-wide collection summary ──────────────────────────────────
        if self._is_collection_question(lower):
            data = self.data.get_collection_summary()
            answer = (
                f"Fee collection summary: Rs. {data['paid']:,.0f} collected from Rs. {data['invoiced']:,.0f} invoiced "
                f"({data['collection_rate']}% recovery). Pending: Rs. {data['pending']:,.0f} across {data['invoices']} invoices."
            )
            return self._response(answer, "get_collection_summary", {"collection": data})

        # ── Single-student queries ──────────────────────────────────────────
        identifier = self._student_identifier(question, history)
        if not identifier:
            return self._response(
                "Please provide the student's full name or roll number so I can retrieve the correct record.",
                "find_students",
                None,
            )

        if any(w in lower for w in ("fee", "fees", "dues", "challan", "invoice", "payment")):
            data = self.data.get_student_fee_summary(identifier)
            if not data.get("found"):
                return self._response(data["message"], "get_student_fee_summary", None)
            t = data["totals"]
            return self._response(
                f"{data['student']['name']} (roll #{data['student']['roll_number']}) — "
                f"Rs. {t['paid']:,.0f} paid, Rs. {t['pending']:,.0f} pending out of Rs. {t['invoiced']:,.0f} invoiced.",
                "get_student_fee_summary",
                {"fees": data},
            )

        if any(w in lower for w in ("result", "marks", "score", "performance")):
            data = self.data.get_student_results(identifier)
            if not data.get("found"):
                return self._response(data["message"], "get_student_results", None)
            if not data["results"]:
                return self._response(
                    f"No exam results recorded yet for {data['student']['name']}.",
                    "get_student_results",
                    None,
                )
            marks = "; ".join(
                f"{r['subject']}: {r['marks_obtained']}/{r['total_marks']} ({r['grade']})"
                for r in data["results"]
            )
            return self._response(
                f"{data['student']['name']}'s average: {data['average_percentage']}%. {marks}.",
                "get_student_results",
                {"results": data},
            )

        data = self.data.get_student_profile(identifier)
        if not data.get("found"):
            return self._response(data["message"], "get_student_profile", None)
        s = data["student"]
        return self._response(
            f"Student: {s['name']} (roll #{s['roll_number']}), {s['grade']} — {s['section']}. "
            f"Guardian: {s['guardian_name']}; Phone: {s['phone']}.",
            "get_student_profile",
            {"profile": data},
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_structured_data(tools_used: list, tool_results: Dict[str, Any]) -> Dict[str, Any] | None:
        """Map tool names → frontend structured_data keys."""
        mapping = {
            "get_student_profile":            "profile",
            "get_student_fee_summary":        "fees",
            "get_student_results":            "results",
            "get_collection_summary":         "collection",
            "find_students":                  "students",
            "get_students_with_pending_fees": "pending_students",
            "get_students_by_grade":          "grade_students",
        }
        out: Dict[str, Any] = {}
        for tool_name, result in tool_results.items():
            key = mapping.get(tool_name)
            if key:
                out[key] = result
        return out if out else None

    def _student_identifier(
        self, question: str, history: Optional[List[Dict[str, str]]] = None
    ) -> str | None:
        # 1. Try finding in current question
        roll_match = re.search(
            r"\b(?:roll\s*(?:number|no\.?)?\s*#?\s*|#)(\d{1,8})\b", question, re.IGNORECASE
        )
        if roll_match:
            return roll_match.group(1)

        students = self.session.exec(select(Student)).all()
        normalized = question.lower()
        for student in students:
            if student.name.lower() in normalized:
                return student.roll_number

        # 2. If not found in current question, inspect conversation history memory
        if history:
            for prev_msg in reversed(history[-8:]):
                prev_text = str(prev_msg.get("content", "")).lower()
                # Check for roll numbers in previous messages
                prev_roll = re.search(r"\b(?:roll\s*(?:number|no\.?)?\s*#?\s*|#)(\d{1,8})\b", prev_text, re.IGNORECASE)
                if prev_roll:
                    return prev_roll.group(1)
                # Check for student names in previous messages
                for student in students:
                    if student.name.lower() in prev_text:
                        return student.roll_number

        return None

    @staticmethod
    def _extract_grade(question: str) -> str | None:
        """Extract grade mention like 'Grade 8', 'grade 9', 'Class 7'."""
        m = re.search(r"\b(?:grade|class)\s*(\d{1,2})\b", question, re.IGNORECASE)
        if m:
            return f"Grade {m.group(1)}"
        return None

    @staticmethod
    def _is_pending_list_question(lower: str) -> bool:
        if ("pending" in lower or "unpaid" in lower or "defaulter" in lower or "due" in lower) and ("fee" in lower or "student" in lower or "challan" in lower or "invoice" in lower):
            return True
        pending_triggers = (
            "pending fee", "pending fees", "fees pending", "fee pending", "pending dues",
            "unpaid fee", "unpaid dues", "whose fees", "whos fees", "who has dues",
            "who have dues", "defaulter", "fee defaulter", "list all student",
            "all students fee", "students with pending", "students who have",
            "students whose fee", "fee not paid",
        )
        return any(t in lower for t in pending_triggers)

    @staticmethod
    def _is_collection_question(lower: str) -> bool:
        return any(
            p in lower
            for p in ("collection", "total fees", "fee summary", "overall fees", "school fees", "fees collected")
        )

    @staticmethod
    def _is_data_question(question: str, history: Optional[List[Dict[str, str]]] = None) -> bool:
        lower = question.lower()
        # Policy keywords → send to RAG, not DB
        policy_overrides = (
            "policy", "refund", "uniform", "conduct", "calendar",
            "surcharge", "discount", "concession", "retake", "grade scale",
            "passing", "criteria", "what is the fee", "attendance rule",
        )
        if any(kw in lower for kw in policy_overrides):
            return False

        # DB record keywords
        data_keywords = (
            "student", "roll", "dues", "challan", "invoice", "payment",
            "collection", "marks", "result", "record", "profile",
            "find", "show me", "look up", "lookup", "who is", "list",
            "pending fee", "unpaid", "defaulter", "fee status", "fee record",
            "all students", "grade students",
        )
        if any(kw in lower for kw in data_keywords):
            return True

        # Contextual follow-ups referring to a student in memory
        follow_up_pronouns = (
            "his", "her", "he", "she", "their", "them", "that student",
            "what about", "and his", "and her", "his fees", "her fees",
            "his marks", "her marks", "phone number", "guardian", "details",
        )
        if history and any(p in lower for p in follow_up_pronouns):
            return True

        return False

    @staticmethod
    def _response(answer: str, tool: str, structured_data: Dict[str, Any] | None) -> Dict[str, Any]:
        return {
            "answer": answer,
            "sources": ["School database"],
            "grounded": True,
            "mode": "school_data",
            "tools_used": [tool],
            "structured_data": structured_data,
        }
