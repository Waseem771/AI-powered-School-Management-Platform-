"""Admissions rules: status workflow, application numbers, roll numbers, and enrollment.

Routers stay thin and call these. Enrollment creates a Student with the same validation as
POST /students, and commits the student and the application together or not at all.
"""
from datetime import date, datetime, timezone
from typing import Dict, Iterable, List, Optional

from fastapi import HTTPException, status as http_status
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, func, select, update

from models.admission import (
    ALLOWED_TRANSITIONS,
    DEFAULT_DOCUMENTS,
    STATUS_APPROVED,
    STATUS_ENROLLED,
    STATUS_LABELS,
    STATUS_NEW,
    STATUS_REJECTED,
    STATUSES,
    AdmissionApplication,
    AdmissionAssessment,
    AdmissionDocumentChecklist,
    AdmissionStatusHistory,
)
from models.fee import AcademicYear, FeeStructure
from models.student import Student, StudentCreate
from services.fee_ledger import school_today

STAFF_ROLES = frozenset({"admin", "principal", "registrar", "staff"})
# Approving and rejecting is the school's decision, so it is limited to leadership.
DECISION_ROLES = frozenset({"admin", "principal"})
DECISION_STATUSES = (STATUS_APPROVED, STATUS_REJECTED)
REJECTION_NOTE_MIN = 5


def _now() -> datetime:
    return datetime.now(timezone.utc)


def conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=detail)


# ── Permissions ─────────────────────────────────────────────────────────────

def require_roles(user, allowed: Iterable[str]) -> None:
    if (user.role or "").lower() not in allowed:
        raise HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail="You do not have permission to do this.")


# ── Lookups ─────────────────────────────────────────────────────────────────

def get_application_or_404(session: Session, application_id: int) -> AdmissionApplication:
    application = session.get(AdmissionApplication, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


def resolve_academic_year(session: Session, year_id: Optional[int]) -> AcademicYear:
    if year_id is not None:
        year = session.get(AcademicYear, year_id)
        if not year:
            raise HTTPException(status_code=422, detail="That academic session does not exist.")
        return year
    year = session.exec(select(AcademicYear).where(AcademicYear.is_current == True)).first()  # noqa: E712
    if not year:
        raise HTTPException(status_code=409, detail="No current academic session is set up yet.")
    return year


# ── Application numbers ─────────────────────────────────────────────────────

def next_application_number(session: Session, on: date) -> str:
    """ADM-2026-0001, counting up within the year. The unique index is the final guard."""
    prefix = f"ADM-{on.year}-"
    latest = session.exec(
        select(AdmissionApplication.application_number)
        .where(col(AdmissionApplication.application_number).startswith(prefix))
        .order_by(col(AdmissionApplication.application_number).desc())
    ).first()
    sequence = int(latest.rsplit("-", 1)[1]) + 1 if latest else 1
    return f"{prefix}{sequence:04d}"


def create_application(session: Session, data, created_by: str) -> AdmissionApplication:
    year = resolve_academic_year(session, data.academic_year_id)
    applied_on = data.application_date or school_today()

    for _attempt in range(5):
        application = AdmissionApplication(
            application_number=next_application_number(session, applied_on),
            academic_year_id=year.id,
            application_date=applied_on,
            created_by=created_by,
            **data.model_dump(exclude={"academic_year_id", "application_date", "documents_received"}),
        )
        session.add(application)
        try:
            session.flush()
        except IntegrityError:
            # Another request took this number a moment ago. Try the next one.
            session.rollback()
            continue

        received = set(data.documents_received)
        for name in DEFAULT_DOCUMENTS:
            session.add(
                AdmissionDocumentChecklist(
                    application_id=application.id,
                    name=name,
                    received=name in received,
                    received_at=_now() if name in received else None,
                )
            )
        session.add(
            AdmissionStatusHistory(
                application_id=application.id, from_status=None, to_status=STATUS_NEW, changed_by=created_by,
                note="Application received.",
            )
        )
        session.commit()
        session.refresh(application)
        return application
    raise conflict("Could not assign an application number. Please try again.")


# ── Status workflow ─────────────────────────────────────────────────────────

def allowed_next(status: str, user_role: Optional[str] = None) -> List[str]:
    options = list(ALLOWED_TRANSITIONS.get(status, ()))
    if user_role is not None and user_role.lower() not in DECISION_ROLES:
        options = [option for option in options if option not in DECISION_STATUSES]
    return options


def change_status(session: Session, application: AdmissionApplication, to_status: str, note: Optional[str], user) -> AdmissionApplication:
    if to_status not in STATUSES or to_status == STATUS_ENROLLED:
        raise HTTPException(status_code=422, detail="Use the enrollment action to enroll an approved applicant.")
    if to_status in DECISION_STATUSES:
        require_roles(user, DECISION_ROLES)

    # Take the write lock before reading, so two staff cannot both move the same application.
    session.exec(update(AdmissionApplication).where(AdmissionApplication.id == application.id).values(status=AdmissionApplication.status))
    session.refresh(application)

    current = application.status
    if to_status not in ALLOWED_TRANSITIONS.get(current, ()):
        session.rollback()
        raise conflict(f"An application that is {STATUS_LABELS[current].lower()} cannot move to {STATUS_LABELS[to_status].lower()}.")
    if to_status == STATUS_REJECTED and (not note or len(note) < REJECTION_NOTE_MIN):
        session.rollback()
        raise HTTPException(status_code=422, detail="Please record the reason for rejecting this application.")

    application.status = to_status
    application.updated_at = _now()
    if to_status in DECISION_STATUSES:
        application.decision_note = note
        application.decided_at = _now()
        application.decided_by = user.username
    session.add(application)
    session.add(
        AdmissionStatusHistory(
            application_id=application.id, from_status=current, to_status=to_status, changed_by=user.username, note=note
        )
    )
    session.commit()
    session.refresh(application)
    return application


# ── Entry tests ─────────────────────────────────────────────────────────────

def percentage(obtained: float, maximum: float) -> float:
    return round(obtained / maximum * 100, 1) if maximum else 0.0


def assessment_dict(assessment: AdmissionAssessment) -> Dict:
    return {
        "id": assessment.id,
        "test_date": assessment.test_date.isoformat(),
        "subject": assessment.subject,
        "max_marks": assessment.max_marks,
        "obtained_marks": assessment.obtained_marks,
        "percentage": percentage(assessment.obtained_marks, assessment.max_marks),
        "remarks": assessment.remarks,
        "interview_notes": assessment.interview_notes,
        "recorded_by": assessment.recorded_by,
    }


# ── Roll numbers and enrollment ─────────────────────────────────────────────

def next_roll_number(session: Session) -> str:
    """One above the highest numeric roll number, in the school's 3-digit style (046). Never reuses a number."""
    numbers = [int(roll) for roll in session.exec(select(Student.roll_number)).all() if roll.isdigit()]
    candidate = max(numbers, default=0) + 1
    taken = set(session.exec(select(Student.roll_number)).all())
    while f"{candidate:03d}" in taken:
        candidate += 1
    return f"{candidate:03d}"


def enroll_application(session: Session, application_id: int, request, user) -> Dict:
    """Creates the student and marks the application enrolled in one transaction."""
    # Lock first: two clicks, or two staff, cannot both enroll the same applicant.
    session.exec(update(AdmissionApplication).where(AdmissionApplication.id == application_id).values(status=AdmissionApplication.status))
    application = session.get(AdmissionApplication, application_id, populate_existing=True)
    try:
        if not application:
            raise HTTPException(status_code=404, detail="Application not found")
        if application.student_id is not None or application.status == STATUS_ENROLLED:
            raise conflict("This applicant is already enrolled.")
        if application.status != STATUS_APPROVED:
            raise conflict("Only an approved application can be enrolled.")
        if request.confirm_academic_year_id != application.academic_year_id:
            raise conflict("The academic session does not match the application. Reload the page and check it.")
        if request.confirm_grade != application.applying_grade:
            raise conflict("The class does not match the application. Reload the page and check it.")

        roll_number = request.roll_number.strip() if request.roll_number else next_roll_number(session)
        # Same validation as adding a student by hand.
        student_in = StudentCreate(
            name=application.student_name,
            roll_number=roll_number,
            grade=application.applying_grade,
            section=request.section,
            guardian_name=application.guardian_name,
            phone=application.phone,
            dob=application.dob,
        )
        if session.exec(select(Student).where(Student.roll_number == student_in.roll_number)).first():
            raise conflict(f"Roll number {student_in.roll_number} is already in use.")

        student = Student(**student_in.model_dump())
        session.add(student)
        session.flush()

        application.student_id = student.id
        application.status = STATUS_ENROLLED
        application.enrolled_at = _now()
        application.updated_at = _now()
        session.add(application)
        record_enrollment_history(session, application, user.username, student.roll_number)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise conflict("This applicant or roll number was just enrolled by someone else. Reload and check.")
    except ValidationError as error:
        session.rollback()
        problems = "; ".join(item["msg"].removeprefix("Value error, ") for item in error.errors())
        raise HTTPException(status_code=422, detail=f"The student record could not be created: {problems}")
    except Exception:
        session.rollback()
        raise

    session.refresh(student)
    session.refresh(application)
    return {"student_id": student.id, "roll_number": student.roll_number, "grade": student.grade, "section": student.section}


def record_enrollment_history(session: Session, application: AdmissionApplication, username: str, roll_number: str) -> None:
    session.add(
        AdmissionStatusHistory(
            application_id=application.id,
            from_status=STATUS_APPROVED,
            to_status=STATUS_ENROLLED,
            changed_by=username,
            note=f"Enrolled with roll number {roll_number}.",
        )
    )


# ── Fees ────────────────────────────────────────────────────────────────────

def configured_monthly_fee(session: Session, grade: str, academic_year_id: int) -> Optional[float]:
    """The school's own configured amount for the class, or None. Nothing is invented."""
    structure = session.exec(
        select(FeeStructure).where(FeeStructure.grade == grade, FeeStructure.academic_year_id == academic_year_id)
    ).first() or session.exec(select(FeeStructure).where(FeeStructure.grade == grade)).first()
    return structure.amount if structure else None


# ── Listing and counts ──────────────────────────────────────────────────────

def status_counts(session: Session) -> Dict[str, int]:
    rows = session.exec(select(AdmissionApplication.status, func.count()).group_by(AdmissionApplication.status)).all()
    counts = {name: 0 for name in STATUSES}
    counts.update({name: total for name, total in rows})
    counts["total"] = sum(counts[name] for name in STATUSES)
    return counts


def checklist_status(session: Session, application_id: int) -> List[AdmissionDocumentChecklist]:
    return list(
        session.exec(
            select(AdmissionDocumentChecklist).where(AdmissionDocumentChecklist.application_id == application_id).order_by(AdmissionDocumentChecklist.id)
        ).all()
    )


def application_summary_row(application: AdmissionApplication) -> Dict:
    return {
        "id": application.id,
        "application_number": application.application_number,
        "student_name": application.student_name,
        "applying_grade": application.applying_grade,
        "guardian_name": application.guardian_name,
        "phone": application.phone,
        "status": application.status,
        "status_label": STATUS_LABELS[application.status],
        "application_date": application.application_date.isoformat(),
        "academic_year_id": application.academic_year_id,
        "student_id": application.student_id,
    }
