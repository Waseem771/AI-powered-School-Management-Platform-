"""New-student admissions. Applicants are not students until enrolled, so they live in their own tables.

These are new tables only: create_all adds them, and no existing table changes.
"""
import re
from datetime import date, datetime, timezone
from typing import Annotated, Literal, Optional

from pydantic import AfterValidator, BaseModel, Field as PydanticField, field_validator, model_validator
from sqlalchemy import CheckConstraint, Index, UniqueConstraint
from sqlmodel import Field, SQLModel

from models.student import (
    GradeName,
    PhoneNumber,
    _clean_name,
    _clean_phone,
    _clean_dob,
)

# Workflow: new -> under_review -> (test_interview) -> approved | rejected -> enrolled.
STATUS_NEW = "new"
STATUS_UNDER_REVIEW = "under_review"
STATUS_TEST = "test_interview"
STATUS_APPROVED = "approved"
STATUS_REJECTED = "rejected"
STATUS_ENROLLED = "enrolled"
STATUSES = (STATUS_NEW, STATUS_UNDER_REVIEW, STATUS_TEST, STATUS_APPROVED, STATUS_REJECTED, STATUS_ENROLLED)

STATUS_LABELS = {
    STATUS_NEW: "New application",
    STATUS_UNDER_REVIEW: "Under review",
    STATUS_TEST: "Entry test / interview",
    STATUS_APPROVED: "Approved",
    STATUS_REJECTED: "Rejected",
    STATUS_ENROLLED: "Enrolled",
}

# Enrolled is reached only through the enrollment action, never by a plain status change.
ALLOWED_TRANSITIONS = {
    STATUS_NEW: (STATUS_UNDER_REVIEW, STATUS_REJECTED),
    STATUS_UNDER_REVIEW: (STATUS_TEST, STATUS_APPROVED, STATUS_REJECTED),
    STATUS_TEST: (STATUS_UNDER_REVIEW, STATUS_APPROVED, STATUS_REJECTED),
    STATUS_APPROVED: (STATUS_REJECTED,),
    STATUS_REJECTED: (STATUS_UNDER_REVIEW,),
    STATUS_ENROLLED: (),
}

# What the school checks on a new application. Staff tick each one off as it arrives.
DEFAULT_DOCUMENTS = (
    "Birth certificate or B-Form",
    "Guardian CNIC copy",
    "Previous school leaving certificate",
    "Previous result card",
    "Passport-size photographs",
)

GENDERS = ("Male", "Female", "Other")
RELATIONSHIPS = ("Father", "Mother", "Guardian", "Other")
NOTES_MAX = 1000
TEXT_MAX = 200
ADDRESS_MAX = 300
ENTRY_TEST_MAX_MARKS = 1000


def school_date_today() -> date:
    """Today's date at the school (Pakistan time), not the server's.

    The browser sends the school's date, and the server may run in UTC. Comparing the two would
    refuse an application made in the first hours of the school's day.
    """
    # Imported here so the models package never needs the services package while it loads.
    from services.fee_ledger import school_today

    return school_today()


class AdmissionApplication(SQLModel, table=True):
    __tablename__ = "admission_applications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('new','under_review','test_interview','approved','rejected','enrolled')",
            name="ck_admission_status",
        ),
        Index("ix_admission_student_link", "student_id", unique=True),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    application_number: str = Field(index=True, unique=True)
    academic_year_id: int = Field(index=True, foreign_key="academic_years.id")
    status: str = Field(default=STATUS_NEW, index=True)
    application_date: date = Field(default_factory=school_date_today)

    student_name: str
    dob: Optional[str] = None  # YYYY-MM-DD, same as students.dob
    gender: Optional[str] = None
    applying_grade: str = Field(index=True)
    previous_class: Optional[str] = None
    previous_school: Optional[str] = None
    previous_performance: Optional[str] = None

    guardian_name: str
    guardian_relationship: str = Field(default="Father")
    phone: str
    alt_phone: Optional[str] = None
    address: str

    staff_notes: Optional[str] = None
    decision_note: Optional[str] = None
    decided_at: Optional[datetime] = None
    decided_by: Optional[str] = None

    # Set once, at enrollment. The unique index above stops one student being linked twice.
    student_id: Optional[int] = Field(default=None, foreign_key="students.id")
    enrolled_at: Optional[datetime] = None

    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AdmissionDocumentChecklist(SQLModel, table=True):
    __tablename__ = "admission_documents"
    __table_args__ = (UniqueConstraint("application_id", "name", name="uq_admission_document"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(index=True, foreign_key="admission_applications.id")
    name: str
    received: bool = Field(default=False)
    received_at: Optional[datetime] = None


class AdmissionAssessment(SQLModel, table=True):
    """An entry test or interview for an applicant. Kept apart from the Results module on purpose."""

    __tablename__ = "admission_assessments"
    __table_args__ = (CheckConstraint("max_marks > 0 AND obtained_marks >= 0 AND obtained_marks <= max_marks", name="ck_admission_marks"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(index=True, foreign_key="admission_applications.id")
    test_date: date
    subject: str
    max_marks: float
    obtained_marks: float
    remarks: Optional[str] = None
    interview_notes: Optional[str] = None
    recorded_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AdmissionStatusHistory(SQLModel, table=True):
    """One row per status change, never edited or removed."""

    __tablename__ = "admission_status_history"

    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(index=True, foreign_key="admission_applications.id")
    from_status: Optional[str] = None
    to_status: str
    changed_by: Optional[str] = None
    note: Optional[str] = None
    changed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Request schemas ─────────────────────────────────────────────────────────

def _person_name(label: str):
    return lambda value: _clean_name(value, label)


def _optional_text(max_length: int, label: str):
    def check(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = " ".join(value.split()) if max_length <= TEXT_MAX else value.strip()
        if not cleaned:
            return None
        if len(cleaned) > max_length:
            raise ValueError(f"{label} must be at most {max_length} characters.")
        return cleaned

    return check


def _required_text(max_length: int, label: str, min_length: int = 1):
    def check(value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < min_length or len(cleaned) > max_length:
            raise ValueError(f"{label} must be {min_length} to {max_length} characters long.")
        return cleaned

    return check


def _optional_phone(value: Optional[str]) -> Optional[str]:
    if value is None or not value.strip():
        return None
    return _clean_phone(value)


def _required_dob(value: str) -> str:
    cleaned = _clean_dob(value)
    if not cleaned:
        raise ValueError("Date of birth is required.")
    return cleaned


def _optional_dob(value: Optional[str]) -> Optional[str]:
    return _clean_dob(value)


_ACADEMIC_SESSION_PATTERN = re.compile(r"\d{4}-\d{4}")

ApplicantName = Annotated[str, AfterValidator(_person_name("Student name"))]
GuardianNameField = Annotated[str, AfterValidator(_person_name("Guardian name"))]
Address = Annotated[str, AfterValidator(_required_text(ADDRESS_MAX, "Address", 5))]
OptionalSchool = Annotated[Optional[str], AfterValidator(_optional_text(TEXT_MAX, "This field"))]
OptionalNotes = Annotated[Optional[str], AfterValidator(_optional_text(NOTES_MAX, "Notes"))]
RequiredDob = Annotated[str, AfterValidator(_required_dob)]
OptionalPhone = Annotated[Optional[str], AfterValidator(_optional_phone)]


class ApplicationCreate(BaseModel):
    student_name: ApplicantName
    dob: RequiredDob
    gender: Optional[Literal["Male", "Female", "Other"]] = None
    applying_grade: GradeName
    previous_class: OptionalSchool = None
    previous_school: OptionalSchool = None
    previous_performance: OptionalSchool = None

    guardian_name: GuardianNameField
    guardian_relationship: Literal["Father", "Mother", "Guardian", "Other"] = "Father"
    phone: PhoneNumber
    alt_phone: OptionalPhone = None
    address: Address

    academic_year_id: Optional[int] = None  # Defaults to the current session.
    application_date: Optional[date] = None
    staff_notes: OptionalNotes = None
    # Documents already in hand when the form is filled in. Must be from the school's list.
    documents_received: list[str] = PydanticField(default_factory=list, max_length=len(DEFAULT_DOCUMENTS))

    @field_validator("application_date")
    @classmethod
    def not_in_future(cls, value: Optional[date]) -> Optional[date]:
        if value and value > school_date_today():
            raise ValueError("Application date cannot be in the future.")
        return value

    @field_validator("documents_received")
    @classmethod
    def known_documents(cls, value: list[str]) -> list[str]:
        unknown = [name for name in value if name not in DEFAULT_DOCUMENTS]
        if unknown:
            raise ValueError("Unknown document in the checklist.")
        return list(dict.fromkeys(value))


class ApplicationUpdate(BaseModel):
    """Leave a field out to keep it. Status is not changed here; it has its own action."""

    student_name: ApplicantName = None
    dob: RequiredDob = None
    gender: Optional[Literal["Male", "Female", "Other"]] = None
    applying_grade: GradeName = None
    previous_class: OptionalSchool = None
    previous_school: OptionalSchool = None
    previous_performance: OptionalSchool = None
    guardian_name: GuardianNameField = None
    guardian_relationship: Literal["Father", "Mother", "Guardian", "Other"] = None
    phone: PhoneNumber = None
    alt_phone: OptionalPhone = None
    address: Address = None
    staff_notes: OptionalNotes = None


class StatusChange(BaseModel):
    to_status: Literal["under_review", "test_interview", "approved", "rejected"]
    note: OptionalNotes = None


class DocumentUpdate(BaseModel):
    name: str
    received: bool

    @field_validator("name")
    @classmethod
    def known(cls, value: str) -> str:
        if value not in DEFAULT_DOCUMENTS:
            raise ValueError("Unknown document in the checklist.")
        return value


class AssessmentCreate(BaseModel):
    test_date: date
    subject: Annotated[str, AfterValidator(_required_text(100, "Subject", 2))]
    max_marks: float = PydanticField(gt=0, le=ENTRY_TEST_MAX_MARKS, allow_inf_nan=False)
    obtained_marks: float = PydanticField(ge=0, allow_inf_nan=False)
    remarks: OptionalNotes = None
    interview_notes: OptionalNotes = None

    @field_validator("test_date")
    @classmethod
    def not_far_future(cls, value: date) -> date:
        if (value - date.today()).days > 366:
            raise ValueError("Test date is too far in the future.")
        return value

    @field_validator("obtained_marks")
    @classmethod
    def whole_marks(cls, value: float) -> float:
        return round(value, 2)

    @model_validator(mode="after")
    def marks_within_maximum(self):
        if self.obtained_marks > self.max_marks:
            raise ValueError("Obtained marks cannot be more than the maximum marks.")
        return self


class EnrollRequest(BaseModel):
    section: Literal["A", "B"] = "A"
    # Staff confirm the session and class on screen; the server checks them against the application.
    confirm_academic_year_id: int
    confirm_grade: GradeName
    roll_number: Optional[str] = None  # Blank means the next free number.


class PolicyQuestion(BaseModel):
    question: Annotated[str, AfterValidator(_required_text(300, "Question", 3))]


class ReminderRequest(BaseModel):
    language: Literal["en", "ur"] = "en"
