"""A receipt for one payment, showing the invoice as it stood right after that payment."""
import io
from typing import Any, Dict, Optional
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlmodel import Session, func, select

from config import SCHOOL_ADDRESS, SCHOOL_NAME, SCHOOL_PHONE
from models.fee import Invoice, Payment
from models.student import Student
from services.fee_ledger import outstanding_balance, school_time
from services.pdf_service import _field, _heading

RECEIPT_FORMAT = "RCP-{:06d}"
_RECEIPT_DATE_FORMAT = "%d-%b-%Y, %I:%M %p"
_NAVY = colors.HexColor("#12274B")
_BORDER = colors.HexColor("#CBD5E1")


def receipt_number(payment_id: int) -> str:
    return RECEIPT_FORMAT.format(payment_id)


def receipt_details(session: Session, payment_id: int) -> Optional[Dict[str, Any]]:
    """Everything printed on a receipt, or None if the payment or its records do not exist."""
    payment = session.get(Payment, payment_id)
    invoice = session.get(Invoice, payment.invoice_id) if payment else None
    student = session.get(Student, invoice.student_id) if invoice else None
    if not student:
        return None

    paid_to_date = session.exec(
        select(func.sum(Payment.amount_paid)).where(Payment.invoice_id == invoice.id, Payment.id <= payment.id)
    ).one()
    paid_to_date = round(paid_to_date or 0.0, 2)
    return {
        "receipt_number": receipt_number(payment.id),
        "received_at": school_time(payment.paid_at).strftime(_RECEIPT_DATE_FORMAT),
        "payment_mode": payment.payment_mode,
        "amount_received": payment.amount_paid,
        "invoice_amount": invoice.amount,
        "paid_to_date": paid_to_date,
        "balance_after": outstanding_balance(invoice.amount, paid_to_date),
        "challan_number": invoice.challan_number,
        "month": invoice.month,
        "student_name": student.name,
        "roll_number": student.roll_number,
        "class_name": f"{student.grade}-{student.section}",
        "guardian_name": student.guardian_name,
    }


def _money(amount: float) -> str:
    return f"Rs. {amount:,.2f}".replace(".00", "")


def generate_receipt_pdf(details: Dict[str, Any]) -> bytes:
    """One A4 page. All stored text goes through `_field`, so any name prints safely."""
    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=48, rightMargin=48, topMargin=48, bottomMargin=48)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("ReceiptSchool", parent=styles["Heading2"], fontSize=16, leading=20, alignment=1, textColor=_NAVY)
    small = ParagraphStyle("ReceiptSmall", parent=styles["Normal"], fontSize=9, leading=12, alignment=1, textColor=colors.HexColor("#475569"))
    heading = ParagraphStyle("ReceiptHeading", parent=styles["Normal"], fontSize=12, leading=16, alignment=1, textColor=_NAVY)
    text = ParagraphStyle("ReceiptText", parent=styles["Normal"], fontSize=10, leading=14)
    total = ParagraphStyle("ReceiptTotal", parent=styles["Normal"], fontSize=12, leading=16)

    details_rows = [
        [_field("Receipt No", details["receipt_number"], text), _field("Date", details["received_at"], text)],
        [_field("Student", details["student_name"], text), _field("Roll No", details["roll_number"], text)],
        [_field("Class", details["class_name"], text), _field("Guardian", details["guardian_name"], text)],
        [_field("Challan No", details["challan_number"], text), _field("Fee month", details["month"], text)],
    ]
    money_rows = [
        [_field("Amount received", _money(details["amount_received"]), total), _field("Paid by", details["payment_mode"].capitalize(), text)],
        [_field("Invoice total", _money(details["invoice_amount"]), text), _field("Paid to date", _money(details["paid_to_date"]), text)],
        [_field("Balance after this payment", _money(details["balance_after"]), total), ""],
    ]
    grid = TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, _BORDER),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, _BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ])
    details_table = Table(details_rows, colWidths=[250, 249])
    details_table.setStyle(grid)
    money_table = Table(money_rows, colWidths=[250, 249])
    money_table.setStyle(grid)
    money_table.setStyle(TableStyle([("SPAN", (0, -1), (-1, -1))]))

    document.build([
        _heading(SCHOOL_NAME.upper(), title),
        Paragraph(f"{escape(SCHOOL_ADDRESS)} &bull; Ph: {escape(SCHOOL_PHONE)}", small),
        Spacer(1, 12),
        Paragraph("<b>FEE PAYMENT RECEIPT</b>", heading),
        Spacer(1, 12),
        details_table,
        Spacer(1, 12),
        money_table,
        Spacer(1, 48),
        Paragraph("Received by: ______________________________", text),
        Spacer(1, 8),
        Paragraph("Please keep this receipt as proof of payment.", small),
    ])
    return buffer.getvalue()
