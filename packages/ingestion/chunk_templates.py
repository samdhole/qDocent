"""Apply chunking templates and attach citation metadata to every chunk.

INVARIANT: Every chunk dict MUST contain all 9 citation metadata fields:
    document_id, source_file, page_start, page_end, section_path,
    bbox, parser, chunk_template, confidence

A chunk missing any field is invalid output (per packages/ingestion/CONTEXT.md).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


def chunk_document(
    pages: list[dict[str, Any]],
    normalized_tables: list[dict[str, Any]],
    document_id: str,
    source_file: str,
    parser: str,
    chunk_template: str,
    max_chars: int = 1200,
) -> list[dict[str, Any]]:
    """Chunk a parsed document into citation-rich chunk dicts.

    Args:
        pages: output of parse_pdf()
        normalized_tables: output of normalize_page_tables() for all pages
        document_id: unique document identifier (e.g. 'company_policy')
        source_file: original filename (e.g. 'company_policy.pdf')
        parser: parser name used (e.g. 'fast_text', 'table_aware', 'ocr')
        chunk_template: template name (e.g. 'policy', 'legal_contract')
        max_chars: maximum characters per text chunk

    Returns:
        List of chunk dicts, each with full citation metadata.
    """
    if chunk_template in ("legal_contract",):
        return _clause_aware_chunks(pages, document_id, source_file, parser, chunk_template, max_chars)
    if chunk_template in ("table_aware",):
        return _table_aware_chunks(pages, normalized_tables, document_id, source_file, parser, chunk_template, max_chars)
    # Default: heading-aware (general, policy, paper, slide, manual)
    return _heading_aware_chunks(pages, document_id, source_file, parser, chunk_template, max_chars)


def _make_chunk(
    text: str,
    document_id: str,
    source_file: str,
    page_start: int,
    page_end: int,
    section_path: str,
    bbox: list[float],
    parser: str,
    chunk_template: str,
    confidence: float,
    extra: dict | None = None,
) -> dict[str, Any]:
    """Build a chunk dict with complete citation metadata schema."""
    chunk: dict[str, Any] = {
        "text": text.strip(),
        "document_id": document_id,
        "source_file": source_file,
        "page_start": page_start,
        "page_end": page_end,
        "section_path": section_path,
        "bbox": bbox,
        "parser": parser,
        "chunk_template": chunk_template,
        "confidence": round(confidence / 100.0, 4),  # normalize to 0-1
    }
    if extra:
        chunk.update(extra)
    return chunk


_HEADING_RE = re.compile(r"^(#{1,3}|[A-Z][A-Z\s]{3,})\s", re.MULTILINE)
_CLAUSE_RE = re.compile(r"^\d+\.\d*\s|^Section \d+", re.MULTILINE | re.IGNORECASE)


def _heading_aware_chunks(
    pages: list[dict], document_id: str, source_file: str,
    parser: str, chunk_template: str, max_chars: int,
) -> list[dict]:
    chunks = []
    current_section = "Document"

    for page in pages:
        text = page["text"]
        confidence = page["confidence"]
        bbox = page["bbox"]
        pnum = page["page_number"]

        # Split on headings
        segments = _HEADING_RE.split(text)
        for seg in segments:
            seg = seg.strip()
            if not seg:
                continue
            # Detect if this segment is a heading
            if _HEADING_RE.match(seg + " "):
                current_section = seg[:80]
                continue
            # Break into max_chars chunks
            for sub in _split_text(seg, max_chars):
                if sub.strip():
                    chunks.append(
                        _make_chunk(
                            text=sub,
                            document_id=document_id,
                            source_file=source_file,
                            page_start=pnum,
                            page_end=pnum,
                            section_path=current_section,
                            bbox=bbox,
                            parser=parser,
                            chunk_template=chunk_template,
                            confidence=confidence,
                        )
                    )
    return chunks


def _clause_aware_chunks(
    pages: list[dict], document_id: str, source_file: str,
    parser: str, chunk_template: str, max_chars: int,
) -> list[dict]:
    chunks = []
    for page in pages:
        text = page["text"]
        pnum = page["page_number"]
        confidence = page["confidence"]
        bbox = page["bbox"]

        clauses = _CLAUSE_RE.split(text)
        for i, clause in enumerate(clauses):
            clause = clause.strip()
            if not clause:
                continue
            for sub in _split_text(clause, max_chars):
                if sub.strip():
                    chunks.append(
                        _make_chunk(
                            text=sub,
                            document_id=document_id,
                            source_file=source_file,
                            page_start=pnum,
                            page_end=pnum,
                            section_path=f"Clause {i+1}",
                            bbox=bbox,
                            parser=parser,
                            chunk_template=chunk_template,
                            confidence=confidence,
                        )
                    )
    return chunks


def _table_aware_chunks(
    pages: list[dict], normalized_tables: list[dict],
    document_id: str, source_file: str,
    parser: str, chunk_template: str, max_chars: int,
) -> list[dict]:
    chunks = []
    # Table chunks first
    for t in normalized_tables:
        pnum = t["page_number"]
        text = t["normalized_table_text"]
        if text.strip():
            chunks.append(
                _make_chunk(
                    text=text,
                    document_id=document_id,
                    source_file=source_file,
                    page_start=pnum,
                    page_end=pnum,
                    section_path="Table",
                    bbox=t["bbox"],
                    parser=parser,
                    chunk_template=chunk_template,
                    confidence=100.0,
                    extra={
                        "raw_table_markdown": t["raw_table_markdown"],
                        "normalized_table_text": t["normalized_table_text"],
                    },
                )
            )
    # Text chunks for non-table content
    chunks.extend(
        _heading_aware_chunks(pages, document_id, source_file, parser, chunk_template, max_chars)
    )
    return chunks


def _split_text(text: str, max_chars: int) -> list[str]:
    """Split text into chunks of at most max_chars, breaking at sentence boundaries."""
    if len(text) <= max_chars:
        return [text]
    parts = []
    while text:
        if len(text) <= max_chars:
            parts.append(text)
            break
        cut = text.rfind(". ", 0, max_chars)
        if cut == -1:
            cut = max_chars
        else:
            cut += 1
        parts.append(text[:cut].strip())
        text = text[cut:].strip()
    return parts
