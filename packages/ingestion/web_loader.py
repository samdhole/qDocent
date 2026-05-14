# pattern: Imperative Shell
"""Fetch a web URL and convert its content to page dicts using trafilatura.

Page dicts match the shape produced by parse_pdf.py so all downstream
chunking works without modification. Bboxes are synthetic.

SSRF protection is enforced upstream in routes/notebooks.py via _is_safe_url().
"""
from __future__ import annotations

import logging
import re
from typing import Any

import trafilatura

log = logging.getLogger(__name__)

_SYNTHETIC_PAGE_BBOX = [0.0, 0.0, 612.0, 792.0]
_SECTION_SPLIT_RE = re.compile(r"^#{1,3} ", re.MULTILINE)


def load_url(url: str) -> list[dict[str, Any]]:
    """Fetch a URL and convert its text to a list of page dicts.

    Raises RuntimeError if trafilatura cannot fetch or extract content.
    trafilatura returns None (not empty string) on fetch/extraction failure.
    """
    downloaded = trafilatura.fetch_url(url)
    if downloaded is None:
        raise RuntimeError(f"trafilatura could not fetch '{url}'")
    text = trafilatura.extract(downloaded, include_tables=True, output_format="txt")
    if not text or not text.strip():
        raise RuntimeError(
            f"trafilatura extracted empty content from '{url}' — "
            "page may be JavaScript-rendered or require authentication"
        )
    return _text_to_pages(text)


def _text_to_pages(text: str) -> list[dict[str, Any]]:
    """Split text on H1-H3 headings; each section becomes a page dict."""
    parts = _SECTION_SPLIT_RE.split(text)
    pages = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        pages.append({
            "page_number": len(pages) + 1,
            "text": part,
            "tables": [],
            "confidence": 100.0,
            "bbox": list(_SYNTHETIC_PAGE_BBOX),
            "text_lines": [],
            "parser": "web",
        })
    if not pages:
        pages.append({
            "page_number": 1,
            "text": text.strip(),
            "tables": [],
            "confidence": 100.0,
            "bbox": list(_SYNTHETIC_PAGE_BBOX),
            "text_lines": [],
            "parser": "web",
        })
    return pages
