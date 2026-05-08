# pattern: Functional Core
from __future__ import annotations

from typing import Any

_PREFIX = "DocQuery Citation:"


def _clean_header_value(value: Any) -> str:
    text = "" if value is None else str(value)
    return text.replace("\n", " ").replace(";", ",").strip()


def chunk_text_for_r2r(chunk: dict[str, Any], chunk_index: int) -> str:
    """Return R2R chunk text with DocQuery citation metadata embedded up front."""
    header = (
        f"{_PREFIX} "
        f"document_id={_clean_header_value(chunk.get('document_id'))}; "
        f"source_file={_clean_header_value(chunk.get('source_file'))}; "
        f"page_start={_clean_header_value(chunk.get('page_start'))}; "
        f"page_end={_clean_header_value(chunk.get('page_end'))}; "
        f"section_path={_clean_header_value(chunk.get('section_path'))}; "
        f"chunk_index={chunk_index}"
    )
    return f"{header}\n\n{str(chunk.get('text', '')).strip()}"


def chunks_for_r2r(chunks: list[dict[str, Any]]) -> list[str]:
    """Convert DocQuery chunk dicts to R2R's list[str] pre-chunked format."""
    return [chunk_text_for_r2r(chunk, i) for i, chunk in enumerate(chunks)]


def citation_from_retrieved_text(text: str) -> tuple[dict[str, Any], str]:
    """Extract DocQuery citation metadata from retrieved text when present."""
    if not text.startswith(_PREFIX):
        return {}, text

    header, separator, body = text.partition("\n\n")
    if not separator:
        return {}, text

    raw_pairs = header[len(_PREFIX):].strip().split(";")
    parsed: dict[str, str] = {}
    for pair in raw_pairs:
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        parsed[key.strip()] = value.strip()

    citation = {
        "document_id": parsed.get("document_id"),
        "document": parsed.get("source_file", "unknown"),
        "page": _int_or_none(parsed.get("page_start")),
        "page_end": _int_or_none(parsed.get("page_end")),
        "section": parsed.get("section_path"),
        "chunk_index": _int_or_none(parsed.get("chunk_index")),
    }
    return citation, body.strip()


def _int_or_none(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None
