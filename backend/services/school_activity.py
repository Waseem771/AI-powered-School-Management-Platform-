"""Recent activity for the dashboard, from the dates on real records. Holds no contact details."""
from typing import Any, Dict, List

from sqlmodel import Session, col, select

from models.fee import Invoice, Payment
from models.student import Student
from services.fee_ledger import utc_iso


def _student_fields(student: Student) -> Dict[str, Any]:
    return {
        "student_id": student.id,
        "student_name": student.name,
        "roll_number": student.roll_number,
        "class_name": f"{student.grade}-{student.section}",
    }


def recent_activity(session: Session, limit: int) -> List[Dict[str, Any]]:
    """Payments, challans, and enrolments together, newest first."""
    payments = session.exec(
        select(Payment, Invoice, Student)
        .join(Invoice, Payment.invoice_id == Invoice.id)
        .join(Student, Invoice.student_id == Student.id)
        .order_by(col(Payment.paid_at).desc())
        .limit(limit)
    ).all()
    challans = session.exec(
        select(Invoice, Student)
        .join(Student, Invoice.student_id == Student.id)
        .order_by(col(Invoice.created_at).desc())
        .limit(limit)
    ).all()
    enrolments = session.exec(
        select(Student)
        .where(col(Student.archived_at).is_(None))
        .order_by(col(Student.created_at).desc())
        .limit(limit)
    ).all()

    items = [
        {
            "kind": "payment",
            "at": utc_iso(payment.paid_at),
            "payment_id": payment.id,
            "amount": payment.amount_paid,
            "month": invoice.month,
            "payment_mode": payment.payment_mode,
            **_student_fields(student),
        }
        for payment, invoice, student in payments
    ] + [
        {
            "kind": "challan",
            "at": utc_iso(invoice.created_at),
            "invoice_id": invoice.id,
            "amount": invoice.amount,
            "month": invoice.month,
            **_student_fields(student),
        }
        for invoice, student in challans
    ] + [
        {"kind": "enrolment", "at": utc_iso(student.created_at), **_student_fields(student)}
        for student in enrolments
    ]
    return sorted(items, key=lambda item: item["at"], reverse=True)[:limit]
