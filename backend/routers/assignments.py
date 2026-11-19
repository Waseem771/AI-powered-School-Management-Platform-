"""Which teacher teaches which class, in which academic session. Administrators only."""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from config import GRADES, SECTIONS
from database import get_session
from models.attendance import TeacherClassAssignment
from models.fee import AcademicYear
from models.user import ROLE_TEACHER, User
from routers.teachers import require_admin
from services import attendance as rules
from services.fee_ledger import utc_iso

router = APIRouter(prefix="/teacher-assignments", tags=["Teacher assignments"])


class AssignmentWrite(BaseModel):
    teacher_id: int
    grade: str
    section: str
    academic_year_id: Optional[int] = None  # the current session when left out


def _teacher(session: Session, teacher_id: int) -> User:
    teacher = session.get(User, teacher_id)
    if teacher is None or (teacher.role or "").lower() != ROLE_TEACHER:
        raise HTTPException(status_code=404, detail="Teacher not found")
    if not teacher.is_active:
        raise HTTPException(status_code=422, detail="That teacher's account is deactivated. Activate it first.")
    return teacher


def _read(session: Session, row: TeacherClassAssignment, enrolled: dict, users: dict, years: dict) -> dict:
    teacher = users.get(row.teacher_id)
    year = years.get(row.academic_year_id)
    return {
        "id": row.id, "teacher_id": row.teacher_id,
        "teacher_name": (teacher.full_name or teacher.username) if teacher else "Unknown",
        "teacher_username": teacher.username if teacher else None,
        "teacher_active": bool(teacher and teacher.is_active),
        "grade": row.grade, "section": row.section,
        "academic_year_id": row.academic_year_id, "academic_year": year.label if year else None,
        "enrolled": enrolled.get((row.grade, row.section), 0),
        "created_at": utc_iso(row.created_at),
    }


def _read_all(session: Session, rows: List[TeacherClassAssignment]) -> List[dict]:
    enrolled = rules.roster_counts(session)
    users = {u.id: u for u in session.exec(select(User).where(User.role == ROLE_TEACHER)).all()}
    years = {y.id: y for y in session.exec(select(AcademicYear)).all()}
    return [_read(session, row, enrolled, users, years) for row in rows]


@router.get("/options")
def options(session: Session = Depends(get_session), _admin: User = Depends(require_admin)):
    enrolled = rules.roster_counts(session)
    teachers = session.exec(select(User).where(User.role == ROLE_TEACHER).order_by(User.full_name, User.username)).all()
    years = session.exec(select(AcademicYear).order_by(AcademicYear.id)).all()
    return {
        "teachers": [{"id": t.id, "name": t.full_name or t.username, "username": t.username, "is_active": t.is_active}
                     for t in teachers],
        "grades": GRADES, "sections": SECTIONS,
        "classes": [{"grade": g, "section": s, "enrolled": enrolled.get((g, s), 0)} for g, s in rules.all_classes()],
        "academic_years": [{"id": y.id, "label": y.label, "is_current": y.is_current} for y in years],
    }


@router.get("")
def list_assignments(
    teacher_id: Optional[int] = None,
    grade: Optional[str] = None,
    section: Optional[str] = None,
    academic_year_id: Optional[int] = None,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    query = select(TeacherClassAssignment).order_by(
        TeacherClassAssignment.grade, TeacherClassAssignment.section, TeacherClassAssignment.id)
    if teacher_id:
        query = query.where(TeacherClassAssignment.teacher_id == teacher_id)
    if grade:
        query = query.where(TeacherClassAssignment.grade == grade)
    if section:
        query = query.where(TeacherClassAssignment.section == section)
    if academic_year_id:
        query = query.where(TeacherClassAssignment.academic_year_id == academic_year_id)
    return _read_all(session, list(session.exec(query).all()))


def _check_unique(session: Session, teacher_id, grade, section, year_id, ignore_id: Optional[int] = None) -> None:
    duplicate = session.exec(select(TeacherClassAssignment).where(
        TeacherClassAssignment.teacher_id == teacher_id, TeacherClassAssignment.grade == grade,
        TeacherClassAssignment.section == section, TeacherClassAssignment.academic_year_id == year_id)).first()
    if duplicate and duplicate.id != ignore_id:
        raise HTTPException(status_code=409, detail="That teacher is already assigned to this class for this session.")


@router.post("", status_code=status.HTTP_201_CREATED)
def create_assignment(
    payload: AssignmentWrite,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin),
):
    rules.check_class(payload.grade, payload.section)
    _teacher(session, payload.teacher_id)
    year = rules.get_year(session, payload.academic_year_id)
    _check_unique(session, payload.teacher_id, payload.grade, payload.section, year.id)
    row = TeacherClassAssignment(teacher_id=payload.teacher_id, grade=payload.grade, section=payload.section,
                                 academic_year_id=year.id, created_by=admin.id)
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="That teacher is already assigned to this class for this session.")
    session.refresh(row)
    return _read_all(session, [row])[0]


@router.put("/{assignment_id}")
def update_assignment(
    assignment_id: int,
    payload: AssignmentWrite,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    row = session.get(TeacherClassAssignment, assignment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    rules.check_class(payload.grade, payload.section)
    _teacher(session, payload.teacher_id)
    year = rules.get_year(session, payload.academic_year_id or row.academic_year_id)
    _check_unique(session, payload.teacher_id, payload.grade, payload.section, year.id, ignore_id=row.id)
    row.teacher_id, row.grade, row.section, row.academic_year_id = payload.teacher_id, payload.grade, payload.section, year.id
    session.add(row)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="That teacher is already assigned to this class for this session.")
    session.refresh(row)
    return _read_all(session, [row])[0]


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    assignment_id: int,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    """Removes only the assignment. Attendance the teacher already recorded stays, untouched."""
    row = session.get(TeacherClassAssignment, assignment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    session.delete(row)
    session.commit()
