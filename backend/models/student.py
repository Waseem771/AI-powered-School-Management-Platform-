import re
import unicodedata
from datetime import date, datetime, timezone
from typing import Annotated, Optional

from pydantic import AfterValidator, BaseModel
from sqlmodel import Field, SQLModel

from config import GRADES, SECTIONS

NAME_MIN_LENGTH = 2
NAME_MAX_LENGTH = 100
NAME_PUNCTUATION = " .'-"
ROLL_NUMBER_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9/-]{0,19}")
PHONE_PATTERN = re.compile(r"\+?[0-9][0-9 ()-]*")
PHONE_MIN_DIGITS = 10
PHONE_MAX_DIGITS = 15
STUDENT_MIN_AGE_YEARS = 3
STUDENT_MAX_AGE_YEARS = 30


def _clean_name(value: str, label: str) -> str:
    """Letters from any language, including Urdu, with the punctuation real names use."""
    cleaned = " ".join(value.split())
    if not NAME_MIN_LENGTH <= len(cleaned) <= NAME_MAX_LENGTH:
        raise ValueError(f"{label} must be {NAME_MIN_LENGTH} to {NAME_MAX_LENGTH} characters long.")
    for character in cleaned:
        is_letter = unicodedata.category(character)[0] in "LM"
        if not is_letter and character not in NAME_PUNCTUATION:
            raise ValueError(f"{label} can only contain letters, spaces, and . ' -")
    return cleaned


def _clean_student_name(value: str) -> str:
    return _clean_name(value, "Student name")


def _clean_guardian_name(value: str) -> str:
    return _clean_name(value, "Guardian name")


def _clean_roll_number(value: str) -> str:
    cleaned = value.strip()
    if not ROLL_NUMBER_PATTERN.fullmatch(cleaned):
        raise ValueError("Roll number must be 1 to 20 letters or digits, and may include - or /")
    return cleaned


def _check_grade(value: str) -> str:
    if value not in GRADES:
        raise ValueError(f"Grade must be one of: {', '.join(GRADES)}.")
    return value


def _check_section(value: str) -> str:
    if value not in SECTIONS:
        raise ValueError(f"Section must be one of: {', '.join(SECTIONS)}.")
    return value


def _clean_phone(value: str) -> str:
    cleaned = value.strip()
    digit_count = sum(character.isdigit() for character in cleaned)
    if not PHONE_PATTERN.fullmatch(cleaned) or not PHONE_MIN_DIGITS <= digit_count <= PHONE_MAX_DIGITS:
        raise ValueError("Enter a valid phone number, such as 0300-1234567.")
    return cleaned


def _clean_dob(value: Optional[str]) -> Optional[str]:
    """Stored as YYYY-MM-DD. Blank means unknown, and is never replaced with a made-up date."""
    if value is None or not value.strip():
        return None
    try:
        born = date.fromisoformat(value.strip())
    except ValueError:
        raise ValueError("Date of birth must be a real date, written YYYY-MM-DD.")
    age_in_years = date.today().year - born.year
    if not STUDENT_MIN_AGE_YEARS <= age_in_years <= STUDENT_MAX_AGE_YEARS:
        raise ValueError(
            f"Date of birth must make the student {STUDENT_MIN_AGE_YEARS} to {STUDENT_MAX_AGE_YEARS} years old."
        )
    return born.isoformat()


StudentName = Annotated[str, AfterValidator(_clean_student_name)]
GuardianName = Annotated[str, AfterValidator(_clean_guardian_name)]
RollNumber = Annotated[str, AfterValidator(_clean_roll_number)]
GradeName = Annotated[str, AfterValidator(_check_grade)]
SectionName = Annotated[str, AfterValidator(_check_section)]
PhoneNumber = Annotated[str, AfterValidator(_clean_phone)]
DateOfBirth = Annotated[Optional[str], AfterValidator(_clean_dob)]


class StudentBase(SQLModel):
    name: str
    roll_number: str = Field(index=True, unique=True)
    grade: str = Field(index=True)
    section: str = Field(default="A")
    guardian_name: str
    phone: str
    dob: Optional[str] = None  # YYYY-MM-DD string
    archived_at: Optional[datetime] = None  # Set when a student leaves. History is always kept.


class Student(StudentBase, table=True):
    __tablename__ = "students"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StudentCreate(BaseModel):
    name: StudentName
    roll_number: RollNumber
    grade: GradeName
    section: SectionName = "A"
    guardian_name: GuardianName
    phone: PhoneNumber
    dob: DateOfBirth = None


class StudentUpdate(BaseModel):
    """Leave a field out to keep it. An explicit null is rejected, except for dob."""

    name: StudentName = None
    roll_number: RollNumber = None
    grade: GradeName = None
    section: SectionName = None
    guardian_name: GuardianName = None
    phone: PhoneNumber = None
    dob: DateOfBirth = None


class StudentRead(StudentBase):
    id: int
    created_at: datetime
