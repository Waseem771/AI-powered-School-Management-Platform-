from datetime import datetime, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, or_, select

from database import get_session
from models.fee import Invoice
from models.result import Result
from models.student import Student, StudentCreate, StudentRead, StudentUpdate
from routers.auth import get_current_user

router = APIRouter(prefix="/students", tags=["Students"])


def _get_student_or_404(session: Session, student_id: int) -> Student:
    student = session.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


def _roll_number_conflict(session: Session, roll_number: str) -> HTTPException:
    holder = session.exec(select(Student).where(Student.roll_number == roll_number)).first()
    if holder and holder.archived_at:
        detail = f"Roll number {roll_number} belongs to an archived student. Restore that record or use another number."
    else:
        detail = f"Roll number {roll_number} is already in use."
    return HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=detail)


def _commit_roll_number_change(session: Session, roll_number: str) -> None:
    """The database index catches a request that lost a race with an identical one."""
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise _roll_number_conflict(session, roll_number)


@router.get("", response_model=List[StudentRead])
def get_students(
    search: Optional[str] = None,
    grade: Optional[str] = None,
    status: Literal["active", "archived", "all"] = "active",
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    query = select(Student)
    if status == "active":
        query = query.where(col(Student.archived_at).is_(None))
    elif status == "archived":
        query = query.where(col(Student.archived_at).is_not(None))
    if grade:
        query = query.where(Student.grade == grade)
    if search:
        search_fmt = f"%{search}%"
        query = query.where(
            or_(
                Student.name.ilike(search_fmt),
                Student.roll_number.ilike(search_fmt),
                Student.guardian_name.ilike(search_fmt),
                Student.phone.ilike(search_fmt),
            )
        )
    return session.exec(query.order_by(Student.grade, Student.roll_number)).all()


@router.post("", response_model=StudentRead, status_code=http_status.HTTP_201_CREATED)
def create_student(
    student_in: StudentCreate,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    if session.exec(select(Student).where(Student.roll_number == student_in.roll_number)).first():
        raise _roll_number_conflict(session, student_in.roll_number)

    student = Student(**student_in.model_dump())
    session.add(student)
    _commit_roll_number_change(session, student_in.roll_number)
    session.refresh(student)
    return student


@router.get("/{id}", response_model=StudentRead)
def get_student(
    id: int,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    return _get_student_or_404(session, id)


@router.put("/{id}", response_model=StudentRead)
def update_student(
    id: int,
    student_in: StudentUpdate,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    student = _get_student_or_404(session, id)
    changes = student_in.model_dump(exclude_unset=True)

    new_roll = changes.get("roll_number")
    if new_roll and new_roll != student.roll_number:
        if session.exec(select(Student).where(Student.roll_number == new_roll)).first():
            raise _roll_number_conflict(session, new_roll)

    for key, value in changes.items():
        setattr(student, key, value)
    session.add(student)
    _commit_roll_number_change(session, new_roll or student.roll_number)
    session.refresh(student)
    return student


@router.post("/{id}/archive", response_model=StudentRead)
def archive_student(
    id: int,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    """A student who leaves disappears from daily lists. Fees and exam history stay untouched."""
    student = _get_student_or_404(session, id)
    if student.archived_at:
        raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail="This student is already archived.")
    student.archived_at = datetime.now(timezone.utc)
    session.add(student)
    session.commit()
    session.refresh(student)
    return student


@router.post("/{id}/restore", response_model=StudentRead)
def restore_student(
    id: int,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    student = _get_student_or_404(session, id)
    if not student.archived_at:
        raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail="This student is not archived.")
    student.archived_at = None
    session.add(student)
    session.commit()
    session.refresh(student)
    return student


@router.delete("/{id}")
def delete_student(
    id: int,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    """Only for a record entered by mistake. Anything with fee or exam history must be archived."""
    student = _get_student_or_404(session, id)

    has_invoices = session.exec(select(Invoice.id).where(Invoice.student_id == id)).first() is not None
    has_results = session.exec(select(Result.id).where(Result.student_id == id)).first() is not None
    if has_invoices or has_results:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail="This student has fee or exam records, so it cannot be deleted. Archive the student instead.",
        )

    session.delete(student)
    session.commit()
    return {"message": "Student deleted successfully", "id": id}
