"""Generate synthetic sample PDFs for local demo use."""
# pattern: Imperative Shell
from pathlib import Path

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
except ImportError:
    raise SystemExit("Run: uv pip install reportlab")

OUT = Path("data/sample_docs")
OUT.mkdir(parents=True, exist_ok=True)


def make_policy(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 720, "Acme Corp — Company Policy")
    c.setFont("Helvetica", 12)
    lines = [
        "",
        "Refund Policy",
        "Customers may request a refund within 30 days of purchase.",
        "Refund requests must be submitted to support@acme.example.",
        "Approval is required from the Customer Success Manager.",
        "",
        "Enterprise Discounts",
        "Enterprise discounts above 20% require VP Sales approval.",
        "Discounts up to 20% may be approved by account executives.",
        "",
        "Data Retention",
        "Customer data is retained for 7 years per regulatory requirements.",
    ]
    y = 700
    for line in lines:
        c.drawString(72, y, line)
        y -= 18
    c.save()


def make_pricing(path: Path) -> None:
    """Create pricing table using Platypus (real PDF table structure)."""
    doc = SimpleDocTemplate(str(path), pagesize=letter)
    story = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.black,
        spaceAfter=20,
    )
    story.append(Paragraph("Acme Corp — Pricing Table", title_style))
    story.append(Spacer(1, 0.3 * inch))

    # Create table data
    data = [
        ["Plan", "Price/mo", "Users", "Support"],
        ["Starter", "$29", "1", "Email"],
        ["Pro", "$99", "5", "Email + Chat"],
        ["Business", "$299", "25", "Priority"],
        ["Enterprise", "Custom", "Unlimited", "Dedicated CSM"],
    ]

    table = Table(data, colWidths=[1.5 * inch, 1.5 * inch, 1.5 * inch, 2 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    story.append(table)
    doc.build(story)


def make_support(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 720, "Acme Corp — Support History Sample")
    c.setFont("Helvetica", 12)
    tickets = [
        "Ticket #1001: Customer requested refund on 2024-01-15. Approved within policy.",
        "Ticket #1002: Enterprise discount requested (25%). Escalated to VP Sales.",
        "Ticket #1003: Data export request. Processed per retention policy.",
        "Ticket #1004: Billing dispute. Resolved by account executive.",
    ]
    y = 700
    for t in tickets:
        c.drawString(72, y, t)
        y -= 20
    c.save()


if __name__ == "__main__":
    make_policy(OUT / "company_policy.pdf")
    make_pricing(OUT / "pricing_table.pdf")
    make_support(OUT / "sample_support_history.pdf")
    print(f"Created 3 sample PDFs in {OUT}/")
