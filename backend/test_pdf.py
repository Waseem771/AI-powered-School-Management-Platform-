"""PDFs must generate for any stored text, print Urdu with a real font, and be sized for Pakistani printers."""
import itertools
import re

import pytest
from fastapi.testclient import TestClient
from reportlab import rl_config
from sqlmodel import Session

from database import engine
from main import app
from models.fee import Invoice
from models.result import Result
from models.student import Student
from services import pdf_text
from services.pdf_service import generate_fee_challan_pdf, generate_report_card_pdf, pdf_content_disposition

_ids = itertools.count(1)
URDU_NAME = "محمد علی"
A4_MEDIA_BOX = b"/MediaBox [ 0 0 595.2756 841.8898 ]"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def headers(client, admin_password):
    response = client.post("/auth/login", json={"username": "admin", "password": admin_password})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture()
def uncompressed(monkeypatch):
    """Without compression, the PDF's structure can be searched as bytes."""
    monkeypatch.setattr(rl_config, "pageCompression", 0)


def _stored_student(name="Hina Soomro", guardian="Akbar Soomro", roll=None):
    """Written straight to the database: older records never passed today's validation."""
    number = next(_ids)
    with Session(engine) as session:
        student = Student(
            name=name,
            roll_number=roll or f"PDF-{number}",
            grade="Grade 8",
            section="A",
            guardian_name=guardian,
            phone="0301-2345678",
        )
        session.add(student)
        session.commit()
        session.add(Result(student_id=student.id, subject="English", marks_obtained=70))
        invoice = Invoice(
            student_id=student.id,
            amount=4000,
            month="January 2026",
            due_date="10-Jan-2026",
            challan_number=f"CHN-P{number}",
            status="pending",
        )
        session.add(invoice)
        session.commit()
        return student.id, invoice.id


def _both_pdfs(client, headers, student_id, invoice_id):
    return (
        client.get(f"/fees/{invoice_id}/pdf", headers=headers),
        client.get(f"/results/{student_id}/report-card/pdf", headers=headers),
    )


def _invoice(**changes):
    return {
        "challan_number": "CHN-1",
        "amount": 4000,
        "month": "January 2026",
        "due_date": "10-Jan-2026",
        "status": "pending",
        "tuition_amount": 3500,
        "exam_amount": 500,
        "amount_paid": 0,
        "balance": 4000,
        **changes,
    }


def _student(**changes):
    return {
        "name": "Hina Soomro",
        "roll_number": "1",
        "grade": "Grade 8",
        "section": "A",
        "guardian_name": "Akbar Soomro",
        "phone": "0301-2345678",
        "dob": "Not recorded",
        **changes,
    }


def _report_card(student=None, reasons=()):
    marks = {"subject": "English", "marks_obtained": 70, "total_marks": 100, "grade": "B"}
    return generate_report_card_pdf(
        student or _student(),
        [marks] * 6,
        {"total_obtained": 420, "total_max": 600, "percentage": 70.0, "grade": "B"},
        {"exam_type": "Final Term", "session": "2025-2026"},
        {"status": "not_promoted", "label": "Not promoted", "reasons": list(reasons), "retake_eligible": True},
    )


def _page_count(pdf):
    return len(re.findall(rb"/Type /Page\b(?!s)", pdf))


# ── Text that used to crash the PDF ──────────────────────────────────────────


@pytest.mark.parametrize(
    "name",
    ["Ali <Khan>", "A & B", "<b>bold", "</para>", "<font color='red'>x", "Ali &bogus; Khan", 'Say "hello"'],
)
def test_awkward_stored_names_produce_both_pdfs(client, headers, name):
    student_id, invoice_id = _stored_student(name=name, guardian=name)

    challan, report_card = _both_pdfs(client, headers, student_id, invoice_id)

    assert challan.status_code == 200
    assert challan.content.startswith(b"%PDF")
    assert report_card.status_code == 200
    assert report_card.content.startswith(b"%PDF")


def test_markup_in_a_name_prints_as_text_and_is_not_obeyed(uncompressed):
    pdf = generate_fee_challan_pdf(_invoice(), _student(name="<font color='red'>Ali</font>"))

    assert b"font color" in pdf


def test_awkward_text_in_every_other_stored_field_is_safe():
    awkward = "<&>"
    assert generate_fee_challan_pdf(
        _invoice(month=awkward, due_date=awkward, challan_number=awkward, status=awkward),
        _student(roll_number=awkward, grade=awkward, section=awkward),
    ).startswith(b"%PDF")
    marks = {"subject": awkward, "marks_obtained": 1, "total_marks": 2, "grade": awkward}
    assert generate_report_card_pdf(
        _student(roll_number=awkward, grade=awkward, section=awkward, phone=awkward, dob=awkward),
        [marks],
        {"total_obtained": 1, "total_max": 2, "percentage": 50.0, "grade": awkward},
        {"exam_type": awkward, "session": awkward},
        {"status": "no_marks", "label": awkward, "reasons": []},
    ).startswith(b"%PDF")


# ── Urdu ─────────────────────────────────────────────────────────────────────


def test_shaping_library_loads():
    assert pdf_text.urdu_supported()


@pytest.mark.parametrize(
    "name, guardian",
    [(URDU_NAME, "اکبر علی"), ("Ali محمد Khan", "Akbar Soomro"), ("Hina Soomro", "اکبر علی")],
)
def test_urdu_names_work_through_the_real_api(client, headers, name, guardian):
    response = client.post(
        "/students",
        headers=headers,
        json={
            "name": name,
            "roll_number": f"URDU-{next(_ids)}",
            "grade": "Grade 8",
            "section": "A",
            "guardian_name": guardian,
            "phone": "0301-2345678",
        },
    )
    assert response.status_code == 201, response.text
    student_id = response.json()["id"]
    assert client.post(
        "/results",
        headers=headers,
        json={"student_id": student_id, "subject": "English", "marks_obtained": 70},
    ).status_code == 200
    challan_response = client.post(
        "/fees/generate",
        headers=headers,
        json={"student_id": student_id, "amount": 4000, "month": "January 2031", "due_date": "2031-01-10"},
    )
    assert challan_response.status_code == 201, challan_response.text

    challan, report_card = _both_pdfs(client, headers, student_id, challan_response.json()["invoice_id"])

    assert challan.status_code == 200
    assert report_card.status_code == 200


def test_urdu_font_is_embedded_only_when_needed(uncompressed):
    assert b"NotoNastaliqUrdu" in generate_fee_challan_pdf(_invoice(), _student(name=URDU_NAME))
    assert b"NotoNastaliqUrdu" in _report_card(_student(guardian_name=URDU_NAME))
    assert b"NotoNastaliqUrdu" not in generate_fee_challan_pdf(_invoice(), _student())


URDU_WORDS = [
    "محمد", "علی", "عائشہ", "بی", "ٹیپو", "سلطان", "ڈاکٹر", "عبدالرحمٰن", "چوہدری", "گُل", "زمان", "خان", "فاطمہ",
    "ژالہ", "ظہیر", "ضیاء", "شازیہ", "صدف", "ثناء", "ذیشان", "غلام", "قاسم", "کلثوم", "مریم", "نور", "وقار", "یاسر",
    "ہارون", "ؤ", "ئ", "آمنہ", "اللہ", "حسین", "رضیہ", "سیّد", "طاہرہ", "ڑ", "ں", "ے",
]


def test_every_urdu_word_can_start_a_name_or_a_wrapped_line():
    """ReportLab crashed on some letter combinations, which depended on the exact name."""
    for first, second in itertools.product(URDU_WORDS, repeat=2):
        name = f"{first} {second}"
        assert generate_fee_challan_pdf(_invoice(), _student(name=name)).startswith(b"%PDF"), name


def test_a_name_at_the_length_limit_wraps_without_crashing():
    name = " ".join(itertools.islice(itertools.cycle(URDU_WORDS), 25))[:100].strip()

    assert _report_card(_student(name=name, guardian_name=name)).startswith(b"%PDF")


def test_an_urdu_school_name_prints_in_the_heading(monkeypatch, uncompressed):
    monkeypatch.setattr("services.pdf_service.SCHOOL_NAME", "النور اکیڈمی Khairpur")

    assert b"NotoNastaliqUrdu" in generate_fee_challan_pdf(_invoice(), _student())
    assert b"NotoNastaliqUrdu" in _report_card()


def test_urdu_markup_keeps_latin_letters_out_of_the_urdu_font():
    """That font has no Latin letters, so they would print as empty boxes."""
    markup = pdf_text.urdu_markup("Ali محمد علی Khan")

    assert markup == (
        f'<font name="{pdf_text.LATIN_FONT}">Ali </font>محمد علی<font name="{pdf_text.LATIN_FONT}"> Khan</font>'
    )


def test_urdu_markup_escapes_the_latin_parts():
    assert "&lt;b&gt;" in pdf_text.urdu_markup("<b> محمد")


def test_has_urdu_recognises_urdu_only_letters():
    assert pdf_text.has_urdu("ٹیپو")
    assert pdf_text.has_urdu("Ali محمد")
    assert not pdf_text.has_urdu("Ali Khan")
    assert not pdf_text.has_urdu("")


def test_without_the_library_urdu_is_replaced_by_a_clear_note_never_garbled(monkeypatch, uncompressed):
    monkeypatch.setattr(pdf_text, "urdu_supported", lambda: False)

    assert pdf_text.printable("Ali محمد علی") == f"Ali {pdf_text.URDU_UNAVAILABLE_NOTE}"
    pdf = generate_fee_challan_pdf(_invoice(), _student(name=URDU_NAME))
    assert b"NotoNastaliqUrdu" not in pdf
    assert pdf.startswith(b"%PDF")


# ── Paper and layout ─────────────────────────────────────────────────────────


def test_both_documents_are_a4(uncompressed):
    assert A4_MEDIA_BOX in generate_fee_challan_pdf(_invoice(), _student())
    assert A4_MEDIA_BOX in _report_card()


def test_both_documents_fit_one_page_in_the_fullest_case(uncompressed):
    long_name = "محمد عبدالرحمٰن چوہدری " * 4
    challan = generate_fee_challan_pdf(
        _invoice(amount_paid=1000, balance=3000, status="partial"),
        _student(name=long_name.strip(), roll_number="A" * 20),
    )
    report_card = _report_card(
        _student(name=long_name.strip(), guardian_name=long_name.strip()),
        reasons=["Passed 3 of 6 subjects; at least 5 of 6 are needed.", "Aggregate is 43.6%; at least 50% is needed."],
    )

    assert _page_count(challan) == 1
    assert _page_count(report_card) == 1


def test_challan_shows_the_school_address(uncompressed, monkeypatch):
    monkeypatch.setattr("services.pdf_service.SCHOOL_ADDRESS", "Test Road Khairpur")

    assert b"Test Road Khairpur" in generate_fee_challan_pdf(_invoice(), _student())


def test_challan_names_other_charges_only_when_there_are_some(uncompressed):
    with_other = generate_fee_challan_pdf(_invoice(), _student())
    tuition_only = generate_fee_challan_pdf(_invoice(amount=3500, exam_amount=0, balance=3500), _student())

    assert b"Other Charges" in with_other
    assert b"Examination" not in with_other
    assert b"Other Charges" not in tuition_only


def test_challan_says_the_amount_excludes_late_charges(uncompressed):
    assert b"late" in generate_fee_challan_pdf(_invoice(), _student()).lower()


# ── Download names ───────────────────────────────────────────────────────────


@pytest.mark.parametrize("roll", ["045", "A/12", "R-7"])
def test_download_names_are_plain_and_hold_no_student_name(client, headers, roll):
    student_id, invoice_id = _stored_student(name=URDU_NAME, roll=f"{roll}-{next(_ids)}")

    challan, report_card = _both_pdfs(client, headers, student_id, invoice_id)

    for response in (challan, report_card):
        disposition = response.headers["content-disposition"]
        assert re.fullmatch(r'inline; filename="[A-Za-z0-9_-]+\.pdf"', disposition), disposition


@pytest.mark.parametrize("hostile", ['a"b', "a\r\nX-Evil: 1", "../../etc", "محمد", ""])
def test_download_names_cannot_carry_header_tricks(hostile):
    value = pdf_content_disposition("Challan", hostile)

    assert re.fullmatch(r'inline; filename="[A-Za-z0-9_-]+\.pdf"', value)


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-q"]))
