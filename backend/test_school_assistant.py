from sqlmodel import Session, SQLModel, create_engine

from models.fee import Invoice
from models.student import Student
from services.school_assistant_service import SchoolAssistantService


def test_local_data_answers_do_not_need_an_llm_key():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    session = Session(engine)
    student = Student(name="Ahmed Khan", roll_number="045", grade="Grade 8", section="A", guardian_name="Imran Khan", phone="0300-0000000")
    session.add(student)
    session.commit()
    session.refresh(student)
    session.add(Invoice(student_id=student.id, amount=3500, month="October 2025", due_date="10-Oct-2025", challan_number="CHN-045", status="pending"))
    session.commit()

    response = SchoolAssistantService(session).answer("What are the fee dues for Ahmed Khan?")

    assert response["mode"] == "school_data"
    assert response["grounded"] is True
    assert "Ahmed Khan" in response["answer"]
    assert "3,500" in response["answer"]


if __name__ == "__main__":
    test_local_data_answers_do_not_need_an_llm_key()
    print("School assistant orchestration tests passed.")
