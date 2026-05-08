"""Create a test PDF with an embedded raster image for visual verification testing."""
# pattern: Imperative Shell
from pathlib import Path
from io import BytesIO

try:
    from PIL import Image, ImageDraw, ImageFont
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
except ImportError:
    raise SystemExit("Run: uv pip install Pillow reportlab")

OUT = Path("data/sample_docs")
OUT.mkdir(parents=True, exist_ok=True)


def make_test_image() -> BytesIO:
    """Create a 300x200 test diagram image."""
    img = Image.new("RGB", (300, 200), color=(240, 248, 255))
    draw = ImageDraw.Draw(img)
    # Draw a simple "architecture diagram"
    draw.rectangle([20, 20, 130, 80], outline=(70, 130, 180), width=3, fill=(173, 216, 230))
    draw.text((35, 45), "Web UI\n:3000", fill=(0, 0, 128))
    draw.rectangle([170, 20, 280, 80], outline=(70, 130, 180), width=3, fill=(173, 216, 230))
    draw.text((185, 45), "API\n:8000", fill=(0, 0, 128))
    draw.rectangle([75, 120, 215, 180], outline=(70, 130, 180), width=3, fill=(144, 238, 144))
    draw.text((90, 145), "R2R :7272", fill=(0, 100, 0))
    # Arrows
    draw.line([130, 50, 170, 50], fill=(100, 100, 100), width=2)
    draw.line([155, 80, 155, 120], fill=(100, 100, 100), width=2)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def make_image_pdf(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, height - 72, "Acme Corp — System Architecture Report")

    c.setFont("Helvetica", 12)
    c.drawString(72, height - 110, "The following diagram shows the system architecture:")

    img_buf = make_test_image()
    img_reader = ImageReader(img_buf)
    c.drawImage(img_reader, 72, height - 340, width=300, height=200)

    c.setFont("Helvetica-Oblique", 10)
    c.drawString(72, height - 360, "Figure 1: System architecture showing Web UI, API, and R2R components.")

    c.setFont("Helvetica", 12)
    c.drawString(72, height - 410, "Key components:")
    lines = [
        "- Web UI (port 3000): Next.js frontend for user interaction",
        "- API (port 8000): FastAPI wrapper handling business logic",
        "- R2R (port 7272): Vector store and RAG retrieval engine",
    ]
    y = height - 430
    for line in lines:
        c.drawString(72, y, line)
        y -= 20

    c.save()
    print(f"Created {path} with embedded raster image")


if __name__ == "__main__":
    make_image_pdf(OUT / "architecture_report.pdf")
