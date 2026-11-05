"""The chatbot's API limits, per-user memory, status, the language-model path, and policy search.

The language model here is a stand-in: nothing in this file calls Groq.
"""
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, select

from conftest import TEST_ADMIN_PASSWORD
from database import engine
from main import app
from models.student import Student
from models.user import User, hash_password
from routers import chatbot
from services import rag_service as rag_module
from services import school_assistant_service as assistant_module
from services.school_assistant_service import SchoolAssistantService

OTHER_USER = "second-office-user"
OTHER_PASSWORD = "second-user-password-1"


@pytest.fixture()
def client():
    return TestClient(app)


def _login(client, username, password):
    response = client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def admin(client):
    return _login(client, "admin", TEST_ADMIN_PASSWORD)


@pytest.fixture()
def other_user(client):
    with Session(engine) as session:
        if not session.exec(select(User).where(User.username == OTHER_USER)).first():
            session.add(User(username=OTHER_USER, password_hash=hash_password(OTHER_PASSWORD)))
            session.commit()
    return _login(client, OTHER_USER, OTHER_PASSWORD)


@pytest.fixture(autouse=True)
def empty_memory():
    chatbot.chat_memory.clear()
    yield
    chatbot.chat_memory.clear()


# ── Limits ────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("payload", [
    {"question": "x" * (chatbot.MAX_QUESTION_LENGTH + 1)},
    {"question": "hello", "session_id": "../../etc"},
    {"question": "hello", "session_id": "x" * 65},
    {"question": "hello", "history": [{"role": "user", "content": "x"}] * (chatbot.MAX_HISTORY_ITEMS + 1)},
    {"question": "hello", "history": [{"role": "user", "content": "x" * (chatbot.MAX_HISTORY_ITEM_LENGTH + 1)}]},
])
def test_oversized_or_malformed_requests_are_refused(client, admin, payload):
    assert client.post("/chatbot/ask", headers=admin, json=payload).status_code == 422


def test_blank_question_is_refused(client, admin):
    assert client.post("/chatbot/ask", headers=admin, json={"question": "   "}).status_code == 400


def test_chat_routes_need_a_login(client):
    assert client.post("/chatbot/ask", json={"question": "hello"}).status_code == 401
    assert client.get("/chatbot/status").status_code == 401
    assert client.get("/chatbot/history/abc").status_code == 401


def test_stored_sessions_are_capped(monkeypatch):
    monkeypatch.setattr(chatbot, "MAX_STORED_SESSIONS", 2)
    for name in ("first", "second", "third"):
        chatbot._remember_turn(("admin", name), "question", "answer")

    assert set(chatbot.chat_memory) == {("admin", "second"), ("admin", "third")}


def test_each_session_keeps_only_the_latest_messages():
    for number in range(chatbot.MAX_MESSAGES_PER_SESSION):
        chatbot._remember_turn(("admin", "long"), f"question {number}", "answer")

    stored = chatbot.chat_memory[("admin", "long")]
    assert len(stored) == chatbot.MAX_MESSAGES_PER_SESSION
    assert stored[-2]["content"] == f"question {chatbot.MAX_MESSAGES_PER_SESSION - 1}"


# ── Memory belongs to one user ────────────────────────────────────────────────

def test_one_user_cannot_read_or_clear_anothers_session(client, admin, other_user):
    session_id = "shared_session_id"
    client.post("/chatbot/ask", headers=admin, json={"question": "Fees for roll number 045", "session_id": session_id})

    assert client.get(f"/chatbot/history/{session_id}", headers=admin).json()["count"] == 2
    assert client.get(f"/chatbot/history/{session_id}", headers=other_user).json()["count"] == 0

    client.delete(f"/chatbot/history/{session_id}", headers=other_user)
    assert client.get(f"/chatbot/history/{session_id}", headers=admin).json()["count"] == 2


def test_one_users_follow_up_does_not_use_anothers_conversation(client, admin, other_user):
    session_id = "shared_session_id"
    client.post("/chatbot/ask", headers=admin, json={"question": "Fees for roll number 045", "session_id": session_id})

    response = client.post("/chatbot/ask", headers=other_user, json={"question": "What are his fees?", "session_id": session_id})

    assert "Which student" in response.json()["answer"]


def test_a_roll_number_reply_works_even_when_the_page_also_sends_older_text(client, admin):
    greeting = {"role": "assistant", "content": "Hello! Try asking: Show roll number 141."}
    first = client.post("/chatbot/ask", headers=admin, json={"question": "Fees of Ahmed", "session_id": "s2", "history": [greeting]}).json()
    assert "Which student" in first["answer"]
    roll = first["structured_data"]["students"][0]["roll_number"]

    history = [greeting, {"role": "user", "content": "Fees of Ahmed"}, {"role": "assistant", "content": first["answer"]}]
    reply = client.post("/chatbot/ask", headers=admin, json={"question": roll, "session_id": "s2", "history": history}).json()

    assert reply["tools_used"] == ["get_student_fee_summary"]
    assert f"#{roll}" in reply["answer"]


def test_the_pages_copy_of_the_conversation_is_used_after_a_restart(client, admin):
    history = [
        {"role": "user", "content": "Show roll number 045"},
        {"role": "assistant", "content": "Student: Ahmed Khan (roll #045)."},
    ]

    reply = client.post("/chatbot/ask", headers=admin, json={"question": "What are his fees?", "session_id": "s3", "history": history}).json()

    assert reply["tools_used"] == ["get_student_fee_summary"]
    assert "#045" in reply["answer"]


def test_memory_off_ignores_earlier_messages(client, admin):
    client.post("/chatbot/ask", headers=admin, json={"question": "Fees for roll number 045", "session_id": "s1"})

    response = client.post("/chatbot/ask", headers=admin, json={"question": "What are his fees?", "session_id": "s1", "use_memory": False})

    assert "Which student" in response.json()["answer"]
    assert response.json()["history_length"] == 0


def test_end_to_end_answer_uses_roll_number_over_id(client, admin):
    answer = client.post("/chatbot/ask", headers=admin, json={"question": "Show roll number 045"}).json()

    assert answer["structured_data"]["profile"]["student"]["roll_number"] == "045"


# ── Status tells the truth ────────────────────────────────────────────────────

def test_status_says_no_language_model_when_there_is_no_key(client, admin):
    status = client.get("/chatbot/status", headers=admin).json()

    assert status["language_model"]["configured"] is False
    assert status["policy_search"]["engine"] in ("not_loaded", "faiss", "tfidf")


# ── The language-model path, with a stand-in for Groq ─────────────────────────

def _tool_call(name, **arguments):
    return SimpleNamespace(id=f"call_{name}", function=SimpleNamespace(name=name, arguments=json.dumps(arguments)))


def _message(content=None, tool_calls=None):
    return SimpleNamespace(
        content=content,
        tool_calls=tool_calls,
        model_dump=lambda exclude_none=True: {"role": "assistant", "content": content or ""},
    )


class FakeGroq:
    """Plays back a list of replies and keeps what it was sent."""
    replies = []
    sent = []
    error = None

    def __init__(self, **_kwargs):
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        FakeGroq.sent.append(json.dumps(kwargs["messages"], default=str))
        if FakeGroq.error:
            raise FakeGroq.error
        return SimpleNamespace(choices=[SimpleNamespace(message=FakeGroq.replies.pop(0))])


@pytest.fixture()
def groq(monkeypatch):
    import groq as groq_package

    FakeGroq.replies, FakeGroq.sent, FakeGroq.error = [], [], None
    monkeypatch.setattr(groq_package, "Groq", FakeGroq)
    monkeypatch.setattr(assistant_module, "GROQ_API_KEY", "stand-in-key")
    monkeypatch.setattr(assistant_module, "_groq_last_call_ok", None)
    return FakeGroq


@pytest.fixture()
def small_school():
    memory = create_engine("sqlite://")
    SQLModel.metadata.create_all(memory)
    with Session(memory) as session:
        session.add_all([
            Student(id=1, name="Ahmed Khan", roll_number="045", grade="Grade 8", section="A", guardian_name="Imran Khan", phone="03001234567"),
            Student(id=2, name="Ahmed Khan", roll_number="077", grade="Grade 9", section="B", guardian_name="Tariq Khan", phone="03007654321"),
            Student(id=45, name="Sana Mir", roll_number="141", grade="Grade 10", section="A", guardian_name="Sohail Mir", phone="03110000000"),
        ])
        session.commit()
        yield session


def test_groq_answer_built_from_a_tool_is_used(groq, small_school):
    groq.replies = [
        _message(tool_calls=[_tool_call("get_student_profile", student_identifier="141")]),
        _message(content="Sana Mir is in Grade 10."),
    ]

    response = SchoolAssistantService(small_school).answer("Show the profile of Sana Mir")

    assert response["mode"] == "groq_tool_calling"
    assert response["answer"] == "Sana Mir is in Grade 10."
    assert response["structured_data"]["profile"]["student"]["roll_number"] == "141"
    assert assistant_module.groq_status()["last_call_ok"] is True


def test_groq_is_not_consulted_when_two_students_share_a_name(groq, small_school):
    response = SchoolAssistantService(small_school).answer("Fees of Ahmed Khan")

    assert groq.sent == []
    assert "Which student" in response["answer"]
    assert response["mode"] == "school_data"


def test_groq_is_told_which_student_was_settled(groq, small_school):
    groq.replies = [_message(tool_calls=[_tool_call("get_student_fee_summary", student_identifier="id:1")]), _message(content="ok")]

    SchoolAssistantService(small_school).answer("Fees for roll number 045")

    assert "id:1" in groq.sent[0]


def test_a_groq_reply_with_no_tool_call_is_not_passed_off_as_school_data(groq, small_school):
    groq.replies = [_message(content="Sana Mir owes Rs. 99,999.")]

    response = SchoolAssistantService(small_school).answer("Show the marks of Sana Mir")

    assert "99,999" not in response["answer"]
    assert response["mode"] == "school_data"


def test_groq_failure_falls_back_and_is_reported(groq, small_school):
    groq.error = RuntimeError("service down")

    response = SchoolAssistantService(small_school).answer("Show the profile of Sana Mir")

    assert response["mode"] == "school_data"
    assert "Sana Mir" in response["answer"]
    assert assistant_module.groq_status()["last_call_ok"] is False


def test_a_model_that_never_stops_calling_tools_falls_back(groq, small_school):
    groq.replies = [_message(tool_calls=[_tool_call("get_collection_summary")]) for _ in range(5)]

    response = SchoolAssistantService(small_school).answer("Show the profile of Sana Mir")

    assert response["mode"] == "school_data"
    assert len(groq.sent) == assistant_module._MAX_TOOL_ROUNDS


def test_contact_details_are_not_sent_to_groq_but_reach_the_card(groq, small_school):
    groq.replies = [
        _message(tool_calls=[_tool_call("get_student_profile", student_identifier="id:45")]),
        _message(content="See the card."),
    ]
    history = [{"role": "assistant", "content": "Guardian: Sohail Mir; Phone: 0311-0000000."}]

    response = SchoolAssistantService(small_school).answer("Show the profile of Sana Mir", history)

    everything_sent = " ".join(groq.sent)
    assert "03110000000" not in everything_sent
    assert "0311-0000000" not in everything_sent
    assert response["structured_data"]["profile"]["student"]["phone"] == "03110000000"


def test_a_tool_called_twice_shows_no_single_card(groq, small_school):
    groq.replies = [
        _message(tool_calls=[
            _tool_call("get_student_profile", student_identifier="id:1"),
            _tool_call("get_student_profile", student_identifier="id:45"),
        ]),
        _message(content="Two students."),
    ]

    response = SchoolAssistantService(small_school).answer("Show the records of both")

    assert response["structured_data"] is None


def test_ambiguous_tool_result_shows_the_matches(groq, small_school):
    groq.replies = [
        _message(tool_calls=[_tool_call("get_student_profile", student_identifier="Ahmed Khan")]),
        _message(content="Which one?"),
    ]

    response = SchoolAssistantService(small_school).answer("show me that record please")

    assert {row["roll_number"] for row in response["structured_data"]["students"]} == {"045", "077"}


@pytest.mark.parametrize("name, arguments", [
    ("drop_table", {}),
    ("get_student_profile", "not a dict"),
    ("get_top_students", {"limit": "many", "grade": 8}),
    ("get_student_results", {"student_identifier": None, "exam_type": 7}),
    ("get_students_by_grade", {"grade": None}),
])
def test_bad_tool_calls_from_a_model_never_crash(small_school, name, arguments):
    from services.data_assistant_service import SchoolDataAssistant

    SchoolDataAssistant(small_school).execute_tool(name, arguments)


def test_every_tool_definition_has_a_working_branch_and_a_card(small_school):
    from services.assistant_tools import TOOL_DEFINITIONS
    from services.data_assistant_service import SchoolDataAssistant

    assistant = SchoolDataAssistant(small_school)
    for definition in TOOL_DEFINITIONS:
        name = definition["function"]["name"]
        assert assistant.execute_tool(name, {}) != {"error": "This data action is not allowed."}
        assert name in assistant_module._STRUCTURED_DATA_KEYS


# ── Policy search ─────────────────────────────────────────────────────────────

LABELLED_POLICY_QUESTIONS = [
    ("What is the fee refund policy?", "fee_policy.txt", "refund"),
    ("How much is the late fee?", "fee_policy.txt", "200"),
    ("What is the sibling concession?", "fee_policy.txt", "25%"),
    ("What is the minimum passing mark?", "exam_policy.txt", "40%"),
    ("How much is the retake examination fee?", "exam_policy.txt", "1,000"),
    ("When is winter vacation?", "academic_calendar.txt", "December 21"),
    ("What is the required uniform for boys?", "conduct_rules.txt", "Sky-blue"),
]
UNRELATED_QUESTIONS = ["What is the capital of France?", "Who won the football world cup?", "How do I bake a cake?"]


@pytest.fixture(params=["faiss", "tfidf"])
def policy_search(request, monkeypatch):
    monkeypatch.setattr(rag_module, "HAS_FAISS", request.param == "faiss")
    service = rag_module.PolicyRAGService()
    service.initialize()
    if request.param == "faiss" and service.index is None:
        pytest.skip("The FAISS model is not available here")
    assert service.status()["engine"] == request.param
    return service


@pytest.mark.parametrize("question, source, expected", LABELLED_POLICY_QUESTIONS)
def test_policy_questions_find_the_right_document_and_line(policy_search, question, source, expected):
    response = policy_search.answer_query(question)

    assert response["grounded"] is True
    assert response["sources"] == [source]
    assert expected in response["answer"]


@pytest.mark.parametrize("question", UNRELATED_QUESTIONS)
def test_unrelated_questions_get_no_policy_text(policy_search, question):
    response = policy_search.answer_query(question)

    assert response["grounded"] is False
    assert response["sources"] == []
    assert "According to" not in response["answer"]


def test_a_model_that_finds_nothing_is_not_marked_as_grounded(monkeypatch):
    service = rag_module.PolicyRAGService()
    service.initialize()
    reply = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="I don't know based on the provided school policies."))])
    service.groq_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_: reply)))

    response = service.answer_query("What is the fee refund policy?")

    assert response["grounded"] is False
    assert response["sources"] == []


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-q"]))
