"""Orchestrate the full ingestion pipeline and return quality report.

Called by apps/api/services/r2r_client.ingest_file_with_pipeline().
Never imported by apps/web/ directly.
# pattern: Imperative Shell
"""
from __future__ import annotations

import re
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


def run_pipeline_for_source(
    path_or_url: str,
    source_file: str | None = None,
    collection_id: str | None = None,
) -> dict[str, Any]:
    """Multi-format pipeline entry point for DOCX, PPTX, and web URLs.

    Do NOT call this for PDFs — use run_pipeline() instead.
    Returns the same shape as run_pipeline: {report, chunks, classifier, figures, figure_manifest}.
    """
    from packages.ingestion.format_router import detect_source_type, SourceType
    from packages.ingestion.docling_loader import load_document_with_docling
    from packages.ingestion.web_loader import load_url

    source_type = detect_source_type(path_or_url)
    if source_type == SourceType.PDF:
        raise ValueError("PDF files must use run_pipeline(), not run_pipeline_for_source()")

    if source_type == SourceType.URL:
        pages = load_url(path_or_url)
        effective_source = source_file or path_or_url
        classifier_name = "web"
        chunk_template = "general"
    else:
        # DOCX or PPTX
        pages = load_document_with_docling(path_or_url)
        effective_source = source_file or Path(path_or_url).name
        classifier_name = source_type.value  # "docx" or "pptx"
        chunk_template = "general"

    document_id = _make_document_id(effective_source)

    chunks = chunk_document(
        pages=pages,
        normalized_tables=[],
        document_id=document_id,
        source_file=effective_source,
        parser=classifier_name,
        chunk_template=chunk_template,
    )

    # Create a classifier_result dict matching the shape from classify_document()
    classifier_result = {
        "document_type": classifier_name,
        "recommended_parser": classifier_name,
        "recommended_template": chunk_template,
    }

    report = generate_report(
        document_id=document_id,
        source_file=effective_source,
        pages=pages,
        chunks=chunks,
        classifier_result=classifier_result,
        figures=[],
    )

    return {
        "report": report,
        "chunks": chunks,
        "classifier": classifier_result,
        "figures": [],
        "figure_manifest": None,
    }


def _make_document_id(source_file: str) -> str:
    """Deterministic document_id from source_file name (same as existing pipeline)."""
    stem = Path(source_file).stem
    slug = re.sub(r"[^A-Za-z0-9_-]", "_", stem)[:40] or "document"
    return slug
