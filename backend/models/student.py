from typing import Optional
from datetime import datetime, date
from sqlmodel import SQLModel, Field

class StudentBase(SQLModel):
    name: str
    roll_number: str = Field(index=True, unique=True)
    grade: str = Field(index=True)
    section: str = Field(default="A")
    guardian_name: str
    phone: str
    dob: Optional[str] = None  # YYYY-MM-DD string

class Student(StudentBase, table=True):
    __tablename__ = "students"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class StudentCreate(StudentBase):
    pass

class StudentUpdate(SQLModel):
    name: Optional[str] = None
    roll_number: Optional[str] = None
    grade: Optional[str] = None
    section: Optional[str] = None
    guardian_name: Optional[str] = None
    phone: Optional[str] = None
    dob: Optional[str] = None

class StudentRead(StudentBase):
    id: int
    created_at: datetime
