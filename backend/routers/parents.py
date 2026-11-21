"""Parent accounts (managed by an administrator) and the Parent Portal.

Parents sign in through the same /auth/login as everyone else. Their accounts are ordinary rows in
`users` with role "parent", so every school-data route already refuses them (see
`routers.auth.get_current_user`). The portal routes below are the only ones a parent can reach, and each
one starts from the parent's own links: a child that is not linked answers 404, exactly as if it did not exist.
"""
from typing import List, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from database import get_session
from models.fee import AcademicYear, Invoice, Payment
from models.parent import ParentStudentLink, PublishedExam
from models.result import ExamType, Result
from models.student import Student
from models.user import ROLE_PARENT, User, hash_password, password_problem
from routers.auth import MAX_CREDENTIAL_LENGTH, require_roles
from routers.fees import download_challan_pdf, download_payment_receipt
from routers.results import download_report_card
from routers.teachers import (
    USERNAME_PATTERN, EmailChange, PasswordReset, change_account_email, require_admin,
)
from services import parent_portal as portal
from services.email_address import optional_email
from services.academics import select_exam
from services.fee_ledger import utc_iso
from services.password_reset import apply_admin_reset, reset_states

router = APIRouter(prefix="/parents", tags=["Parent accounts"])
publishing_router = APIRouter(prefix="/result-publishing", tags=["Result publishing"])
portal_router = APIRouter(prefix="/parent", tags=["Parent portal"])

require_parent = require_roles(ROLE_PARENT)
Relationship = Literal["Father", "Mother", "Guardian"]


# ── Administrator: parent accounts ──────────────────────────────────────────

class ParentCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=2, max_length=100)
    email: Optional[str] = Field(default=None, max_length=254)
    password: str = Field(min_length=1, max_length=MAX_CREDENTIAL_LENGTH)
    student_ids: List[int] = Field(min_length=1, max_length=portal.MAX_CHILDREN_PER_PARENT)
    relationship: Optional[Relationship] = None

    @field_validator("username")
    @classmethod
    def _username(cls, value: str) -> str:
        value = value.strip()
        if not USERNAME_PATTERN.match(value):
            raise ValueError("Username must be 3-50 letters, numbers, dots, dashes or underscores")
        return value

    @field_validator("full_name")
    @classmethod
    def _full_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Enter the parent's full name")
        return value

    @field_validator("email")
    @classmethod
    def _email(cls, value: Optional[str]) -> Optional[str]:
        return optional_email(value)

    @field_validator("student_ids")
    @classmethod
    def _students(cls, value: List[int]) -> List[int]:
        if len(set(value)) != len(value):
            raise ValueError("The same child is listed twice")
        return value


class LinkChild(BaseModel):
    student_id: int
    relationship: Optional[Relationship] = None


def _children_of(session: Session, parent_ids: List[int]) -> dict:
    rows = session.exec(
        select(ParentStudentLink, Student)
        .join(Student, Student.id == ParentStudentLink.student_id)
        .where(col(ParentStudentLink.parent_id).in_(parent_ids or [0]))
        .order_by(Student.grade, Student.section, Student.roll_number)
    ).all()
    result: dict = {}
    for link, student in rows:
        result.setdefault(link.parent_id, []).append({
            "student_id": student.id, "name": student.name, "roll_number": student.roll_number,
            "grade": student.grade, "section": student.section, "relationship": link.relationship,
            "enrolled": student.archived_at is None,
        })
    return result


def _parent_read(user: User, children: List[dict], reset_state: Optional[dict] = None) -> dict:
    """Built field by field, so the password hash can never leak into a response."""
    return {
        "id": user.id, "username": user.username, "full_name": user.full_name, "email": user.email,
        "role": user.role, "is_active": user.is_active, "created_at": utc_iso(user.created_at),
        "children": children,
        "must_change_password": bool(reset_state and reset_state["pending"]),
        "last_password_reset": reset_state["last"] if reset_state else None,
    }


def _get_parent(session: Session, parent_id: int) -> User:
    parent = session.get(User, parent_id)
    # Only parent accounts can be managed here, so this can never touch an administrator or a teacher.
    if parent is None or (parent.role or "").lower() != ROLE_PARENT:
        raise HTTPException(status_code=404, detail="Parent not found")
    return parent


def _readable(session: Session, parent: User) -> dict:
    return _parent_read(
        parent, _children_of(session, [parent.id]).get(parent.id, []), reset_states(session, [parent.id])[parent.id])


def _linkable_student(session: Session, student_id: int) -> Student:
    student = session.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="One of those students was not found.")
    if student.archived_at:
        raise HTTPException(status_code=409, detail=f"{student.name} is archived. Restore the student before linking.")
    return student


@router.get("")
def list_parents(session: Session = Depends(get_session), _admin: User = Depends(require_admin)):
    parents = session.exec(select(User).where(User.role == ROLE_PARENT).order_by(User.full_name, User.username)).all()
    ids = [parent.id for parent in parents]
    children = _children_of(session, ids)
    states = reset_states(session, ids)
    return [_parent_read(parent, children.get(parent.id, []), states[parent.id]) for parent in parents]


@router.put("/{parent_id}/email")
def update_parent_email(
    parent_id: int,
    payload: EmailChange,
    http_request: Request,
    background: BackgroundTasks,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin),
):
    """Sets or clears the email a parent can use to reset their own password. Needs the administrator's password."""
    parent = _get_parent(session, parent_id)
    change_account_email(session, parent, admin, payload, http_request, background)
    session.refresh(parent)
    return _readable(session, parent)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_parent(
    payload: ParentCreate,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin),
):
    problem = password_problem(payload.password)
    if problem:
        raise HTTPException(status_code=422, detail=f"Password is not acceptable: {problem}.")
    if session.exec(select(User).where(func.lower(User.username) == payload.username.lower())).first():
        raise HTTPException(status_code=409, detail="That username is already taken.")
    if payload.email and session.exec(select(User).where(func.lower(User.email) == payload.email)).first():
        raise HTTPException(status_code=409, detail="That email address is already used by another account.")
    students = [_linkable_student(session, student_id) for student_id in payload.student_ids]

    parent = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=ROLE_PARENT,
        full_name=payload.full_name,
        email=payload.email,
        is_active=True,
    )
    session.add(parent)
    try:
        session.flush()  # gives the account its id; the links below join the same commit
        for student in students:
            session.add(ParentStudentLink(
                parent_id=parent.id, student_id=student.id, relationship=payload.relationship, created_by=admin.id))
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="That username is already taken.")
    session.refresh(parent)
    return _readable(session, parent)


def _set_active(session: Session, parent_id: int, active: bool) -> dict:
    parent = _get_parent(session, parent_id)
    if parent.is_active != active:
        parent.is_active = active
        session.add(parent)
        session.commit()
        session.refresh(parent)
    return _readable(session, parent)


@router.post("/{parent_id}/activate")
def activate_parent(parent_id: int, session: Session = Depends(get_session), _admin: User = Depends(require_admin)):
    return _set_active(session, parent_id, True)


@router.post("/{parent_id}/deactivate")
def deactivate_parent(parent_id: int, session: Session = Depends(get_session), _admin: User = Depends(require_admin)):
    return _set_active(session, parent_id, False)


@router.post("/{parent_id}/reset-password")
def reset_parent_password(
    parent_id: int,
    payload: PasswordReset,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin),
):
    """Sets a new password for a parent. It ends their sessions at once and makes them choose their own at
    next sign-in. The password is checked against the same policy as every other password, is never stored
    except as a hash, and appears in no response and no log."""
    parent = _get_parent(session, parent_id)
    apply_admin_reset(session, parent, admin, payload.new_password)
    session.refresh(parent)
    return {
        "message": "Password reset. The parent must choose a new password at next sign-in.",
        "parent": _readable(session, parent),
    }


@router.post("/{parent_id}/children", status_code=status.HTTP_201_CREATED)
def link_child(
    parent_id: int,
    payload: LinkChild,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin),
):
    parent = _get_parent(session, parent_id)
    student = _linkable_student(session, payload.student_id)
    existing = session.exec(select(ParentStudentLink).where(ParentStudentLink.parent_id == parent.id)).all()
    if any(link.student_id == student.id for link in existing):
        raise HTTPException(status_code=409, detail=f"{student.name} is already linked to this parent.")
    if len(existing) >= portal.MAX_CHILDREN_PER_PARENT:
        raise HTTPException(status_code=422, detail=f"A parent account can have at most {portal.MAX_CHILDREN_PER_PARENT} children.")
    session.add(ParentStudentLink(
        parent_id=parent.id, student_id=student.id, relationship=payload.relationship, created_by=admin.id))
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail=f"{student.name} is already linked to this parent.")
    return _readable(session, parent)


@router.delete("/{parent_id}/children/{student_id}")
def unlink_child(
    parent_id: int,
    student_id: int,
    session: Session = Depends(get_session),
    _admin: User = Depends(require_admin),
):
    parent = _get_parent(session, parent_id)
    link = session.exec(
        select(ParentStudentLink).where(
            ParentStudentLink.parent_id == parent.id, ParentStudentLink.student_id == student_id)
    ).first()
    if link is None:
        raise HTTPException(status_code=404, detail="That child is not linked to this parent.")
    session.delete(link)
    session.commit()
    return _readable(session, parent)


# ── Administrator: which exams parents may see ──────────────────────────────

class PublishRequest(BaseModel):
    academic_year_id: int
    exam_type: ExamType
    published: bool


def _exam_rows(session: Session) -> List[dict]:
    recorded = session.exec(
        select(Result.academic_year_id, Result.exam_type, func.count(func.distinct(Result.student_id)))
        .where(col(Result.academic_year_id).is_not(None))
        .group_by(Result.academic_year_id, Result.exam_type)
    ).all()
    published = {(row.academic_year_id, row.exam_type): row for row in session.exec(select(PublishedExam)).all()}
    labels = {year.id: year.label for year in session.exec(select(AcademicYear)).all()}
    rows = [
        {
            "academic_year_id": year_id, "exam_type": exam_type, "session": labels.get(year_id),
            "students_with_marks": students,
            "published": (year_id, exam_type) in published,
            "published_at": utc_iso(published[(year_id, exam_type)].published_at) if (year_id, exam_type) in published else None,
        }
        for year_id, exam_type, students in recorded
    ]
    # Newest session first, and the final before the midterm within a session.
    return sorted(rows, key=lambda row: (row["academic_year_id"], row["exam_type"] == "Final Term"), reverse=True)


@publishing_router.get("")
def list_exams(session: Session = Depends(get_session), _admin: User = Depends(require_admin)):
    return _exam_rows(session)


@publishing_router.put("")
def set_exam_published(
    payload: PublishRequest,
    session: Session = Depends(get_session),
    admin: User = Depends(require_admin),
):
    exists = session.exec(
        select(Result.id).where(Result.academic_year_id == payload.academic_year_id, Result.exam_type == payload.exam_type)
    ).first()
    if exists is None:
        raise HTTPException(status_code=404, detail="No marks are recorded for that exam.")
    current = session.exec(
        select(PublishedExam).where(
            PublishedExam.academic_year_id == payload.academic_year_id, PublishedExam.exam_type == payload.exam_type)
    ).first()
    if payload.published and current is None:
        session.add(PublishedExam(
            academic_year_id=payload.academic_year_id, exam_type=payload.exam_type, published_by=admin.id))
    elif not payload.published and current is not None:
        session.delete(current)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()  # published twice at the same moment: it is published, which is what was asked
    return _exam_rows(session)


# ── The parent's own portal ─────────────────────────────────────────────────

def _child(session: Session, parent: User, student_id: int) -> Student:
    return portal.linked_student(session, parent, student_id)


@portal_router.get("/profile")
def parent_profile(session: Session = Depends(get_session), parent: User = Depends(require_parent)):
    """The signed-in parent's own account, read from the database rather than from the token."""
    return _readable(session, parent)


@portal_router.get("/children")
def my_children(session: Session = Depends(get_session), parent: User = Depends(require_parent)):
    month = portal.current_month()
    children = [portal.child_summary(session, parent, student, month) for student in portal.linked_students(session, parent)]
    return {
        "parent": {"username": parent.username, "full_name": parent.full_name},
        "month": month,
        "children": children,
        "totals": {
            "outstanding": round(sum(child["fees"]["outstanding"] for child in children), 2),
            "overdue": round(sum(child["fees"]["overdue"] for child in children), 2),
        },
    }


@portal_router.get("/children/{student_id}")
def my_child(student_id: int, session: Session = Depends(get_session), parent: User = Depends(require_parent)):
    student = _child(session, parent, student_id)
    return portal.child_summary(session, parent, student, portal.current_month())


@portal_router.get("/children/{student_id}/attendance")
def child_attendance(
    student_id: int,
    month: Optional[str] = None,
    session: Session = Depends(get_session),
    parent: User = Depends(require_parent),
):
    return portal.attendance_view(session, _child(session, parent, student_id), month)


@portal_router.get("/children/{student_id}/results")
def child_results(
    student_id: int,
    exam_type: Optional[ExamType] = None,
    academic_year_id: Optional[int] = None,
    session: Session = Depends(get_session),
    parent: User = Depends(require_parent),
):
    return portal.results_view(session, _child(session, parent, student_id), exam_type, academic_year_id)


@portal_router.get("/children/{student_id}/report-card/pdf")
def child_report_card(
    student_id: int,
    exam_type: Optional[ExamType] = None,
    academic_year_id: Optional[int] = None,
    session: Session = Depends(get_session),
    parent: User = Depends(require_parent),
):
    student = _child(session, parent, student_id)
    marks = portal.published_marks(session, student.id)
    # The exam is chosen from published marks only, so an unreleased exam can never be picked.
    chosen = select_exam(marks, exam_type, academic_year_id)
    if not chosen:
        raise HTTPException(status_code=404, detail="No published results for this exam yet.")
    return download_report_card(
        student.id, exam_type=chosen[0].exam_type, academic_year_id=chosen[0].academic_year_id,
        session=session, _user=parent)


@portal_router.get("/children/{student_id}/fees")
def child_fees(student_id: int, session: Session = Depends(get_session), parent: User = Depends(require_parent)):
    return portal.fees_view(session, _child(session, parent, student_id))


@portal_router.get("/children/{student_id}/invoices/{invoice_id}/challan/pdf")
def child_challan(
    student_id: int,
    invoice_id: int,
    session: Session = Depends(get_session),
    parent: User = Depends(require_parent),
):
    student = _child(session, parent, student_id)
    invoice = session.get(Invoice, invoice_id)
    if invoice is None or invoice.student_id != student.id:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return download_challan_pdf(id=invoice.id, session=session, _user=parent)


@portal_router.get("/children/{student_id}/payments/{payment_id}/receipt")
def child_receipt(
    student_id: int,
    payment_id: int,
    session: Session = Depends(get_session),
    parent: User = Depends(require_parent),
) -> Response:
    student = _child(session, parent, student_id)
    payment = session.get(Payment, payment_id)
    invoice = session.get(Invoice, payment.invoice_id) if payment else None
    if invoice is None or invoice.student_id != student.id:
        raise HTTPException(status_code=404, detail="Payment not found")
    return download_payment_receipt(payment_id=payment.id, session=session, _user=parent)
