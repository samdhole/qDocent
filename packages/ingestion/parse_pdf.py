"""PDF parsing — routes to fast-text, table-aware, or OCR parser.

Returns a list of raw page dicts. Chunking happens in chunk_templates.py.
Table normalization happens in normalize_tables.py.

No LLM calls here — this module is 100% deterministic.
"""
# pattern: Imperative Shell
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import camelot
import pdfplumber
import pytesseract
from PIL import Image
from pytesseract import Output

# Set Tesseract binary path for Windows
_TESS_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(_TESS_PATH):
    pytesseract.pytesseract.tesseract_cmd = _TESS_PATH


def parse_pdf(pdf_path: str | Path, parser: str) -> list[dict[str, Any]]:
    """Parse a PDF and return a list of page-level dicts.

    Each dict has:
        page_number: int (1-indexed)
        text: str
        tables: list[dict]  — raw table dicts (see normalize_tables.py)
        confidence: float   — 100.0 for text pages, OCR confidence for scanned
        bbox: list[float]   — [x0, top, x1, bottom] of page
        parser: str
    """
    path = Path(pdf_path)
    if parser == "ocr":
        return _parse_ocr(path)
    if parser == "table_aware":
        return _parse_table_aware(path)
    return _parse_fast_text(path)


def _parse_fast_text(path: Path) -> list[dict[str, Any]]:
    pages = []
    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            bbox = [page.bbox[0], page.bbox[1], page.bbox[2], page.bbox[3]]
            text_lines = [
                {"text": l["text"], "x0": l["x0"], "top": l["top"], "x1": l["x1"], "bottom": l["bottom"]}
                for l in page.extract_text_lines(return_chars=False)
                if l.get("text", "").strip()
            ]
            pages.append(
                {
                    "page_number": i + 1,
                    "text": text,
                    "tables": [],
                    "confidence": 100.0,
                    "bbox": bbox,
                    "text_lines": text_lines,
                    "parser": "fast_text",
                }
            )
    return pages


def _parse_table_aware(path: Path) -> list[dict[str, Any]]:
    # First pass: get text per page via pdfplumber
    text_by_page: dict[int, str] = {}
    bbox_by_page: dict[int, list[float]] = {}
    text_lines_by_page: dict[int, list[dict]] = {}
    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages):
            text_by_page[i + 1] = page.extract_text() or ""
            bbox_by_page[i + 1] = list(page.bbox)
            text_lines_by_page[i + 1] = [
                {"text": l["text"], "x0": l["x0"], "top": l["top"], "x1": l["x1"], "bottom": l["bottom"]}
                for l in page.extract_text_lines(return_chars=False)
                if l.get("text", "").strip()
            ]

    # Second pass: extract tables via camelot (pdfium backend, no Ghostscript needed)
    tables_by_page: dict[int, list[dict]] = {}
    try:
        camelot_tables = camelot.read_pdf(str(path), pages="all", flavor="lattice")
        for t in camelot_tables:
            pnum = t.parsing_report["page"]
            tables_by_page.setdefault(pnum, []).append(
                {
                    "df": t.df,
                    "accuracy": t.accuracy,
                    "bbox": list(getattr(t, "_bbox", None) or bbox_by_page.get(pnum, [])),
                    "page_number": pnum,
                }
            )
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("camelot failed on %s: %s", path.name, exc)

    pages = []
    for pnum, text in sorted(text_by_page.items()):
        pages.append(
            {
                "page_number": pnum,
                "text": text,
                "tables": tables_by_page.get(pnum, []),
                "confidence": 100.0,
                "bbox": bbox_by_page[pnum],
                "text_lines": text_lines_by_page.get(pnum, []),
                "parser": "table_aware",
            }
        )
    return pages


def _parse_ocr(path: Path) -> list[dict[str, Any]]:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError("Run: uv pip install pymupdf") from None

    pages = []
    doc = fitz.open(str(path))
    for i in range(len(doc)):
        page = doc[i]
        mat = fitz.Matrix(300 / 72, 300 / 72)
        pix = page.get_pixmap(matrix=mat)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        text = pytesseract.image_to_string(img)
        df_data = pytesseract.image_to_data(img, output_type=Output.DATAFRAME)
        word_rows = df_data[(df_data["level"] == 5) & (df_data["conf"] != -1)]
        confidence = float(word_rows["conf"].mean()) if not word_rows.empty else 0.0

        rect = page.rect
        pages.append(
            {
                "page_number": i + 1,
                "text": text,
                "tables": [],
                "confidence": confidence,
                "bbox": [rect.x0, rect.y0, rect.x1, rect.y1],
                "text_lines": [],
                "parser": "ocr",
            }
        )
    doc.close()
    return pages
