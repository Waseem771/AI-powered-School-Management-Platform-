"""The one place fee money is calculated. Payment rows are the source of truth for money received."""
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional

from sqlmodel import Session, col, func, select

from models.fee import Invoice, Payment

STATUS_PENDING = "pending"
STATUS_PARTIAL = "partial"
STATUS_PAID = "paid"

DUE_DATE_DISPLAY_FORMAT = "%d-%b-%Y"
_READABLE_DUE_DATE_FORMATS = (DUE_DATE_DISPLAY_FORMAT, "%Y-%m-%d")
_PAKISTAN_TIME = timezone(timedelta(hours=5))


def school_today() -> date:
    """Overdue is judged by the date at the school, not the server's."""
    return datetime.now(_PAKISTAN_TIME).date()


def outstanding_balance(amount: float, paid: float) -> float:
    """Never negative, even if older data recorded more than was invoiced."""
    return max(round(amount - paid, 2), 0.0)


def payment_status(amount: float, paid: float) -> str:
    if outstanding_balance(amount, paid) == 0:
        return STATUS_PAID
    return STATUS_PARTIAL if paid > 0 else STATUS_PENDING


def parse_due_date(text: str) -> Optional[date]:
    """Older invoices hold free text, so an unreadable date is None rather than an error."""
    for date_format in _READABLE_DUE_DATE_FORMATS:
        try:
            return datetime.strptime((text or "").strip(), date_format).date()
        except ValueError:
            continue
    return None


def is_overdue(status: str, due_date_text: str, today: date) -> bool:
    due_on = parse_due_date(due_date_text)
    return status != STATUS_PAID and due_on is not None and due_on < today


def paid_by_invoice(session: Session, invoice_ids: Optional[Iterable[int]] = None) -> Dict[int, float]:
    query = select(Payment.invoice_id, func.sum(Payment.amount_paid)).group_by(Payment.invoice_id)
    if invoice_ids is not None:
        query = query.where(col(Payment.invoice_id).in_(list(invoice_ids)))
    return {invoice_id: round(total, 2) for invoice_id, total in session.exec(query).all()}


def invoice_money(invoice: Invoice, paid: float, today: date) -> dict:
    """The money fields every screen shows for one invoice."""
    due_on = parse_due_date(invoice.due_date)
    return {
        "amount_paid": paid,
        "balance": outstanding_balance(invoice.amount, paid),
        "due_on": due_on.isoformat() if due_on else None,
        "is_overdue": is_overdue(invoice.status, invoice.due_date, today),
    }


def _month_order(month: str) -> tuple:
    try:
        return (0, datetime.strptime(month.strip(), "%B %Y"))
    except ValueError:
        return (1, month)


def monthly_totals(session: Session, month: Optional[str] = None) -> List[dict]:
    """Money for each billing month, oldest first. "October" alone finds October of every year.

    A payment counts towards the month of its invoice, not the day it was received.
    """
    wanted = (month or "").strip().casefold()
    invoices = [
        invoice for invoice in session.exec(select(Invoice)).all()
        if not wanted or invoice.month.casefold() == wanted or invoice.month.casefold().split(" ")[0] == wanted
    ]
    paid = paid_by_invoice(session, [invoice.id for invoice in invoices])

    by_month: Dict[str, List[Invoice]] = {}
    for invoice in invoices:
        by_month.setdefault(invoice.month, []).append(invoice)

    rows = []
    for name in sorted(by_month, key=_month_order):
        group = by_month[name]
        invoiced = round(sum(invoice.amount for invoice in group), 2)
        outstanding = round(sum(outstanding_balance(invoice.amount, paid.get(invoice.id, 0.0)) for invoice in group), 2)
        rows.append({
            "month": name,
            "invoice_count": len(group),
            "invoiced": invoiced,
            "collected": round(sum(paid.get(invoice.id, 0.0) for invoice in group), 2),
            "outstanding": outstanding,
            "collection_rate": round((invoiced - outstanding) / invoiced * 100, 1) if invoiced > 0 else 0.0,
        })
    return rows


def school_totals(session: Session, today: Optional[date] = None) -> dict:
    """Whole-school totals, shared by the dashboard, Fees page, and chatbot so they cannot disagree."""
    today = today or school_today()
    invoices = session.exec(select(Invoice)).all()
    paid = paid_by_invoice(session)

    invoiced = round(sum(invoice.amount for invoice in invoices), 2)
    balances = [(invoice, outstanding_balance(invoice.amount, paid.get(invoice.id, 0.0))) for invoice in invoices]
    outstanding = round(sum(balance for _, balance in balances), 2)
    overdue = round(
        sum(balance for invoice, balance in balances if is_overdue(invoice.status, invoice.due_date, today)), 2
    )

    return {
        "invoice_count": len(invoices),
        "invoiced": invoiced,
        "collected": round(sum(paid.values()), 2),
        "outstanding": outstanding,
        "overdue": overdue,
        "collection_rate": round((invoiced - outstanding) / invoiced * 100, 1) if invoiced > 0 else 0.0,
    }
