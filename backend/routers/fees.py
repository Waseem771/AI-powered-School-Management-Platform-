import random
from datetime import date, datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status as http_status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select, update

from config import TUITION_FEE_MONTHLY
from database import get_session
from models.fee import Invoice, Payment
from models.student import Student
from routers.auth import get_current_user
from services.fee_ledger import (
    DUE_DATE_DISPLAY_FORMAT,
    invoice_money,
    outstanding_balance,
    paid_by_invoice,
    payment_status,
    school_today,
    school_totals,
)
from services.pdf_service import generate_fee_challan_pdf

router = APIRouter(prefix="/fees", tags=["Fees"])

MAX_MONEY_AMOUNT = 10_000_000
MIN_PAYMENT_AMOUNT = 0.01
MONTH_FORMAT = "%B %Y"


class ChallanGenerateRequest(BaseModel):
    student_id: int
    amount: float = Field(gt=0, le=MAX_MONEY_AMOUNT, allow_inf_nan=False)
    month: str  # "November 2026"
    due_date: date

    @field_validator("month")
    @classmethod
    def normalize_month(cls, value: str) -> str:
        try:
            return datetime.strptime(value.strip(), MONTH_FORMAT).strftime(MONTH_FORMAT)
        except ValueError:
            raise ValueError("month must look like 'November 2026'")


class PaymentRequest(BaseModel):
    # Leave out the amount to settle whatever is still owed.
    amount_paid: Optional[float] = Field(default=None, ge=MIN_PAYMENT_AMOUNT, le=MAX_MONEY_AMOUNT, allow_inf_nan=False)
    payment_mode: Literal["cash", "bank", "online"] = "cash"


def _unique_challan_number(session: Session) -> str:
    for _ in range(20):
        candidate = f"CHN-{random.randint(1000, 9999)}"
        if not session.exec(select(Invoice).where(Invoice.challan_number == candidate)).first():
            return candidate
    # 4-digit space is crowded; widen it rather than fail on the unique constraint
    while True:
        candidate = f"CHN-{random.randint(100000, 999999)}"
        if not session.exec(select(Invoice).where(Invoice.challan_number == candidate)).first():
            return candidate


def _duplicate_challan_error(month: str) -> HTTPException:
    return HTTPException(
        status_code=http_status.HTTP_409_CONFLICT,
        detail=f"This student already has a challan for {month}.",
    )


@router.get("")
def get_invoices(
    status: Optional[Literal["pending", "partial", "paid"]] = None,
    grade: Optional[str] = None,
    student_id: Optional[int] = None,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    query = select(Invoice, Student).join(Student, Invoice.student_id == Student.id)
    if status:
        query = query.where(Invoice.status == status)
    if grade:
        query = query.where(Student.grade == grade)
    if student_id is not None:
        query = query.where(Invoice.student_id == student_id)

    rows = session.exec(query.order_by(Invoice.id.desc())).all()
    paid = paid_by_invoice(session)
    today = school_today()
    return [
        {
            "id": invoice.id,
            "student_id": student.id,
            "student_name": student.name,
            "roll_number": student.roll_number,
            "grade": student.grade,
            "section": student.section,
            "amount": invoice.amount,
            "month": invoice.month,
            "due_date": invoice.due_date,
            "challan_number": invoice.challan_number,
            "status": invoice.status,
            "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
            **invoice_money(invoice, paid.get(invoice.id, 0.0), today),
        }
        for invoice, student in rows
    ]


@router.get("/summary")
def get_fee_summary(session: Session = Depends(get_session), _user=Depends(get_current_user)):
    return school_totals(session)


@router.post("/generate", status_code=http_status.HTTP_201_CREATED)
def generate_challan(
    req: ChallanGenerateRequest,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    student = session.get(Student, req.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    existing = session.exec(
        select(Invoice).where(Invoice.student_id == student.id, Invoice.month == req.month)
    ).first()
    if existing:
        raise _duplicate_challan_error(req.month)

    invoice = Invoice(
        student_id=student.id,
        amount=round(req.amount, 2),
        month=req.month,
        due_date=req.due_date.strftime(DUE_DATE_DISPLAY_FORMAT),
        challan_number=_unique_challan_number(session),
        status="pending",
    )
    session.add(invoice)
    try:
        session.commit()
    except IntegrityError:
        # Lost a race with an identical request; the database index caught it.
        session.rollback()
        raise _duplicate_challan_error(req.month)
    session.refresh(invoice)

    return {
        "message": "Challan generated successfully",
        "invoice_id": invoice.id,
        "challan_number": invoice.challan_number,
        "amount": invoice.amount,
        "status": invoice.status,
    }


def _lock_invoice(session: Session, invoice_id: int) -> Optional[Invoice]:
    """Takes the write lock before reading, so two simultaneous payments cannot both see the same balance."""
    session.exec(update(Invoice).where(Invoice.id == invoice_id).values(status=Invoice.status))
    return session.get(Invoice, invoice_id, populate_existing=True)


@router.post("/{id}/pay", status_code=http_status.HTTP_201_CREATED)
def pay_invoice(
    id: int,
    payment_req: PaymentRequest,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    invoice = _lock_invoice(session, id)
    if not invoice:
        session.rollback()
        raise HTTPException(status_code=404, detail="Invoice not found")

    paid_so_far = paid_by_invoice(session, [invoice.id]).get(invoice.id, 0.0)
    balance = outstanding_balance(invoice.amount, paid_so_far)

    if balance == 0:
        session.rollback()
        raise HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail="This invoice is already fully paid.")

    amount = balance if payment_req.amount_paid is None else round(payment_req.amount_paid, 2)
    if amount > balance:
        session.rollback()
        raise HTTPException(
            status_code=422,
            detail=f"The amount is more than the Rs. {balance:,.2f} still owed on this invoice.",
        )

    paid_total = round(paid_so_far + amount, 2)
    invoice.status = payment_status(invoice.amount, paid_total)
    payment = Payment(invoice_id=invoice.id, amount_paid=amount, payment_mode=payment_req.payment_mode)
    session.add(invoice)
    session.add(payment)
    session.commit()

    return {
        "message": "Payment recorded",
        "invoice_id": invoice.id,
        "status": invoice.status,
        "amount_paid": amount,
        "total_paid": paid_total,
        "balance": outstanding_balance(invoice.amount, paid_total),
        "payment_mode": payment.payment_mode,
    }


@router.get("/{id}/payments")
def get_invoice_payments(
    id: int,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    if not session.get(Invoice, id):
        raise HTTPException(status_code=404, detail="Invoice not found")

    payments = session.exec(select(Payment).where(Payment.invoice_id == id).order_by(Payment.id)).all()
    return [
        {
            "id": payment.id,
            "amount_paid": payment.amount_paid,
            "payment_mode": payment.payment_mode,
            "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
        }
        for payment in payments
    ]


@router.get("/{id}/pdf")
def download_challan_pdf(
    id: int,
    session: Session = Depends(get_session),
    _user=Depends(get_current_user),
):
    invoice = session.get(Invoice, id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    student = session.get(Student, invoice.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Associated student not found")

    student_data = {
        "name": student.name,
        "roll_number": student.roll_number,
        "grade": student.grade,
        "section": student.section,
        "guardian_name": student.guardian_name,
    }
    tuition_amount = min(invoice.amount, float(TUITION_FEE_MONTHLY))
    paid = paid_by_invoice(session, [invoice.id]).get(invoice.id, 0.0)
    invoice_data = {
        "challan_number": invoice.challan_number,
        "amount": invoice.amount,
        "month": invoice.month,
        "due_date": invoice.due_date,
        "status": invoice.status,
        "tuition_amount": tuition_amount,
        "exam_amount": invoice.amount - tuition_amount,
        "amount_paid": paid,
        "balance": outstanding_balance(invoice.amount, paid),
    }

    pdf_content = generate_fee_challan_pdf(invoice_data, student_data)
    filename = f"Challan_{invoice.challan_number}_{student.roll_number}.pdf"

    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"},
    )
