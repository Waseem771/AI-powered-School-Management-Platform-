from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import Index
from sqlmodel import SQLModel, Field

INVOICE_STUDENT_MONTH_INDEX = "uq_invoices_student_month"

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
    # Existing databases get this index from migrate_db.py; create_all only adds it to new ones.
    __table_args__ = (Index(INVOICE_STUDENT_MONTH_INDEX, "student_id", "month", unique=True),)

    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(index=True, foreign_key="students.id")
    amount: float
    month: str  # "November 2026"
    due_date: str  # "10-Nov-2026"
    challan_number: str = Field(index=True, unique=True)
    status: str = Field(default="pending", index=True)  # 'pending', 'partial' or 'paid'
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Payment(SQLModel, table=True):
    __tablename__ = "payments"

    id: Optional[int] = Field(default=None, primary_key=True)
    invoice_id: int = Field(index=True, foreign_key="invoices.id")
    amount_paid: float
    paid_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    payment_mode: str = Field(default="cash")  # cash, bank, online
