"""A labelled question set for the chatbot's local path, which works with no AI key.

The small school here is built to be awkward on purpose: a database id that equals another
student's roll number, two students with the same name, and an archived student.
"""
import pytest
from sqlmodel import Session, SQLModel, create_engine

from models.fee import Invoice, Payment
from models.result import Result
from models.student import Student
from services.school_assistant_service import SchoolAssistantService

SUBJECT_NAMES = ["English", "Urdu", "Mathematics", "Science", "Islamiat", "Pakistan Studies"]
AHMED_THEN_REPLY = [
    {"role": "user", "content": "Show Ahmed Khan (roll 045)"},
    {"role": "assistant", "content": "Student: Ahmed Khan (roll #045), Grade 8 - A."},
]


def _student(student_id, name, roll, grade="Grade 8", section="A", **extra):
    return Student(
        id=student_id, name=name, roll_number=roll, grade=grade, section=section,
        guardian_name="Guardian Name", phone="03001234567", **extra,
    )


def _exam(student_id, marks, exam_type="Final Term", year=1):
    return [
        Result(student_id=student_id, subject=subject, marks_obtained=mark, total_marks=100, exam_type=exam_type, academic_year_id=year)
        for subject, mark in zip(SUBJECT_NAMES, marks)
    ]


@pytest.fixture()
def session():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([
            _student(1, "Ahmed Khan", "045"),
            _student(2, "Ahmed Khan", "077", grade="Grade 9", section="B"),
            _student(3, "Minahil Khan", "101", grade="Grade 9"),
            _student(4, "Zoya Malik", "023", grade="Grade 7"),
            _student(45, "Sana Mir", "141", grade="Grade 10"),
            _student(5, "Bilal Tariq", "5", grade="Grade 9"),
            _student(6, "Hina Soomro", "H-7/2", grade="Grade 6", section="B"),
        ])
        db.commit()
        db.add_all([
            Invoice(id=1, student_id=1, amount=3500, month="October 2026", due_date="10-Oct-2026", challan_number="CHN-1", status="partial"),
            Invoice(id=2, student_id=4, amount=4000, month="October 2026", due_date="10-Oct-2026", challan_number="CHN-2", status="paid"),
            Invoice(id=3, student_id=45, amount=2000, month="November 2026", due_date="10-Nov-2026", challan_number="CHN-3", status="pending"),
            Payment(invoice_id=1, amount_paid=1500),
            Payment(invoice_id=2, amount_paid=4000),
            *_exam(1, [90, 90, 90, 90, 90, 90]),
            *_exam(1, [50, 50, 50, 50, 50, 50], exam_type="Midterm"),
            *_exam(4, [60, 60, 60, 60, 60, 60]),
            *_exam(3, [30, 30, 30, 30, 70, 70]),
            Result(student_id=45, subject="English", marks_obtained=100, total_marks=100, exam_type="Final Term", academic_year_id=1),
        ])
        db.commit()
        yield db


def ask(session, question, history=None):
    return SchoolAssistantService(session).answer(question, history=history)


# ── The right student ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("question, expected, wrong", [
    ("Fees for roll number 045", "Ahmed Khan", "Sana Mir"),
    ("fees for roll no 45", "Ahmed Khan", "Sana Mir"),
    ("What are the dues for #045?", "Ahmed Khan", "Sana Mir"),
    ("Results for roll 023", "Zoya Malik", "Ahmed"),
    ("Fees for roll number H-7/2", "Hina Soomro", "Ahmed"),
    ("Show student id 45", "Sana Mir", "Ahmed"),
    ("Results for Zoya Malik", "Zoya Malik", "Ahmed"),
    ("results for zoya", "Zoya Malik", "Ahmed"),
    ("zoya malik ki fees kitni hai", "Zoya Malik", "Ahmed"),
    ("Fees of Minahil Khan", "Minahil Khan", "Ahmed"),
])
def test_finds_the_student_who_was_asked_about(session, question, expected, wrong):
    response = ask(session, question)

    assert expected in response["answer"]
    assert wrong not in response["answer"]
    assert response["grounded"] is True


def test_roll_number_with_nothing_on_file_is_not_answered_with_someone_else(session):
    # Student id 45 exists, roll 45 belongs to Ahmed; 145 belongs to no one, and neither does id 145.
    response = ask(session, "Fees for roll number 145")

    assert "145" in response["answer"]
    assert "No student" in response["answer"]
    assert response["structured_data"] is None


@pytest.mark.parametrize("identifier", ["45", "%", "_"])
def test_tool_lookup_never_treats_a_number_as_an_id_or_text_as_a_wildcard(session, identifier):
    from services.data_assistant_service import SchoolDataAssistant

    result = SchoolDataAssistant(session).get_student_profile(identifier)

    if identifier == "45":
        assert result["student"]["name"] == "Ahmed Khan"
    else:
        assert result["found"] is False


def test_tool_lookup_uses_an_id_only_when_told_it_is_one(session):
    from services.data_assistant_service import SchoolDataAssistant

    assert SchoolDataAssistant(session).get_student_profile("id:45")["student"]["name"] == "Sana Mir"


# ── Asking rather than guessing ───────────────────────────────────────────────

@pytest.mark.parametrize("question", [
    "Fees of Ahmed Khan",
    "Show Ahmed Khan",
    "What are the marks of Ahmed?",
    "Fees for Khan",
])
def test_asks_which_student_when_several_match(session, question):
    response = ask(session, question)

    assert "Which student" in response["answer"]
    assert "045" in response["answer"] and "077" in response["answer"]
    assert "paid" not in response["answer"]
    assert {row["roll_number"] for row in response["structured_data"]["students"]} >= {"045", "077"}


def test_a_grade_in_the_question_settles_which_student(session):
    response = ask(session, "Fees of Ahmed Khan in Grade 8")

    assert "045" in response["answer"]
    assert "077" not in response["answer"]


def test_a_name_partly_matching_one_student_is_offered_not_assumed(session):
    # There is no Sara Malik. Zoya Malik must not silently stand in for her.
    response = ask(session, "Fees of Sara Malik")

    assert "Sara" in response["answer"] and "Zoya Malik" in response["answer"]
    assert "paid" not in response["answer"]


def test_a_roll_number_reply_answers_the_original_question(session):
    first = ask(session, "What are the fee dues of Ahmed Khan?")
    history = [
        {"role": "user", "content": "What are the fee dues of Ahmed Khan?"},
        {"role": "assistant", "content": first["answer"]},
    ]

    response = ask(session, "045", history)

    assert "2,000 pending" in response["answer"]
    assert response["tools_used"] == ["get_student_fee_summary"]


def test_a_grade_reply_answers_the_original_question(session):
    first = ask(session, "Show the marks of Ahmed Khan")
    history = [
        {"role": "user", "content": "Show the marks of Ahmed Khan"},
        {"role": "assistant", "content": first["answer"]},
    ]

    response = ask(session, "the one in Grade 8", history)

    assert response["tools_used"] == ["get_student_results"]
    assert "90.0%" in response["answer"]


def test_asks_for_the_student_when_a_record_question_names_nobody(session):
    response = ask(session, "Show the marks")

    assert "Which student" in response["answer"]


# ── Follow-up questions use memory only when they are follow-ups ──────────────

@pytest.mark.parametrize("question, tool", [
    ("What are his fees?", "get_student_fee_summary"),
    ("and his marks?", "get_student_results"),
    ("What is her phone number?", "get_student_profile"),
    ("marks?", "get_student_results"),
])
def test_follow_ups_use_the_student_in_memory(session, question, tool):
    response = ask(session, question, AHMED_THEN_REPLY)

    assert response["tools_used"] == [tool]
    assert "Ahmed Khan" in response["answer"]


def test_a_follow_up_with_nobody_in_memory_asks(session):
    assert "Which student" in ask(session, "What are his fees?")["answer"]


def test_a_school_wide_question_ignores_the_student_in_memory(session):
    response = ask(session, "Which students have pending fees?", AHMED_THEN_REPLY)

    assert response["tools_used"] == ["get_students_with_pending_fees"]
    assert response["structured_data"]["pending_students"]["count"] == 2


def test_a_policy_question_ignores_the_student_in_memory(session):
    response = ask(session, "When is winter vacation?", AHMED_THEN_REPLY)

    assert response["mode"] == "policy_rag"


def test_the_word_the_is_not_a_pronoun(session):
    response = ask(session, "Is the school open?", AHMED_THEN_REPLY)

    assert response["mode"] == "policy_rag"


def test_a_place_in_a_policy_answer_is_not_taken_for_a_student(session):
    session.add(_student(50, "Mahnoor Iqbal", "150"))
    session.commit()
    history = [
        {"role": "user", "content": "What are the holidays?"},
        {"role": "assistant", "content": "According to the calendar: Iqbal Day is a holiday."},
    ]

    assert "Which student" in ask(session, "What are her fees?", history)["answer"]


# ── School-wide questions ─────────────────────────────────────────────────────

@pytest.mark.parametrize("question, tool", [
    ("List all students in Grade 8", "get_students_by_grade"),
    ("Show students in class 8", "get_students_by_grade"),
    ("Grade 8 students", "get_students_by_grade"),
    ("List me all students whose fees are pending", "get_students_with_pending_fees"),
    ("who are the fee defaulters?", "get_students_with_pending_fees"),
    ("pending fees in Grade 8", "get_students_with_pending_fees"),
    ("How many students are there?", "get_student_counts"),
    ("how many students in Grade 9?", "get_student_counts"),
    ("Who are the top students?", "get_top_students"),
    ("top 2 students in Grade 8", "get_top_students"),
    ("Show the subject averages", "get_subject_averages"),
    ("Which students are at risk?", "get_at_risk_students"),
    ("Show high risk students", "get_at_risk_students"),
    ("Is Zoya Malik at risk?", "get_student_risk"),
    ("What is the overall fee collection summary?", "get_collection_summary"),
    ("How much was collected in October 2026?", "get_monthly_collection"),
    ("monthly fee collection", "get_monthly_collection"),
])
def test_school_wide_questions_reach_the_right_tool(session, question, tool):
    response = ask(session, question)

    assert response["mode"] == "school_data"
    assert response["tools_used"] == [tool]
    assert response["structured_data"]


def test_a_grade_list_holds_the_grade_and_not_the_dues_list(session):
    data = ask(session, "List all students in Grade 8")["structured_data"]["grade_students"]

    assert data["count"] == 1
    assert data["students"][0]["roll_number"] == "045"


def test_a_grade_the_school_does_not_have_says_so(session):
    response = ask(session, "List all students in Grade 99")

    assert "Grade 99" in response["answer"]
    assert "Grade 6" in response["answer"]


def test_section_narrows_counts_and_lists(session):
    data = ask(session, "how many students in Grade 9 section B?")["structured_data"]["student_counts"]

    assert data["total"] == 1


def test_counts_leave_out_archived_students_and_say_how_many(session):
    from datetime import datetime, timezone

    student = session.get(Student, 6)
    student.archived_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    session.add(student)
    session.commit()

    data = ask(session, "How many students are there?")["structured_data"]["student_counts"]

    assert data["total"] == 6
    assert data["archived"] == 1


def test_top_students_ranks_one_exam_and_leaves_out_incomplete_marks(session):
    data = ask(session, "Who are the top students?")["structured_data"]["top_students"]

    assert [row["roll_number"] for row in data["students"]] == ["045", "023", "101"]
    assert data["students"][0]["percentage"] == 90.0
    assert data["exam_type"] == "Final Term"
    # Sana Mir has one subject at 100%, which must not put her at the top.
    assert data["left_out_incomplete"] == 1


def test_top_students_can_use_the_midterm(session):
    data = ask(session, "top students in midterm")["structured_data"]["top_students"]

    assert data["exam_type"] == "Midterm"
    assert data["students"][0]["percentage"] == 50.0


def test_subject_averages_use_one_exam_and_do_not_mix_in_the_midterm(session):
    data = ask(session, "Show the subject averages")["structured_data"]["subject_averages"]

    row = next(item for item in data["subjects"] if item["subject"] == "Mathematics")
    assert row["average_percentage"] == 60.0
    assert row["students"] == 3
    assert data["exam_type"] == "Final Term"


def test_exam_filter_on_one_students_results(session):
    data = ask(session, "Midterm results for roll 045")["structured_data"]["results"]

    assert data["exam_type"] == "Midterm"
    assert data["average_percentage"] == 50.0


def test_at_risk_list_skips_students_with_no_marks_and_low_risk(session):
    data = ask(session, "Which students are at risk?")["structured_data"]["at_risk"]

    rolls = {row["roll_number"] for row in data["students"]}
    assert "5" not in rolls
    assert data["not_scored"] >= 2
    assert all(row["risk_category"] in ("High", "Medium") for row in data["students"])
    assert "review" in data["note"].lower()


def test_one_students_risk_with_no_marks_gives_no_estimate(session):
    response = ask(session, "Is Hina Soomro at risk?")

    assert "Not enough marks" in response["answer"]
    assert response["structured_data"] is None


def test_monthly_collection_matches_the_whole_school_totals(session):
    from services.fee_ledger import school_totals

    rows = ask(session, "monthly fee collection")["structured_data"]["monthly_collection"]["months"]
    totals = school_totals(session)

    assert [row["month"] for row in rows] == ["October 2026", "November 2026"]
    assert sum(row["invoiced"] for row in rows) == totals["invoiced"]
    assert sum(row["collected"] for row in rows) == totals["collected"]
    assert sum(row["outstanding"] for row in rows) == totals["outstanding"]


def test_a_month_with_no_invoices_says_so(session):
    response = ask(session, "How much was collected in January 2026?")

    assert "No invoices" in response["answer"]
    assert "January 2026" in response["answer"]


@pytest.mark.parametrize("question", [
    "How many students failed?",
    "How many students are girls?",
])
def test_a_count_it_cannot_make_is_not_answered_with_a_different_count(session, question):
    response = ask(session, question)

    assert response.get("tools_used") != ["get_student_counts"]
    assert response["grounded"] is False


# ── Policy and unrelated questions ────────────────────────────────────────────

@pytest.mark.parametrize("question", [
    "What is the fee refund policy?",
    "What are the uniform rules?",
    "What is the age for admission of a student?",
    "How much is the late fee?",
    "When is winter vacation?",
    "What are the rules and fees for retake examinations?",
])
def test_policy_questions_go_to_the_policy_documents(session, question):
    response = ask(session, question)

    assert response["mode"] == "policy_rag"
    assert response["grounded"] is True
    assert response["sources"]


@pytest.mark.parametrize("question", [
    "What is the capital of France?",
    "Who won the football world cup?",
    "Write me a poem about cats",
])
def test_unrelated_questions_say_they_cannot_be_answered(session, question):
    response = ask(session, question)

    assert response["grounded"] is False
    assert response["sources"] == []
    assert "cannot answer" in response["answer"].lower()


def test_a_student_with_a_soft_policy_word_is_a_record_question(session):
    response = ask(session, "Is Zoya Malik passing? Show her marks")

    assert response["tools_used"] == ["get_student_results"]


def test_the_school_name_is_not_taken_for_a_student(session):
    from config import SCHOOL_NAME

    session.add(_student(51, f"{SCHOOL_NAME.split()[-1]} Person", "151"))
    session.commit()

    response = ask(session, f"What is the uniform at {SCHOOL_NAME}?")

    assert response["mode"] == "policy_rag"


def test_archived_student_is_found_and_marked(session):
    from datetime import datetime, timezone

    student = session.get(Student, 4)
    student.archived_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    session.add(student)
    session.commit()

    assert "archived" in ask(session, "Fees of Zoya Malik")["answer"].lower()


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-q"]))
