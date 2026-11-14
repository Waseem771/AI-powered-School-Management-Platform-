"""New-student admissions: applications, documents, entry tests, decisions, enrollment, and AI help.

Every route needs a signed-in staff member. Approving and rejecting is limited to leadership roles.
The older /api/admissions-crew/evaluate route is untouched and lives in routers/admissions_crew.py.
"""
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, col, func, or_, select

from config import GRADES, SECTIONS
from database import get_session
from models.admission import (
    DEFAULT_DOCUMENTS,
    GENDERS,
    RELATIONSHIPS,
    STATUS_ENROLLED,
    STATUS_LABELS,
    STATUSES,
    AdmissionApplication,
    AdmissionAssessment,
    AdmissionStatusHistory,
    ApplicationCreate,
    ApplicationUpdate,
    AssessmentCreate,
    DocumentUpdate,
    EnrollRequest,
    PolicyQuestion,
    ReminderRequest,
    StatusChange,
)
from models.fee import AcademicYear
from routers.auth import get_current_user
from services import admission_assistant, admissions
from services.admissions import STAFF_ROLES

router = APIRouter(prefix="/admissions", tags=["Admissions"])


def staff_user(user=Depends(get_current_user)):
    admissions.require_roles(user, STAFF_ROLES)
    return user


def _application_dict(session: Session, application: AdmissionApplication, user) -> dict:
    checklist = admissions.checklist_status(session, application.id)
    assessments = session.exec(
        select(AdmissionAssessment).where(AdmissionAssessment.application_id == application.id).order_by(AdmissionAssessment.test_date, AdmissionAssessment.id)
    ).all()
    history = session.exec(
        select(AdmissionStatusHistory).where(AdmissionStatusHistory.application_id == application.id).order_by(AdmissionStatusHistory.id)
    ).all()
    years = {year.id: year.label for year in session.exec(select(AcademicYear)).all()}
    return {
        **application.model_dump(mode="json"),
        "status_label": STATUS_LABELS[application.status],
        "academic_session": years.get(application.academic_year_id),
        "allowed_next_statuses": [
            {"value": value, "label": STATUS_LABELS[value]} for value in admissions.allowed_next(application.status, user.role)
        ],
        "can_enroll": application.status == "approved" and application.student_id is None,
        "documents": [
            {"name": item.name, "received": item.received, "received_at": item.received_at.isoformat() if item.received_at else None}
            for item in checklist
        ],
        "assessments": [admissions.assessment_dict(item) for item in assessments],
        "history": [
            {
                "from_status": item.from_status,
                "to_status": item.to_status,
                "to_label": STATUS_LABELS[item.to_status],
                "changed_by": item.changed_by,
                "note": item.note,
                "changed_at": item.changed_at.isoformat(),
            }
            for item in history
        ],
    }


# ── Reference data and overview ─────────────────────────────────────────────

@router.get("/options")
def get_options(session: Session = Depends(get_session), _user=Depends(staff_user)):
    years = session.exec(select(AcademicYear).order_by(AcademicYear.id.desc())).all()
    return {
        "grades": GRADES,
        "sections": SECTIONS,
        "documents": list(DEFAULT_DOCUMENTS),
        "genders": list(GENDERS),
        "relationships": list(RELATIONSHIPS),
        "statuses": [{"value": value, "label": STATUS_LABELS[value]} for value in STATUSES],
        "academic_years": [{"id": year.id, "label": year.label, "is_current": year.is_current} for year in years],
    }


@router.get("/stats")
def get_stats(session: Session = Depends(get_session), _user=Depends(staff_user)):
    return admissions.status_counts(session)


@router.get("/next-roll-number")
def preview_roll_number(session: Session = Depends(get_session), _user=Depends(staff_user)):
    return {"roll_number": admissions.next_roll_number(session)}


# ── Applications ────────────────────────────────────────────────────────────

@router.get("")
def list_applications(
    search: Optional[str] = Query(default=None, max_length=100),
    status: Optional[Literal["new", "under_review", "test_interview", "approved", "rejected", "enrolled"]] = None,
    grade: Optional[str] = Query(default=None, max_length=20),
    academic_year_id: Optional[int] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    session: Session = Depends(get_session),
    _user=Depends(staff_user),
):
    query = select(AdmissionApplication)
    if status:
        query = query.where(AdmissionApplication.status == status)
    if grade:
        query = query.where(AdmissionApplication.applying_grade == grade)
    if academic_year_id is not None:
        query = query.where(AdmissionApplication.academic_year_id == academic_year_id)
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                col(AdmissionApplication.student_name).ilike(pattern),
                col(AdmissionApplication.application_number).ilike(pattern),
                col(AdmissionApplication.guardian_name).ilike(pattern),
                col(AdmissionApplication.phone).ilike(pattern),
            )
        )
    total = session.exec(select(func.count()).select_from(query.subquery())).one()
    rows = session.exec(
        query.order_by(col(AdmissionApplication.id).desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "items": [admissions.application_summary_row(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("", status_code=201)
def create_application(data: ApplicationCreate, session: Session = Depends(get_session), user=Depends(staff_user)):
    application = admissions.create_application(session, data, user.username)
    return _application_dict(session, application, user)


@router.post("/assistant/policy")
def ask_policy(body: PolicyQuestion, _user=Depends(staff_user)):
    """Only the question text is searched. No applicant record is attached to it."""
    from services.rag_service import rag_service

    return admission_assistant.explain_policy(body.question, rag_service)


@router.get("/{application_id}")
def get_application(application_id: int, session: Session = Depends(get_session), user=Depends(staff_user)):
    return _application_dict(session, admissions.get_application_or_404(session, application_id), user)


@router.put("/{application_id}")
def update_application(
    application_id: int, data: ApplicationUpdate, session: Session = Depends(get_session), user=Depends(staff_user)
):
    application = admissions.get_application_or_404(session, application_id)
    if application.status == STATUS_ENROLLED:
        raise admissions.conflict("An enrolled applicant's record is now the student's record. Edit it under Students.")
    changes = data.model_dump(exclude_unset=True)
    required = {"student_name", "dob", "applying_grade", "guardian_name", "guardian_relationship", "phone", "address"}
    if any(changes.get(name, "x") is None for name in required):
        raise HTTPException(status_code=422, detail="Required fields cannot be cleared.")
    for key, value in changes.items():
        setattr(application, key, value)
    application.updated_at = datetime.now(timezone.utc)
    session.add(application)
    session.commit()
    session.refresh(application)
    return _application_dict(session, application, user)


@router.post("/{application_id}/status")
def change_application_status(
    application_id: int, body: StatusChange, session: Session = Depends(get_session), user=Depends(staff_user)
):
    application = admissions.get_application_or_404(session, application_id)
    application = admissions.change_status(session, application, body.to_status, body.note, user)
    return _application_dict(session, application, user)


@router.put("/{application_id}/documents")
def update_document(
    application_id: int, body: DocumentUpdate, session: Session = Depends(get_session), user=Depends(staff_user)
):
    application = admissions.get_application_or_404(session, application_id)
    if application.status == STATUS_ENROLLED:
        raise admissions.conflict("This applicant is already enrolled.")
    item = next((row for row in admissions.checklist_status(session, application_id) if row.name == body.name), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Document not found on this checklist")
    item.received = body.received
    item.received_at = datetime.now(timezone.utc) if body.received else None
    session.add(item)
    application.updated_at = datetime.now(timezone.utc)
    session.add(application)
    session.commit()
    session.refresh(application)
    return _application_dict(session, application, user)


@router.post("/{application_id}/assessments", status_code=201)
def add_assessment(
    application_id: int, body: AssessmentCreate, session: Session = Depends(get_session), user=Depends(staff_user)
):
    application = admissions.get_application_or_404(session, application_id)
    if application.status == STATUS_ENROLLED:
        raise admissions.conflict("This applicant is already enrolled.")
    session.add(AdmissionAssessment(application_id=application_id, recorded_by=user.username, **body.model_dump()))
    session.commit()
    return _application_dict(session, application, user)


@router.post("/{application_id}/enroll", status_code=201)
def enroll(application_id: int, body: EnrollRequest, session: Session = Depends(get_session), user=Depends(staff_user)):
    result = admissions.enroll_application(session, application_id, body, user)
    return {"message": "Applicant enrolled", **result}


@router.get("/{application_id}/fee-policy")
def get_fee_policy(application_id: int, session: Session = Depends(get_session), _user=Depends(staff_user)):
    """The school's configured monthly fee for this class, if any. Nothing is charged by looking at it."""
    application = admissions.get_application_or_404(session, application_id)
    amount = admissions.configured_monthly_fee(session, application.applying_grade, application.academic_year_id)
    return {"configured": amount is not None, "monthly_fee": amount, "student_id": application.student_id}


# ── AI help for staff. Drafts only; never a decision. ───────────────────────

@router.get("/{application_id}/assistant/missing-documents")
def assistant_missing_documents(application_id: int, session: Session = Depends(get_session), _user=Depends(staff_user)):
    admissions.get_application_or_404(session, application_id)
    return {"missing_documents": admission_assistant.missing_documents(admissions.checklist_status(session, application_id))}


@router.post("/{application_id}/assistant/reminder")
def assistant_reminder(
    application_id: int, body: ReminderRequest, session: Session = Depends(get_session), _user=Depends(staff_user)
):
    application = admissions.get_application_or_404(session, application_id)
    missing = admission_assistant.missing_documents(admissions.checklist_status(session, application_id))
    return admission_assistant.draft_reminder(application, missing, body.language)


@router.get("/{application_id}/assistant/summary")
def assistant_summary(application_id: int, session: Session = Depends(get_session), _user=Depends(staff_user)):
    application = admissions.get_application_or_404(session, application_id)
    assessments = session.exec(select(AdmissionAssessment).where(AdmissionAssessment.application_id == application_id)).all()
    return admission_assistant.summarize_application(application, admissions.checklist_status(session, application_id), assessments)
