# pattern: Imperative Shell
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

from packages.ingestion.extract_figures_helpers import (
    figure_id_from,
    nearest_caption,
)

log = logging.getLogger(__name__)

FIGURES_DIR = Path("data/figures")


def extract_figures(
    pdf_path: str | Path,
    document_id: str,
    source_file: str,
    min_width: float = 80.0,
    min_height: float = 80.0,
) -> list[dict[str, Any]]:
    """Extract embedded raster figures from a PDF and save as PNG assets.

    Writes figures.json to data/figures/{document_id}/ only when figures are
    found (overwrites on re-run for idempotency). Returns list of figure records.
    """
    pdf_path = Path(pdf_path)
    out_dir = FIGURES_DIR / document_id

    doc = fitz.open(str(pdf_path))
    records: list[dict[str, Any]] = []

    for page_index in range(len(doc)):
        page = doc[page_index]
        page_number = page_index + 1
        text_blocks = page.get_text("blocks")
        seen_rects: set[tuple[int, ...]] = set()

        for image_number, image_info in enumerate(page.get_images(full=True), start=1):
            xref = image_info[0]
            rects = page.get_image_rects(xref)

            for rect_index, rect in enumerate(rects, start=1):
                if rect.width < min_width or rect.height < min_height:
                    continue

                rect_key = tuple(round(v) for v in (rect.x0, rect.y0, rect.x1, rect.y1))
                if rect_key in seen_rects:
                    continue
                seen_rects.add(rect_key)

                fig_id = figure_id_from(document_id, page_number, image_number, rect_index)
                asset_rel = Path(document_id) / f"{fig_id}.png"
                asset_path = FIGURES_DIR / asset_rel

                out_dir.mkdir(parents=True, exist_ok=True)
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), clip=rect)
                pix.save(str(asset_path))

                ocr_text = _ocr_image(asset_path)
                caption = nearest_caption(text_blocks, rect)

                records.append({
                    "content_type": "figure",
                    "figure_id": fig_id,
                    "document_id": document_id,
                    "source_file": source_file,
                    "page_number": page_number,
                    "bbox": [rect.x0, rect.y0, rect.x1, rect.y1],
                    "asset_path": str(asset_path),
                    "image_url": f"/figures/{asset_rel.as_posix()}",
                    "caption": caption,
                    "ocr_text": ocr_text,
                })

    doc.close()

    if records:
        figures_json = out_dir / "figures.json"
        figures_json.write_text(
            json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    return records


def write_figure_manifest(
    document_id: str, figures: list[dict[str, Any]]
) -> Path | None:
    """Write figures.md Markdown sidecar for R2R ingestion.

    Returns None when figures list is empty (no file written).
    Each figure is a ## heading so R2R chunks it as one retrievable unit.
    """
    if not figures:
        return None

    out_dir = FIGURES_DIR / document_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "figures.md"

    lines: list[str] = [f"# Figure index for {document_id}", ""]
    for f in figures:
        lines += [
            f"## Figure ID: {f['figure_id']}",
            f"Content type: figure",
            f"Source file: {f['source_file']}",
            f"Page: {f['page_number']}",
            f"Image URL: {f['image_url']}",
            f"Caption: {f.get('caption') or ''}",
            f"OCR text: {f.get('ocr_text') or ''}",
            "",
        ]

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _ocr_image(path: Path) -> str:
    """Run pytesseract on a saved PNG. Returns '' on any failure."""
    try:
        with Image.open(path) as image:
            return " ".join(pytesseract.image_to_string(image).split())
    except Exception:
        return ""
