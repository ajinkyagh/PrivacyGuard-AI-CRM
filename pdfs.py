from io import BytesIO
from typing import Dict, Any
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

GST_RATE = 0.28  # 28%


def _money(v: float) -> str:
    return f"₹{v:,.2f}"


def _doc_header(story, title: str, lead: Dict[str, Any]) -> None:
    styles = getSampleStyleSheet()
    story.append(Paragraph("Luxury Automotive", styles['Title']))
    story.append(Paragraph(title, styles['h2']))
    story.append(Spacer(1, 6))
    meta = f"Client: {lead.get('name')} | Email: {lead.get('email')} | Phone: {lead.get('phone')}"
    story.append(Paragraph(meta, styles['Normal']))
    story.append(Spacer(1, 12))


def generate_quotation_pdf(lead: Dict[str, Any], vehicle_config: Dict[str, Any]) -> bytes:
    """Generate a quotation PDF with GST for the selected vehicle configuration."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=15*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()
    story = []

    _doc_header(story, "Quotation", lead)

    items = vehicle_config.get('items', []) or [
        {"name": lead.get('interest', 'Vehicle'), "price": vehicle_config.get('base_price', 100000000.0)},
    ]

    data = [["Item", "Price (excl. GST)"]]
    subtotal = 0.0
    for it in items:
        data.append([it.get('name'), _money(float(it.get('price', 0.0)))])
        subtotal += float(it.get('price', 0.0))

    gst = subtotal * GST_RATE
    total = subtotal + gst

    tbl = Table(data, colWidths=[120*mm, 50*mm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#101218')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.25, colors.gray),
        ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 8))

    totals = Table([
        ["Subtotal", _money(subtotal)],
        ["GST (28%)", _money(gst)],
        ["Total", _money(total)],
    ], colWidths=[120*mm, 50*mm])
    totals.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.25, colors.gray),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('FONTNAME', (0,2), (-1,2), 'Helvetica-Bold'),
    ]))
    story.append(totals)
    story.append(Spacer(1, 8))
    story.append(Paragraph("All amounts are in INR. Prices include GST as applicable.", styles['Italic']))

    doc.build(story)
    return buf.getvalue()


def generate_invoice_pdf(lead: Dict[str, Any], invoice: Dict[str, Any]) -> bytes:
    """Generate an invoice PDF with GST computation."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=15*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()
    story = []

    _doc_header(story, "Tax Invoice", lead)

    items = invoice.get('items', [])
    data = [["Description", "Qty", "Unit Price", "Amount"]]
    subtotal = 0.0
    for it in items:
        qty = float(it.get('qty', 1))
        unit = float(it.get('unit_price', 0.0))
        amt = qty * unit
        data.append([it.get('name', 'Item'), f"{qty:.0f}", _money(unit), _money(amt)])
        subtotal += amt

    gst = subtotal * GST_RATE
    total = subtotal + gst

    tbl = Table(data, colWidths=[90*mm, 20*mm, 30*mm, 30*mm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#101218')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 0.25, colors.gray),
        ('ALIGN', (1,1), (-1,-1), 'RIGHT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 8))

    totals = Table([
        ["Subtotal", _money(subtotal)],
        ["GST (28%)", _money(gst)],
        ["Total Payable", _money(total)],
    ], colWidths=[120*mm, 50*mm])
    totals.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.25, colors.gray),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('FONTNAME', (0,2), (-1,2), 'Helvetica-Bold'),
    ]))
    story.append(totals)
    story.append(Spacer(1, 8))
    story.append(Paragraph(f"Invoice Date: {datetime.now().strftime('%Y-%m-%d')}", styles['Normal']))

    doc.build(story)
    return buf.getvalue()


def generate_contract_pdf(lead: Dict[str, Any], contract: Dict[str, Any]) -> bytes:
    """Generate a detailed, professional purchase contract with border and formal clauses."""
    buf = BytesIO()

    def _draw_border(canv: canvas.Canvas, doc_obj):
        canv.saveState()
        # Outer border
        margin = 12 * mm
        canv.setStrokeColor(colors.HexColor('#22262e'))
        canv.setLineWidth(2)
        canv.rect(margin, margin, A4[0] - 2*margin, A4[1] - 2*margin)
        # Inner border
        inner = 16 * mm
        canv.setStrokeColor(colors.HexColor('#3a404a'))
        canv.setLineWidth(0.7)
        canv.rect(inner, inner, A4[0] - 2*inner, A4[1] - 2*inner)
        # Footer
        canv.setFont("Helvetica", 8)
        canv.setFillColor(colors.HexColor('#444b57'))
        canv.drawRightString(A4[0] - inner, 10 * mm, "Confidential - For the intended recipient only")
        canv.restoreState()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=22*mm,
        rightMargin=22*mm,
        topMargin=22*mm,
        bottomMargin=22*mm,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ContractTitle', parent=styles['Title'], fontName='Helvetica-Bold', spaceAfter=6))
    styles.add(ParagraphStyle(name='Section', parent=styles['Heading2'], spaceBefore=10, spaceAfter=6))
    styles.add(ParagraphStyle(name='Clause', parent=styles['BodyText'], leading=14, spaceAfter=4))
    styles.add(ParagraphStyle(name='Small', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#444b57')))

    story = []

    # Header
    story.append(Paragraph("Luxury Automotive", styles['ContractTitle']))
    story.append(Paragraph("Purchase Contract", styles['Section']))
    story.append(Spacer(1, 4))

    # Party details
    party_tbl = Table([
        ["Buyer Name", lead.get('name', '')],
        ["Buyer Email", lead.get('email', '')],
        ["Buyer Phone", lead.get('phone', '')],
        ["Vehicle", lead.get('interest', '')],
        ["Delivery Location", contract.get('delivery_location', 'TBD')],
        ["Payment Terms", contract.get('payment_terms', '100% on delivery')],
    ], colWidths=[50*mm, 110*mm])
    party_tbl.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.25, colors.gray),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#101218')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(party_tbl)
    story.append(Spacer(1, 8))

    # Customizations
    customizations = ", ".join(contract.get('customizations', [])) or 'None'
    story.append(Paragraph(f"Customizations: {customizations}", styles['Normal']))
    story.append(Spacer(1, 6))

    # Clauses
    clauses = [
        ("Scope of Purchase", f"The Buyer agrees to purchase the {lead.get('interest', 'vehicle')} including approved customizations as per final order form."),
        ("Price and Taxes", "All prices are in INR and inclusive of applicable taxes. GST at 28% applies to luxury vehicles and shall be itemized in the tax invoice."),
        ("Payments", contract.get('payment_terms', '100% on delivery') + ". Payments are to be made via bank transfer or other approved modes."),
        ("Delivery", f"Delivery will be made at {contract.get('delivery_location', 'the dealership')} subject to availability, regulatory compliance, and receipt of due payments."),
        ("Inspection & Acceptance", "Buyer may inspect the vehicle upon delivery. Acceptance occurs upon signing the delivery note or registration completion."),
        ("Registration & Compliance", "All RTO registration, insurance, and statutory compliances will be coordinated by the dealership with Buyer cooperation."),
        ("Warranty", "Manufacturer warranty terms apply as per official documentation. Any extended warranties will be listed separately."),
        ("Cancellation & Refunds", "If the Buyer cancels prior to delivery, cancellation fees may apply to cover actual losses incurred."),
        ("Confidentiality", "Both parties shall keep this agreement, pricing, and specifications confidential, except as required by law."),
        ("Limitation of Liability", "In no event shall the dealership be liable for indirect or consequential losses. Liability is limited to the amounts paid."),
        ("Governing Law & Jurisdiction", "This contract is governed by the laws of India. Courts in Mumbai shall have exclusive jurisdiction."),
        ("Arbitration", "Any dispute shall be referred to a sole arbitrator appointed mutually, under the Arbitration and Conciliation Act, 1996."),
        ("Force Majeure", "Neither party shall be liable for delays due to events beyond reasonable control, including natural calamities or government actions."),
        ("Entire Agreement", "This document with its annexures constitutes the entire agreement and supersedes prior communications on the subject."),
    ]

    for idx, (title, text) in enumerate(clauses, start=1):
        story.append(Paragraph(f"{idx}. {title}", styles['Section']))
        story.append(Paragraph(text, styles['Clause']))

    story.append(Spacer(1, 10))
    story.append(Paragraph("Signatures", styles['Section']))

    sig_tbl = Table([
        ["Buyer Signature", "Authorized Signatory (Dealership)"] ,
        ["\n\n__________________________", "\n\n__________________________"],
        [lead.get('name', ''), "For Luxury Automotive"],
        [datetime.now().strftime('%Y-%m-%d'), datetime.now().strftime('%Y-%m-%d')],
    ], colWidths=[80*mm, 80*mm])
    sig_tbl.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('LINEABOVE', (0,1), (0,1), 0.25, colors.gray),
        ('LINEABOVE', (1,1), (1,1), 0.25, colors.gray),
        ('TOPPADDING', (0,1), (-1,1), 12),
    ]))
    story.append(sig_tbl)

    story.append(Spacer(1, 8))
    story.append(Paragraph("Note: Please review all details carefully. For queries, contact your Relationship Manager.", styles['Small']))

    doc.build(story, onFirstPage=_draw_border, onLaterPages=_draw_border)
    return buf.getvalue()
