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
from packages.ingestion.extract_figures import extract_figures, write_figure_manifest
from packages.ingestion.normalize_tables import normalize_page_tables
from packages.ingestion.parse_pdf import parse_pdf
from packages.ingestion.quality_report import generate_report


def run_pipeline(
    pdf_path: str | Path,
    document_id: str | None = None,
    source_file: str | None = None,
) -> dict[str, Any]:
    """Classify, parse, normalize, chunk, extract figures, and report on a PDF.

    source_file: the original uploaded filename. Defaults to path.name so
    callers that don't pass it get the temp filename — pass it explicitly to
    avoid temp paths appearing in figure records and quality reports.

    Returns the quality report dict plus figures and chunk metadata.
    R2R ingestion is done by the caller after this function returns.

    NOTE: The API sends these chunks to R2R's pre-chunked ingest path with a
    citation header embedded in each chunk, preserving DocQuery source/page metadata
    through retrieval. If this pipeline fails or emits no chunks, the caller can still
    fall back to raw-file ingestion.
    """
    path = Path(pdf_path)
    doc_id = document_id or path.stem
    src_file = source_file or path.name

    cls = classify_document(path)
    pages = parse_pdf(path, cls["recommended_parser"])
    tables: list[dict] = []
    for p in pages:
        tables.extend(normalize_page_tables(p))
    chunks = chunk_document(
        pages,
        tables,
        document_id=doc_id,
        source_file=src_file,
        parser=cls["recommended_parser"],
        chunk_template=cls["recommended_template"],
    )

    figures = extract_figures(path, doc_id, src_file)
    figure_manifest = write_figure_manifest(doc_id, figures)

    report = generate_report(doc_id, src_file, pages, chunks, cls, figures=figures)
    return {
        "report": report,
        "chunks": chunks,
        "classifier": cls,
        "figures": figures,
        "figure_manifest": str(figure_manifest) if figure_manifest else None,
    }
