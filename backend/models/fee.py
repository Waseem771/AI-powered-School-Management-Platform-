from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

class AcademicYear(SQLModel, table=True):
    __tablename__ = "academic_years"

    id: Optional[int] = Field(default=None, primary_key=True)
    label: str = Field(default="2025-2026")
    is_current: bool = Field(default=True)

class FeeStructure(SQLModel, table=True):
    __tablename__ = "fee_structures"

    id: Optional[int] = Field(default=None, primary_key=True)
    grade: str = Field(index=True)
    label: str = Field(default="Monthly Tuition Fee")
    amount: float = Field(default=3500.0)
    academic_year_id: Optional[int] = Field(default=None, foreign_key="academic_years.id")

class Invoice(SQLModel, table=True):
    __tablename__ = "invoices"

    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(index=True, foreign_key="students.id")
    amount: float = Field(default=4000.0)
    month: str = Field(default="October 2025")
    due_date: str = Field(default="10-Oct-2025")
    challan_number: str = Field(index=True, unique=True)
    status: str = Field(default="pending", index=True)  # 'paid' or 'pending'
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Payment(SQLModel, table=True):
    __tablename__ = "payments"

    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_id: int = Field(index=True, foreign_key="invoices.id")
    amount_paid: float
    paid_at: datetime = Field(default_factory=datetime.utcnow)
    payment_mode: str = Field(default="cash")  # cash, bank, online
