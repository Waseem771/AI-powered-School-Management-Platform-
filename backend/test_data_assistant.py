from sqlmodel import Session, SQLModel, create_engine

from models.fee import Invoice
from models.result import Result
from models.student import Student
from services.data_assistant_service import SchoolDataAssistant


def setup_session():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    student = Student(
        name="Ahmed Khan",
        roll_number="045",
        grade="Grade 8",
        section="A",
        guardian_name="Imran Khan",
        phone="0300-0000000",
    )
    session.add(student)
    session.commit()
    session.refresh(student)
    session.add_all([
        Invoice(student_id=student.id, amount=3500, month="October 2025", due_date="10-Oct-2025", challan_number="CHN-045A", status="paid"),
        Invoice(student_id=student.id, amount=3500, month="November 2025", due_date="10-Nov-2025", challan_number="CHN-045B", status="pending"),
        Result(student_id=student.id, subject="Mathematics", marks_obtained=82, total_marks=100),
    ])
    session.commit()
    return session


def test_student_lookup_and_fee_summary():
    session = setup_session()
    assistant = SchoolDataAssistant(session)

    matches = assistant.find_students("ahmed")
    assert matches == [{"id": 1, "name": "Ahmed Khan", "roll_number": "045", "grade": "Grade 8", "section": "A"}]

    summary = assistant.get_student_fee_summary("045")
    assert summary["student"]["name"] == "Ahmed Khan"
    assert summary["totals"] == {"invoiced": 7000.0, "paid": 3500.0, "pending": 3500.0}


def test_collection_summary_and_unknown_student_are_safe():
    session = setup_session()
    assistant = SchoolDataAssistant(session)

    summary = assistant.get_collection_summary()
    assert summary["collection_rate"] == 50.0
    assert assistant.get_student_profile("999") == {"found": False, "message": "No student matched '999'."}


if __name__ == "__main__":
    test_student_lookup_and_fee_summary()
    test_collection_summary_and_unknown_student_are_safe()
    print("School data assistant tests passed.")
