# pattern: Functional Core
"""Detect whether a source is a PDF, DOCX, PPTX, or web URL.

All functions are pure — no I/O. Callers dispatch to the appropriate loader.
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path


class SourceType(Enum):
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    URL = "url"


_EXT_MAP: dict[str, SourceType] = {
    ".pdf": SourceType.PDF,
    ".docx": SourceType.DOCX,
    ".pptx": SourceType.PPTX,
}


def detect_source_type(path_or_url: str) -> SourceType:
    """Return the SourceType for a file path or URL.

    Raises ValueError for unsupported types (.doc, .zip, etc.).
    """
    s = path_or_url.strip()
    if s.startswith("http://") or s.startswith("https://"):
        return SourceType.URL
    ext = Path(s).suffix.lower()
    if ext in _EXT_MAP:
        return _EXT_MAP[ext]
    raise ValueError(f"Unsupported source '{path_or_url}': extension '{ext}' not in {list(_EXT_MAP)}")
