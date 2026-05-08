"""Generate synthetic sample PDFs for local demo use."""
from pathlib import Path

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
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
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, 720, "Acme Corp — Pricing Table")
    c.setFont("Helvetica", 12)
    rows = [
        ("Plan", "Price/mo", "Users", "Support"),
        ("Starter", "$29", "1", "Email"),
        ("Pro", "$99", "5", "Email + Chat"),
        ("Business", "$299", "25", "Priority"),
        ("Enterprise", "Custom", "Unlimited", "Dedicated CSM"),
    ]
    y = 690
    for row in rows:
        c.drawString(72, y, "  |  ".join(row))
        y -= 20
    c.save()


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
