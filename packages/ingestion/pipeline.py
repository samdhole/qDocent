"""Orchestrate the full ingestion pipeline and return quality report.

Called by apps/api/services/r2r_client.ingest_file_with_pipeline().
Never imported by apps/web/ directly.
# pattern: Imperative Shell
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.ingestion.chunk_templates import chunk_document
from packages.ingestion.classify_document import classify_document
from packages.ingestion.normalize_tables import normalize_page_tables
from packages.ingestion.parse_pdf import parse_pdf
from packages.ingestion.quality_report import generate_report


def run_pipeline(pdf_path: str | Path, document_id: str | None = None) -> dict[str, Any]:
    """Classify, parse, normalize, chunk, and report on a PDF.

    Returns the quality report dict. Chunks are not sent to R2R here —
    that is done by the caller after this function returns.

    NOTE: Chunks are produced for quality reporting and citation metadata extraction.
    The raw PDF file is sent to R2R separately via ingest_file() — R2R performs its own
    chunking for retrieval. Pre-chunked ingestion via R2R SDK is a Phase 4 enhancement.
    """
    path = Path(pdf_path)
    doc_id = document_id or path.stem

    cls = classify_document(path)
    pages = parse_pdf(path, cls["recommended_parser"])
    tables: list[dict] = []
    for p in pages:
        tables.extend(normalize_page_tables(p))
    chunks = chunk_document(
        pages,
        tables,
        document_id=doc_id,
        source_file=path.name,
        parser=cls["recommended_parser"],
        chunk_template=cls["recommended_template"],
    )
    report = generate_report(doc_id, path.name, pages, chunks, cls)
    return {"report": report, "chunks": chunks, "classifier": cls}
