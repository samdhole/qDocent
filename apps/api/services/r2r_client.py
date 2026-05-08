"""R2R SDK wrapper — the only place in apps/api/ that imports r2r."""
# pattern: Imperative Shell
from __future__ import annotations

import logging
import os
from typing import Any
from uuid import UUID

import httpx
from dotenv import load_dotenv
from r2r import R2RClient
from shared.abstractions.exception import R2RException

from apps.api.services.document_store import save_source_pdf, write_document_manifest
from apps.api.services.figure_store import figures_for_response
from apps.api.services.r2r_chunk_adapter import (
    chunks_for_r2r,
    citation_from_retrieved_text,
)
from apps.api.services.r2r_client_helpers import _label_from_score
from packages.ingestion.pipeline import run_pipeline

load_dotenv()

_BASE_URL = os.getenv("R2R_BASE_URL", "http://localhost:7272")
_SEARCH_SETTINGS: dict[str, Any] = {
    "limit": 5,
    "graph_settings": {"enabled": False},
}


def _client() -> R2RClient:
    return R2RClient(base_url=_BASE_URL)


def rag_query(query: str) -> dict[str, Any]:
    """Ask a RAG question. Returns structured dict for the /ask route."""
    try:
        client = _client()
        response = client.retrieval.rag(
            query=query,
            search_settings=_SEARCH_SETTINGS,
        )
    except (httpx.HTTPError, R2RException) as exc:
        raise RuntimeError(f"R2R unavailable: {exc}") from exc

    # New R2R SDK (>=3.6.6 with core) wraps responses in a .results object
    inner = getattr(response, "results", response)

    # Extract answer text
    answer = getattr(inner, "generated_answer", None) or str(inner)

    # Extract chunk search results from AggregateSearchResult
    agg = getattr(inner, "search_results", None)
    search_results = getattr(agg, "chunk_search_results", None) or [] if agg else []
    citations = []
    retrieved_contexts = []
    for r in search_results:
        meta = getattr(r, "metadata", {}) or {}
        score = getattr(r, "score", 0.0) or 0.0
        raw_text = getattr(r, "text", "") or ""
        header_citation, clean_text = citation_from_retrieved_text(raw_text)
        chunk_id = meta.get("chunk_id") or getattr(r, "id", None)
        citations.append(
            {
                "document": (
                    header_citation.get("document")
                    or meta.get("source_file")
                    or "unknown"
                ),
                "page": header_citation.get("page") or meta.get("page_start"),
                "page_end": header_citation.get("page_end") or meta.get("page_end"),
                "section": (
                    header_citation.get("section")
                    or meta.get("section_path")
                ),
                "document_id": header_citation.get("document_id"),
                "chunk_id": chunk_id,
            }
        )
        retrieved_contexts.append(
            {
                "chunk_id": chunk_id,
                "text": clean_text[:400],
                "score": round(score, 4),
            }
        )

    # Heuristic confidence label (0–1 score scale from R2R)
    # Thresholds: high >= 0.80, medium >= 0.50, low < 0.50 or no results
    top_score = retrieved_contexts[0]["score"] if retrieved_contexts else 0.0
    confidence_label, needs_review = _label_from_score(top_score)

    known_citations = [
        c for c in citations
        if c.get("document") != "unknown" or c.get("page") is not None
    ]
    if known_citations:
        citations = known_citations

    figures = figures_for_response(citations, retrieved_contexts)

    return {
        "question": query,
        "answer": answer,
        "citations": citations,
        "retrieved_contexts": retrieved_contexts,
        "figures": figures,
        "confidence_label": confidence_label,
        "needs_human_review": needs_review,
    }


def ingest_file(file_path: str) -> Any:
    """Ingest a single file into R2R. Returns raw SDK response."""
    try:
        client = _client()
        return client.documents.create(file_path=file_path)
    except (httpx.HTTPError, R2RException) as exc:
        raise RuntimeError(f"R2R unavailable: {exc}") from exc


def delete_r2r_documents(document_ids: list[str]) -> dict[str, list[str]]:
    """Delete known R2R documents by SDK ID."""
    deleted: list[str] = []
    failed: list[str] = []
    try:
        client = _client()
        for document_id in document_ids:
            try:
                client.documents.delete(document_id)
                deleted.append(document_id)
            except (httpx.HTTPError, R2RException):
                failed.append(document_id)
    except (httpx.HTTPError, R2RException) as exc:
        raise RuntimeError(f"R2R unavailable: {exc}") from exc
    return {"deleted": deleted, "failed": failed}


def ingest_prechunked_document(chunks: list[dict[str, Any]], report: dict[str, Any]) -> Any:
    """Ingest DocQuery-produced chunks into R2R so retrieval keeps citation headers."""
    try:
        client = _client()
        metadata = {
            "docquery_document_id": report.get("document_id"),
            "source_file": report.get("source_file"),
            "ingestion_mode": "docquery_pre_chunked",
        }
        return client.documents.create(
            chunks=chunks_for_r2r(chunks),
            metadata={k: v for k, v in metadata.items() if v is not None},
        )
    except (httpx.HTTPError, R2RException) as exc:
        raise RuntimeError(f"R2R unavailable: {exc}") from exc


def _valid_chunks(chunks: list[dict]) -> list[dict]:
    """Filter out chunks missing required fields for citation header embedding."""
    required = {"text", "document_id", "source_file"}
    valid = [c for c in chunks if all(c.get(k) for k in required)]
    if len(valid) < len(chunks):
        log = logging.getLogger(__name__)
        log.warning(
            "Dropped %d of %d chunks missing required fields",
            len(chunks) - len(valid),
            len(chunks),
        )
    return valid


def ingest_file_with_pipeline(
    file_path: str, original_filename: str | None = None
) -> dict:
    """Run ingestion pipeline, then ingest the original file and figure manifest into R2R.

    original_filename: the original uploaded filename. When provided, threads through
    to run_pipeline so figure records and quality reports show the real filename
    instead of the temp path.

    Figure manifest ingest runs only after the raw PDF ingest succeeds. Failure
    of the manifest ingest is non-fatal — logged as warning, not raised.

    Returns combined result: R2R response + quality report + figures list.
    Gracefully falls back to plain R2R ingestion if pipeline fails.
    """
    log = logging.getLogger(__name__)
    pipeline_result: dict = {}
    try:
        pipeline_result = run_pipeline(file_path, source_file=original_filename)
        log.info(
            "Pipeline complete: %d chunks, %d tables, %d figures",
            len(pipeline_result.get("chunks", [])),
            pipeline_result.get("report", {}).get("tables_detected", 0),
            len(pipeline_result.get("figures", [])),
        )
    except Exception as exc:
        log.warning("Pipeline failed, falling back to direct R2R ingest: %s", exc)

    chunks = pipeline_result.get("chunks", [])
    report = pipeline_result.get("report", {})
    source_url = None
    r2r_document_ids: list[str] = []
    if chunks:  # validation pass first (Task 3)
        chunks = _valid_chunks(chunks)
    if chunks:  # pre-chunked path — may be empty after validation → falls to else
        r2r_result = ingest_prechunked_document(chunks, report)
        primary_r2r_id = _r2r_document_id_from_response(r2r_result)
        if primary_r2r_id:
            r2r_document_ids.append(primary_r2r_id)
        ingestion_mode = "pre_chunked"
        document_id = report.get("document_id")
        source_file = (
            report.get("source_file")
            or original_filename
            or os.path.basename(file_path)
        )
        if document_id and source_file:
            save_source_pdf(file_path, document_id=document_id, source_file=source_file)
            source_url = f"/documents/{document_id}/source"
    else:  # fallback path: no chunks, pipeline failed, or all chunks filtered invalid
        r2r_result = ingest_file(file_path)
        ingestion_mode = "raw_file_fallback"
        # Task 2: save source PDF when pipeline provided a document_id
        _fallback_doc_id = report.get("document_id")
        _fallback_source = (
            report.get("source_file")
            or original_filename
            or os.path.basename(file_path)
        )
        if _fallback_doc_id and _fallback_source:
            save_source_pdf(file_path, document_id=_fallback_doc_id, source_file=_fallback_source)
            source_url = f"/documents/{_fallback_doc_id}/source"

    # Ingest figure manifest only after PDF ingest succeeds — non-fatal on failure
    figure_r2r_result = None
    figure_manifest = pipeline_result.get("figure_manifest")
    if figure_manifest:
        try:
            figure_r2r_result = ingest_file(figure_manifest)
            figure_r2r_id = _r2r_document_id_from_response(figure_r2r_result)
            if figure_r2r_id:
                r2r_document_ids.append(figure_r2r_id)
        except RuntimeError as exc:
            log.warning("Figure manifest ingest failed: %s", exc)

    if chunks and report.get("document_id"):
        write_document_manifest(
            report["document_id"],
            source_file=(
                report.get("source_file")
                or original_filename
                or os.path.basename(file_path)
            ),
            r2r_document_ids=r2r_document_ids,
        )

    return {
        "r2r": str(r2r_result),
        "quality_report": pipeline_result.get("report"),
        "document_id": pipeline_result.get("report", {}).get("document_id"),
        "ingestion_mode": ingestion_mode,
        "source_url": source_url,
        "r2r_document_ids": r2r_document_ids,
        "figures": pipeline_result.get("figures", []),
        "figures_r2r": str(figure_r2r_result) if figure_r2r_result else None,
    }


def _r2r_document_id_from_response(response: Any) -> str | None:
    """Best-effort extraction across R2R wrapped response shapes."""
    candidates = [getattr(response, "results", None), response]
    if isinstance(response, dict):
        candidates.extend([response.get("results"), response.get("result")])
    for candidate in candidates:
        if candidate is None:
            continue
        if isinstance(candidate, dict):
            document = candidate.get("document")
            values = [
                candidate.get("id"),
                candidate.get("document_id"),
                document.get("id") if isinstance(document, dict) else None,
            ]
        else:
            values = [
                getattr(candidate, "id", None),
                getattr(candidate, "document_id", None),
            ]
        for value in values:
            if isinstance(value, str | int | UUID) and value:
                return str(value)
    return None
