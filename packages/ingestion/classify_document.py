"""Classify a PDF document and recommend parser + chunking template.

60/30/10 rule: classification is fully deterministic (regex + pdfplumber heuristics).
LLM is used only when document_type cannot be resolved by rules — and only as a last resort.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import TypedDict

import pdfplumber

OCR_CHAR_THRESHOLD = 10  # pages with fewer chars than this are treated as scanned
TABLE_PAGE_RATIO_THRESHOLD = 0.25  # docs with >25% table-containing pages are table_heavy
COLUMN_GAP_THRESHOLD = 100  # points of horizontal gap indicating multi-column layout

# Keyword sets for rule-based document_type detection
_CONTRACT_KEYWORDS = re.compile(
    r"\b(agreement|contract|msa|dpa|terms and conditions|whereas|indemnif|governing law)\b",
    re.IGNORECASE,
)
_PAPER_KEYWORDS = re.compile(
    r"\b(abstract|introduction|methodology|conclusion|references|doi:|arxiv)\b",
    re.IGNORECASE,
)
_SLIDE_KEYWORDS = re.compile(
    r"\b(agenda|slide|presentation|click to edit|confidential — do not distribute)\b",
    re.IGNORECASE,
)


class ClassificationResult(TypedDict):
    file_name: str
    is_scanned: bool
    has_tables: bool
    has_columns: bool
    document_type: str
    recommended_template: str
    recommended_parser: str


_TEMPLATE_MAP: dict[str, str] = {
    "general": "policy",
    "paper": "paper",
    "legal_contract": "legal_contract",
    "table_heavy": "table_aware",
    "slide_deck": "slide",
    "manual": "manual",
}

_PARSER_MAP: dict[str, str] = {
    "general": "fast_text",
    "paper": "fast_text",
    "legal_contract": "fast_text",
    "table_heavy": "table_aware",
    "slide_deck": "fast_text",
    "manual": "table_aware",
}


def classify_document(pdf_path: str | Path) -> ClassificationResult:
    """Return classification dict for a PDF file."""
    path = Path(pdf_path)
    text_sample = ""
    scanned_pages = 0
    table_pages = 0
    has_columns = False
    total_pages = 0

    with pdfplumber.open(str(path)) as pdf:
        total_pages = len(pdf.pages)
        for page in pdf.pages:
            chars = page.chars
            if len(chars) < OCR_CHAR_THRESHOLD:
                scanned_pages += 1
            else:
                text_sample += (page.extract_text() or "") + "\n"

            # Detect tables heuristically via pdfplumber
            if page.extract_tables():
                table_pages += 1

            # Detect multi-column layout via large horizontal gap in word positions
            if not has_columns:
                words = page.extract_words()
                if len(words) > 10:
                    x_positions = sorted(w["x0"] for w in words)
                    gaps = [x_positions[i+1] - x_positions[i] for i in range(len(x_positions)-1)]
                    if any(g > COLUMN_GAP_THRESHOLD for g in gaps):
                        has_columns = True

    is_scanned = scanned_pages > total_pages * 0.5
    has_tables = table_pages > 0
    table_ratio = table_pages / max(total_pages, 1)

    document_type = _classify_type(text_sample, table_ratio, has_columns)
    recommended_parser = "ocr" if is_scanned else _PARSER_MAP[document_type]
    recommended_template = _TEMPLATE_MAP[document_type]

    return ClassificationResult(
        file_name=path.name,
        is_scanned=is_scanned,
        has_tables=has_tables,
        has_columns=has_columns,
        document_type=document_type,
        recommended_template=recommended_template,
        recommended_parser=recommended_parser,
    )


def _classify_type(text: str, table_ratio: float, has_columns: bool) -> str:
    """Rule-based document type detection. No LLM calls here."""
    if table_ratio >= TABLE_PAGE_RATIO_THRESHOLD:
        return "table_heavy"
    if _CONTRACT_KEYWORDS.search(text):
        return "legal_contract"
    if _PAPER_KEYWORDS.search(text):
        return "paper"
    if _SLIDE_KEYWORDS.search(text):
        return "slide_deck"
    return "general"
