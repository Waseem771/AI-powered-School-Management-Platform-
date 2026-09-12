from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, or_
from typing import List, Optional
from database import get_session
from models.student import Student, StudentCreate, StudentUpdate, StudentRead
from models.result import Result
from models.fee import Invoice
from routers.auth import get_current_user

router = APIRouter(prefix="/students", tags=["Students"])

@router.get("", response_model=List[StudentRead])
def get_students(
    search: Optional[str] = None,
    grade: Optional[str] = None,
    session: Session = Depends(get_session),
    _user = Depends(get_current_user)
):
    query = select(Student)
    if grade:
        query = query.where(Student.grade == grade)
    if search:
        search_fmt = f"%{search}%"
        query = query.where(
            or_(
                Student.name.ilike(search_fmt),
                Student.roll_number.ilike(search_fmt),
                Student.guardian_name.ilike(search_fmt),
                Student.phone.ilike(search_fmt)
            )
        )
    return session.exec(query.order_by(Student.grade, Student.roll_number)).all()

@router.post("", response_model=StudentRead)
def create_student(
    student_in: StudentCreate,
    session: Session = Depends(get_session),
    _user = Depends(get_current_user)
):
    existing = session.exec(select(Student).where(Student.roll_number == student_in.roll_number)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Roll number already exists")

    student = Student.model_validate(student_in)
    session.add(student)
    session.commit()
    session.refresh(student)
    return student

@router.get("/{id}", response_model=StudentRead)
def get_student(
    id: int,
    session: Session = Depends(get_session),
    _user = Depends(get_current_user)
):
    student = session.get(Student, id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student

@router.put("/{id}", response_model=StudentRead)
def update_student(
    id: int,
    student_in: StudentUpdate,
    session: Session = Depends(get_session),
    _user = Depends(get_current_user)
):
    student = session.get(Student, id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    student_data = student_in.model_dump(exclude_unset=True)
    for key, value in student_data.items():
        setattr(student, key, value)

    session.add(student)
    session.commit()
    session.refresh(student)
    return student

@router.delete("/{id}")
def delete_student(
    id: int,
    session: Session = Depends(get_session),
    _user = Depends(get_current_user)
):
    student = session.get(Student, id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Delete student's marks and invoices
    results = session.exec(select(Result).where(Result.student_id == id)).all()
    for r in results:
        session.delete(r)

    invoices = session.exec(select(Invoice).where(Invoice.student_id == id)).all()
    for inv in invoices:
        session.delete(inv)

    session.delete(student)
    session.commit()
    return {"message": "Student deleted successfully", "id": id}
