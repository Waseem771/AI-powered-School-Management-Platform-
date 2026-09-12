from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, select
from typing import List, Optional
from pydantic import BaseModel
import random
from database import get_session
from models.fee import Invoice, Payment
from models.student import Student
from services.pdf_service import generate_fee_challan_pdf
from routers.auth import get_current_user

router = APIRouter(prefix="/fees", tags=["Fees"])

class ChallanGenerateRequest(BaseModel):
    student_id: int
    amount: float = 4000.0
    month: str = "November 2025"
    due_date: str = "10-Nov-2025"

class PaymentRequest(BaseModel):
    amount_paid: Optional[float] = None
    payment_mode: str = "cash"  # cash, bank, online

@router.get("")
def get_invoices(
    status: Optional[str] = None,
    grade: Optional[str] = None,
    session: Session = Depends(get_session),
    _user = Depends(get_current_user)
):
    query = select(Invoice, Student).join(Student, Invoice.student_id == Student.id)
    if status:
        query = query.where(Invoice.status == status)
    if grade:
        query = query.where(Student.grade == grade)

    results = session.exec(query.order_by(Invoice.id.desc())).all()
    invoices = []
    for inv, stud in results:
        invoices.append({
            "id": inv.id,
            "student_id": stud.id,
            "student_name": stud.name,
            "roll_number": stud.roll_number,
            "grade": stud.grade,
            "section": stud.section,
            "amount": inv.amount,
            "month": inv.month,
            "due_date": inv.due_date,
            "challan_number": inv.challan_number,
            "status": inv.status,
            "created_at": inv.created_at.isoformat() if inv.created_at else None
        })
    return invoices

@router.post("/generate")
def generate_challan(
    req: ChallanGenerateRequest,
    session: Session = Depends(get_session),
    _user = Depends(get_current_user)
):
    student = session.get(Student, req.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    challan_num = f"CHN-{random.randint(1000, 9999)}"
    invoice = Invoice(
        student_id=student.id,
        amount=req.amount,
        month=req.month,
        due_date=req.due_date,
        challan_number=challan_num,
        status="pending"
    )
    session.add(invoice)
    session.commit()
    session.refresh(invoice)

    return {
        "message": "Challan generated successfully",
        "invoice_id": invoice.id,
        "challan_number": invoice.challan_number,
        "amount": invoice.amount,
        "status": invoice.status
    }

@router.post("/{id}/pay")
def pay_invoice(
    id: int,
    payment_req: PaymentRequest,
    session: Session = Depends(get_session),
    _user = Depends(get_current_user)
):
    invoice = session.get(Invoice, id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice.status = "paid"
    payment = Payment(
        invoice_id=invoice.id,
        amount_paid=payment_req.amount_paid or invoice.amount,
        payment_mode=payment_req.payment_mode
    )
    session.add(invoice)
    session.add(payment)
    session.commit()

    return {
        "message": "Invoice marked as paid",
        "invoice_id": invoice.id,
        "status": invoice.status,
        "payment_mode": payment.payment_mode
    }

@router.get("/{id}/pdf")
def download_challan_pdf(
    id: int,
    session: Session = Depends(get_session)
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
        "guardian_name": student.guardian_name
    }
    invoice_data = {
        "challan_number": invoice.challan_number,
        "amount": invoice.amount,
        "month": invoice.month,
        "due_date": invoice.due_date,
        "status": invoice.status,
        "tuition_amount": 3500.0,
        "exam_amount": max(0.0, invoice.amount - 3500.0)
    }

    pdf_content = generate_fee_challan_pdf(invoice_data, student_data)
    filename = f"Challan_{invoice.challan_number}_{student.roll_number}.pdf"

    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )
