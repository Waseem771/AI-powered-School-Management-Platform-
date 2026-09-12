import io
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from config import SCHOOL_NAME, SCHOOL_TAGLINE, SCHOOL_ADDRESS, SCHOOL_PHONE

def generate_fee_challan_pdf(invoice_data: dict, student_data: dict) -> bytes:
    """
    Generates a professional 2-part Fee Challan PDF (Bank Copy & Student Copy)
    matching the layout specified in Section 9 of the implementation plan.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
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

    tuition = invoice_data.get("tuition_amount", 3500)
    exam = invoice_data.get("exam_amount", 500)
    total = invoice_data.get("amount", tuition + exam)
    month = invoice_data.get("month", "October 2025")
    due_date = invoice_data.get("due_date", "10-Oct-2025")
    challan_no = invoice_data.get("challan_number", "CHN-1045")
    status = invoice_data.get("status", "Pending").upper()

    def build_copy_block(copy_title: str):
        block = []
        # Header
        block.append(Paragraph(f"<b>{SCHOOL_NAME.upper()}</b>", title_style))
        block.append(Paragraph(f"{SCHOOL_TAGLINE} &bull; Ph: {SCHOOL_PHONE}", sub_title_style))
        block.append(Spacer(1, 4))
        block.append(Paragraph(f"<b>[ {copy_title.upper()} ]</b> &nbsp;&nbsp;|&nbsp;&nbsp; Status: <b>{status}</b>", copy_badge_style))
        block.append(Spacer(1, 6))

        # Student & Challan Meta Table
        student_meta = [
            [
                Paragraph(f"<b>Student:</b> {student_data.get('name', 'N/A')}", normal_style),
                Paragraph(f"<b>Roll No:</b> {student_data.get('roll_number', 'N/A')}", normal_style)
            ],
            [
                Paragraph(f"<b>Class:</b> {student_data.get('grade', 'Grade 8')}-{student_data.get('section', 'A')}", normal_style),
                Paragraph(f"<b>Month:</b> {month}", normal_style)
            ],
            [
                Paragraph(f"<b>Challan No:</b> {challan_no}", normal_style),
                Paragraph(f"<b>Due Date:</b> <font color='red'><b>{due_date}</b></font>", normal_style)
            ]
        ]
        meta_table = Table(student_meta, colWidths=[260, 260])
        meta_table.setStyle(TableStyle([
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
            [Paragraph("Examination & Lab Charges", normal_style), Paragraph(f"Rs. {exam:,.0f}", normal_style)],
            [Paragraph("<b>TOTAL PAYABLE AMOUNT</b>", total_style), Paragraph(f"<b>Rs. {total:,.0f}</b>", total_style)],
        ]
        fee_table = Table(fee_items, colWidths=[360, 160])
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
        block.append(Spacer(1, 8))

        # Signatures line
        sig_data = [
            [Paragraph("Authorized Bank Officer / Cashier", normal_style), Paragraph("Parent / Guardian Signature", normal_style)]
        ]
        sig_table = Table(sig_data, colWidths=[260, 260])
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

def generate_report_card_pdf(student_data: dict, results_list: list, summary_stats: dict) -> bytes:
    """
    Generates an official Student Report Card PDF matching Section 9.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
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
    elements.append(Paragraph(f"<b>{SCHOOL_NAME.upper()}</b>", title_style))
    elements.append(Paragraph(f"{SCHOOL_TAGLINE} &bull; {SCHOOL_ADDRESS}", sub_style))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph("<b>OFFICIAL STUDENT REPORT CARD &bull; ACADEMIC SESSION 2025-2026</b>", badge_style))
    elements.append(Spacer(1, 10))

    # Student Info Table
    info_data = [
        [
            Paragraph(f"<b>Student Name:</b> {student_data.get('name', 'N/A')}", normal_style),
            Paragraph(f"<b>Roll Number:</b> {student_data.get('roll_number', 'N/A')}", normal_style)
        ],
        [
            Paragraph(f"<b>Grade & Section:</b> {student_data.get('grade', 'N/A')}-{student_data.get('section', 'A')}", normal_style),
            Paragraph(f"<b>Guardian:</b> {student_data.get('guardian_name', 'N/A')}", normal_style)
        ],
        [
            Paragraph(f"<b>Contact:</b> {student_data.get('phone', 'N/A')}", normal_style),
            Paragraph(f"<b>Date of Birth:</b> {student_data.get('dob', 'N/A')}", normal_style)
        ]
    ]
    info_table = Table(info_data, colWidths=[266, 266])
    info_table.setStyle(TableStyle([
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
    headers = [
        Paragraph("<b>Subject</b>", bold_style),
        Paragraph("<b>Marks Obtained</b>", center_bold),
        Paragraph("<b>Total Marks</b>", center_bold),
        Paragraph("<b>Percentage</b>", center_bold),
        Paragraph("<b>Grade</b>", center_bold)
    ]
    table_rows = [headers]

    for item in results_list:
        obtained = float(item.get("marks_obtained", 0))
        total = float(item.get("total_marks", 100))
        pct = (obtained / total * 100) if total > 0 else 0
        grade = item.get("grade", "F")
        grade_color = "#DC2626" if grade == "F" else ("#16A34A" if grade in ["A+", "A"] else "#2563EB")

        row = [
            Paragraph(item.get("subject", ""), normal_style),
            Paragraph(f"{obtained:.1f}", center_text),
            Paragraph(f"{total:.0f}", center_text),
            Paragraph(f"{pct:.1f}%", center_text),
            Paragraph(f"<font color='{grade_color}'><b>{grade}</b></font>", center_bold),
        ]
        table_rows.append(row)

    results_table = Table(table_rows, colWidths=[182, 90, 85, 90, 85])
    results_table.setStyle(TableStyle([
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
    # Change header font color to white in paragraph styles
    elements.append(results_table)
    elements.append(Spacer(1, 12))

    # Summary Box
    total_obtained = summary_stats.get("total_obtained", 0)
    total_max = summary_stats.get("total_max", 600)
    overall_pct = summary_stats.get("percentage", 0.0)
    overall_grade = summary_stats.get("grade", "N/A")

    summary_data = [
        [
            Paragraph(f"<b>Aggregate Marks:</b> {total_obtained:.1f} / {total_max:.0f}", normal_style),
            Paragraph(f"<b>Overall Percentage:</b> {overall_pct:.1f}%", normal_style),
            Paragraph(f"<b>Final Grade:</b> <font size='12' color='#1E3A8A'><b>{overall_grade}</b></font>", normal_style)
        ]
    ]
    summary_table = Table(summary_data, colWidths=[176, 176, 180])
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
            Paragraph("<b>Class Teacher's Remarks:</b><br/>Consistent effort noted. Keep up the dedication towards academic excellence.", normal_style),
            Paragraph("<b>Promotion Status:</b><br/><font color='green'><b>PROMOTED TO NEXT HIGHER CLASS</b></font>" if overall_grade != "F" else "<font color='red'><b>ACADEMIC PROBATION / RETAKE REQUIRED</b></font>", normal_style)
        ]
    ]
    remarks_table = Table(remarks_data, colWidths=[310, 222])
    remarks_table.setStyle(TableStyle([
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
    sig_table = Table(sig_data, colWidths=[176, 176, 180])
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
