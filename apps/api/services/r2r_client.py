"""R2R SDK wrapper — the only place in apps/api/ that imports r2r."""
# pattern: Imperative Shell
from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from dotenv import load_dotenv
from r2r import R2RClient
from shared.abstractions.exception import R2RException

from apps.api.services.figure_store import figures_for_response
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
        chunk_id = meta.get("chunk_id") or getattr(r, "id", None)
        citations.append(
            {
                "document": meta.get("source_file", "unknown"),
                "page": meta.get("page_start"),
                "section": meta.get("section_path"),
                "chunk_id": chunk_id,
            }
        )
        retrieved_contexts.append(
            {
                "chunk_id": chunk_id,
                "text": (getattr(r, "text", "") or "")[:400],
                "score": round(score, 4),
            }
        )

    # Heuristic confidence label (0–1 score scale from R2R)
    # Thresholds: high >= 0.80, medium >= 0.50, low < 0.50 or no results
    top_score = retrieved_contexts[0]["score"] if retrieved_contexts else 0.0
    confidence_label, needs_review = _label_from_score(top_score)

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

    # Always ingest the raw file into R2R for vector retrieval
    r2r_result = ingest_file(file_path)

    # Ingest figure manifest only after PDF ingest succeeds — non-fatal on failure
    figure_r2r_result = None
    figure_manifest = pipeline_result.get("figure_manifest")
    if figure_manifest:
        try:
            figure_r2r_result = ingest_file(figure_manifest)
        except RuntimeError as exc:
            log.warning("Figure manifest ingest failed: %s", exc)

    return {
        "r2r": str(r2r_result),
        "quality_report": pipeline_result.get("report"),
        "document_id": pipeline_result.get("report", {}).get("document_id"),
        "figures": pipeline_result.get("figures", []),
        "figures_r2r": str(figure_r2r_result) if figure_r2r_result else None,
    }
