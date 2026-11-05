import io
import re
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from config import SCHOOL_NAME, SCHOOL_TAGLINE, SCHOOL_ADDRESS, SCHOOL_PHONE
from services.pdf_text import (
    LATIN_FONT_BOLD,
    has_urdu,
    printable,
    urdu_markup,
    urdu_style,
)

LATE_CHARGES_NOTE = "This amount does not include any late-payment charges under the school fee policy."


def pdf_content_disposition(*name_parts: str) -> str:
    """A plain download name. It holds no student name, and nothing that could break the header."""
    name = "_".join(re.sub(r"[^A-Za-z0-9-]+", "-", part).strip("-") or "record" for part in name_parts)
    return f'inline; filename="{name}.pdf"'


def _field(label: str, value: object, style: ParagraphStyle) -> Paragraph:
    """A "Label: value" cell for any stored text, safe for markup characters and Urdu."""
    shown = printable(str(value))
    if has_urdu(shown):
        return Paragraph(f'<font name="{LATIN_FONT_BOLD}">{label}:</font> {urdu_markup(shown)}', urdu_style(style))
    return Paragraph(f"<b>{label}:</b> {escape(shown)}", style)


def _heading(text: str, style: ParagraphStyle) -> Paragraph:
    """A line of configured text, such as the school name, which may be in either script."""
    shown = printable(text)
    if has_urdu(shown):
        return Paragraph(urdu_markup(shown, LATIN_FONT_BOLD), urdu_style(style, bold=True))
    return Paragraph(f"<b>{escape(shown)}</b>", style)


def generate_fee_challan_pdf(invoice_data: dict, student_data: dict) -> bytes:
    """
    Generates a professional 2-part Fee Challan PDF (Bank Copy & Student Copy)
    matching the layout specified in Section 9 of the implementation plan.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'ChallanTitle',
        parent=styles['Heading2'],
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#1E3A8A"),
        alignment=1, # Center
        fontName="Helvetica-Bold"
    )
    sub_title_style = ParagraphStyle(
        'ChallanSubTitle',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#4B5563"),
        alignment=1,
        fontName="Helvetica"
    )
    copy_badge_style = ParagraphStyle(
        'CopyBadge',
        parent=styles['Normal'],
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#1E3A8A"),
        alignment=1,
        fontName="Helvetica-Bold"
    )
    normal_style = ParagraphStyle('ChallanText', parent=styles['Normal'], fontSize=9, leading=12)
    bold_style = ParagraphStyle('ChallanBold', parent=styles['Normal'], fontSize=9, leading=12, fontName="Helvetica-Bold")
    total_style = ParagraphStyle('ChallanTotal', parent=styles['Normal'], fontSize=11, leading=14, fontName="Helvetica-Bold", textColor=colors.HexColor("#1E3A8A"))

    elements = []

    tuition = invoice_data["tuition_amount"]
    other_charges = invoice_data["exam_amount"]
    total = invoice_data["amount"]
    month = invoice_data["month"]
    due_date = escape(str(invoice_data["due_date"]))
    challan_no = invoice_data["challan_number"]
    status = escape(str(invoice_data["status"]).upper())
    amount_paid = invoice_data.get("amount_paid", 0)
    balance = invoice_data.get("balance", total)

    def build_copy_block(copy_title: str):
        block = []
        # Header
        block.append(_heading(SCHOOL_NAME.upper(), title_style))
        block.append(Paragraph(f"{escape(SCHOOL_ADDRESS)} &bull; Ph: {escape(SCHOOL_PHONE)}", sub_title_style))
        block.append(Spacer(1, 4))
        block.append(Paragraph(f"<b>[ {copy_title.upper()} ]</b> &nbsp;&nbsp;|&nbsp;&nbsp; Status: <b>{status}</b>", copy_badge_style))
        block.append(Spacer(1, 6))

        # Student & Challan Meta Table
        student_meta = [
            [
                _field("Student", student_data["name"], normal_style),
                _field("Roll No", student_data["roll_number"], normal_style)
            ],
            [
                _field("Class", f"{student_data['grade']}-{student_data['section']}", normal_style),
                _field("Month", month, normal_style)
            ],
            [
                _field("Challan No", challan_no, normal_style),
                Paragraph(f"<b>Due Date:</b> <font color='red'><b>{due_date}</b></font>", normal_style)
            ]
        ]
        meta_table = Table(student_meta, colWidths=[260, 263])
        meta_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#CBD5E1")),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))
        block.append(meta_table)
        block.append(Spacer(1, 6))

        # Fee Details Table
        fee_items = [
            [Paragraph("<b>Fee Particulars</b>", bold_style), Paragraph("<b>Amount (PKR)</b>", bold_style)],
            [Paragraph("Monthly Tuition Fee", normal_style), Paragraph(f"Rs. {tuition:,.0f}", normal_style)],
        ]
        # An invoice stores one total, so anything above tuition cannot be named more exactly.
        if other_charges > 0:
            fee_items.append(
                [Paragraph("Other Charges", normal_style), Paragraph(f"Rs. {other_charges:,.0f}", normal_style)]
            )
        fee_items.append(
            [Paragraph("<b>TOTAL PAYABLE AMOUNT</b>", total_style), Paragraph(f"<b>Rs. {total:,.0f}</b>", total_style)]
        )
        if amount_paid > 0:
            fee_items.extend([
                [Paragraph("Paid to date", normal_style), Paragraph(f"Rs. {amount_paid:,.0f}", normal_style)],
                [Paragraph("<b>BALANCE DUE</b>", total_style), Paragraph(f"<b>Rs. {balance:,.0f}</b>", total_style)],
            ])
        fee_table = Table(fee_items, colWidths=[363, 160])
        fee_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#E0E7FF")),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#93C5FD")),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#EEF2F6")),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
            ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ]))
        block.append(fee_table)
        block.append(Spacer(1, 4))
        block.append(Paragraph(LATE_CHARGES_NOTE, sub_title_style))
        block.append(Spacer(1, 26))

        # Signatures line
        sig_data = [
            [Paragraph("Authorized Bank Officer / Cashier", normal_style), Paragraph("Parent / Guardian Signature", normal_style)]
        ]
        sig_table = Table(sig_data, colWidths=[260, 263])
        sig_table.setStyle(TableStyle([
            ('LINEABOVE', (0,0), (0,0), 0.75, colors.HexColor("#94A3B8")),
            ('LINEABOVE', (1,0), (1,0), 0.75, colors.HexColor("#94A3B8")),
            ('TOPPADDING', (0,0), (-1,-1), 2),
            ('ALIGN', (0,0), (0,0), 'LEFT'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
        ]))
        block.append(sig_table)
        return block

    # Add Bank Copy
    elements.extend(build_copy_block("Bank Copy"))
    elements.append(Spacer(1, 14))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#94A3B8"), spaceBefore=8, spaceAfter=14, dash=[4, 4]))
    # Add Student Copy
    elements.extend(build_copy_block("Student / Parent Copy"))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes

def _promotion_paragraph_text(promotion: dict) -> str:
    """States only what the recorded marks support. See services/academics.py."""
    status = promotion.get("status")
    if status == "promoted":
        return (
            "<font color='green'><b>PROMOTED TO NEXT HIGHER CLASS</b></font><br/>"
            "Based on Final Term marks under the school exam policy."
        )
    if status == "not_promoted":
        lines = ["<font color='red'><b>NOT PROMOTED</b></font>", *promotion.get("reasons", [])]
        if promotion.get("retake_eligible"):
            lines.append("Eligible for the retake examination.")
        return "<br/>".join(lines)
    return escape(promotion.get("label", ""))


def generate_report_card_pdf(
    student_data: dict, results_list: list, summary_stats: dict, exam: dict, promotion: dict
) -> bytes:
    """
    Generates an official Student Report Card PDF for one exam.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CardTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1E3A8A"),
        alignment=1,
        fontName="Helvetica-Bold"
    )
    sub_style = ParagraphStyle(
        'CardSub',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#4B5563"),
        alignment=1,
        fontName="Helvetica"
    )
    badge_style = ParagraphStyle(
        'CardBadge',
        parent=styles['Normal'],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1E40AF"),
        alignment=1,
        fontName="Helvetica-Bold"
    )
    normal_style = ParagraphStyle('CardText', parent=styles['Normal'], fontSize=10, leading=14)
    bold_style = ParagraphStyle('CardBold', parent=styles['Normal'], fontSize=10, leading=14, fontName="Helvetica-Bold")
    center_bold = ParagraphStyle('CenterBold', parent=styles['Normal'], fontSize=10, leading=14, fontName="Helvetica-Bold", alignment=1)
    center_text = ParagraphStyle('CenterText', parent=styles['Normal'], fontSize=10, leading=14, alignment=1)

    elements = []

    # Header
    elements.append(_heading(SCHOOL_NAME.upper(), title_style))
    elements.append(Paragraph(f"{escape(SCHOOL_TAGLINE)} &bull; {escape(SCHOOL_ADDRESS)}", sub_style))
    elements.append(Spacer(1, 6))
    session_text = f" &bull; ACADEMIC SESSION {escape(exam['session'])}" if exam.get("session") else ""
    elements.append(Paragraph(f"<b>OFFICIAL STUDENT REPORT CARD{session_text}</b>", badge_style))
    elements.append(Paragraph(f"{escape(exam['exam_type'])} Examination", sub_style))
    elements.append(Spacer(1, 10))

    # Student Info Table
    info_data = [
        [
            _field("Student Name", student_data.get("name", "N/A"), normal_style),
            _field("Roll Number", student_data.get("roll_number", "N/A"), normal_style)
        ],
        [
            _field("Grade &amp; Section", f"{student_data.get('grade', 'N/A')}-{student_data.get('section', 'N/A')}", normal_style),
            _field("Guardian", student_data.get("guardian_name", "N/A"), normal_style)
        ],
        [
            _field("Contact", student_data.get("phone", "N/A"), normal_style),
            _field("Date of Birth", student_data.get("dob", "N/A"), normal_style)
        ]
    ]
    info_table = Table(info_data, colWidths=[257, 258])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F1F5F9")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 12))

    # Subjects Table
    table_header = ParagraphStyle('TableHeader', parent=center_bold, textColor=colors.white)
    table_header_left = ParagraphStyle('TableHeaderLeft', parent=bold_style, textColor=colors.white)
    headers = [
        Paragraph("<b>Subject</b>", table_header_left),
        Paragraph("<b>Marks Obtained</b>", table_header),
        Paragraph("<b>Total Marks</b>", table_header),
        Paragraph("<b>Percentage</b>", table_header),
        Paragraph("<b>Grade</b>", table_header)
    ]
    table_rows = [headers]

    for item in results_list:
        obtained = float(item.get("marks_obtained", 0))
        total = float(item.get("total_marks", 100))
        pct = (obtained / total * 100) if total > 0 else 0
        grade = escape(item.get("grade", "N/A"))
        grade_color = "#DC2626" if grade == "F" else ("#16A34A" if grade in ["A+", "A"] else "#2563EB")

        row = [
            Paragraph(escape(item.get("subject", "")), normal_style),
            Paragraph(f"{obtained:.1f}", center_text),
            Paragraph(f"{total:.0f}", center_text),
            Paragraph(f"{pct:.1f}%", center_text),
            Paragraph(f"<font color='{grade_color}'><b>{grade}</b></font>", center_bold),
        ]
        table_rows.append(row)

    results_table = Table(table_rows, colWidths=[175, 90, 80, 90, 80])
    results_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1E3A8A")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#1E3A8A")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(results_table)
    elements.append(Spacer(1, 12))

    # Summary Box
    total_obtained = summary_stats.get("total_obtained", 0)
    total_max = summary_stats.get("total_max", 0)
    overall_pct = summary_stats.get("percentage", 0.0)
    overall_grade = escape(summary_stats.get("grade", "N/A"))

    summary_data = [
        [
            Paragraph(f"<b>Aggregate Marks:</b> {total_obtained:.1f} / {total_max:.0f}", normal_style),
            Paragraph(f"<b>Overall Percentage:</b> {overall_pct:.1f}%", normal_style),
            Paragraph(f"<b>Overall Grade:</b> <font size='12' color='#1E3A8A'><b>{overall_grade}</b></font>", normal_style)
        ]
    ]
    summary_table = Table(summary_data, colWidths=[170, 170, 175])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#E0E7FF")),
        ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor("#4F46E5")),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 16))

    # Remarks & Signatures
    remarks_data = [
        [
            # Left blank for the teacher to write by hand.
            Paragraph("<b>Class Teacher's Remarks:</b><br/><br/><br/>", normal_style),
            Paragraph(f"<b>Promotion Status:</b><br/>{_promotion_paragraph_text(promotion)}", normal_style)
        ]
    ]
    remarks_table = Table(remarks_data, colWidths=[295, 220])
    remarks_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(remarks_table)
    elements.append(Spacer(1, 28))

    # Signatures
    sig_data = [
        [
            Paragraph("Class Teacher", center_bold),
            Paragraph("Exam Controller", center_bold),
            Paragraph("Principal / Headmaster", center_bold)
        ]
    ]
    sig_table = Table(sig_data, colWidths=[170, 170, 175])
    sig_table.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (0,0), 1, colors.HexColor("#64748B")),
        ('LINEABOVE', (1,0), (1,0), 1, colors.HexColor("#64748B")),
        ('LINEABOVE', (2,0), (2,0), 1, colors.HexColor("#64748B")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
    ]))
    elements.append(sig_table)

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
