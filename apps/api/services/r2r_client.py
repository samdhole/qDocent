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

from apps.api.services.document_store import (
    load_document_manifest,
    save_source_pdf,
    write_chunks_manifest,
    write_document_manifest,
)
from apps.api.services.figure_store import figures_for_response
from apps.api.services.r2r_chunk_adapter import (
    chunks_for_r2r,
    citation_from_retrieved_text,
)
from apps.api.services.citation_marker_rewriter import rewrite_brackets
from apps.api.services.r2r_client_helpers import _label_from_score, _valid_chunks
from packages.ingestion.pipeline import run_pipeline

load_dotenv()

_BASE_URL = os.getenv("R2R_BASE_URL", "http://localhost:7272")
DEFAULT_SEARCH_SETTINGS: dict[str, Any] = {
    "limit": 15,
    "use_hybrid_search": True,
    "hybrid_settings": {
        "full_text_weight": 1.0,
        "semantic_weight": 5.0,
        "full_text_limit": 200,
        "rrf_k": 50,
    },
    "graph_settings": {"enabled": False},
}


def get_client() -> R2RClient:
    """Public factory for the R2R SDK client. Use from other service modules."""
    return R2RClient(base_url=_BASE_URL)


def create_r2r_collection(name: str) -> str:
    """Create a new R2R collection and return its collection ID string."""
    client = get_client()
    response = client.collections.create(name=name)
    return str(response.results.id)


def delete_r2r_collection(collection_id: str) -> None:
    """Delete an R2R collection. Does NOT delete documents from R2R storage."""
    client = get_client()
    client.collections.delete(id=collection_id)


def add_document_to_r2r_collection(collection_id: str, r2r_document_id: str) -> None:
    """Associate an already-ingested R2R document with a collection."""
    client = get_client()
    client.collections.add_document(id=collection_id, document_id=r2r_document_id)


def rag_query(
    query: str,
    document_ids: list[str] | None = None,
    collection_id: str | None = None,
    search_strategy: str = "vanilla",
) -> dict[str, Any]:
    """Ask a RAG question. Returns structured dict for the /ask route.

    When collection_id is provided, filters retrieval to that collection using $overlap.
    When document_ids is provided and collection_id is None, filters by document IDs.
    collection_id takes precedence over document_ids when both are set.
    search_strategy: "vanilla" (default), "hyde" (good for conceptual queries), or "rag_fusion".
    """
    search_settings = dict(DEFAULT_SEARCH_SETTINGS)
    if search_strategy != "vanilla":
        search_settings["search_strategy"] = search_strategy
    if collection_id:
        search_settings["filters"] = {"collection_ids": {"$overlap": [collection_id]}}
    elif document_ids:
        combined_r2r_ids: list[str] = []
        for doc_id in document_ids:
            manifest = load_document_manifest(doc_id)
            r2r_ids = (manifest or {}).get("r2r_document_ids") or []
            combined_r2r_ids.extend(r2r_ids)
        if combined_r2r_ids:
            search_settings["filters"] = {"document_id": {"$in": combined_r2r_ids}}

    try:
        client = get_client()
        response = client.retrieval.rag(
            query=query,
            search_settings=search_settings,
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
                "chunk_index": header_citation.get("chunk_index"),
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

    answer, citations, retrieved_contexts = rewrite_brackets(
        answer, citations, retrieved_contexts
    )

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


def ingest_file(file_path: str, collection_id: str | None = None) -> Any:
    """Ingest a single file into R2R. Returns raw SDK response.

    When collection_id is provided, adds the document to that collection.
    """
    try:
        client = get_client()
        create_kwargs: dict[str, Any] = {"file_path": file_path}
        if collection_id:
            create_kwargs["collection_ids"] = [collection_id]
        return client.documents.create(**create_kwargs)
    except (httpx.HTTPError, R2RException) as exc:
        raise RuntimeError(f"R2R unavailable: {exc}") from exc


def delete_r2r_documents(document_ids: list[str]) -> dict[str, list[str]]:
    """Delete known R2R documents by SDK ID. Never raises — failures go to failed[]."""
    deleted: list[str] = []
    failed: list[str] = []
    try:
        client = get_client()
    except Exception:
        return {"deleted": [], "failed": list(document_ids)}
    for document_id in document_ids:
        try:
            client.documents.delete(document_id)
            deleted.append(document_id)
        except Exception as exc:
            logging.getLogger(__name__).warning("R2R delete failed for %s: %s", document_id, exc)
            failed.append(document_id)
    return {"deleted": deleted, "failed": failed}


def ingest_prechunked_document(
    chunks: list[dict[str, Any]],
    report: dict[str, Any],
    collection_id: str | None = None,
) -> Any:
    """Ingest DocQuery-produced chunks into R2R so retrieval keeps citation headers.

    When collection_id is provided, adds the document to that collection.
    """
    try:
        client = get_client()
        metadata = {
            "docquery_document_id": report.get("document_id"),
            "source_file": report.get("source_file"),
            "ingestion_mode": "docquery_pre_chunked",
        }
        create_kwargs: dict[str, Any] = {
            "chunks": chunks_for_r2r(chunks),
            "metadata": metadata,  # pass None values — R2R accepts them; preserves key presence for introspection
        }
        if collection_id:
            create_kwargs["collection_ids"] = [collection_id]
        return client.documents.create(**create_kwargs)
    except (httpx.HTTPError, R2RException) as exc:
        raise RuntimeError(f"R2R unavailable: {exc}") from exc


def ingest_file_with_pipeline(
    file_path: str, original_filename: str | None = None, collection_id: str | None = None
) -> dict:
    """Run ingestion pipeline, then ingest the original file and figure manifest into R2R.

    original_filename: the original uploaded filename. When provided, threads through
    to run_pipeline so figure records and quality reports show the real filename
    instead of the temp path.

    collection_id: optional R2R collection ID to associate the document with.
    When provided, the document is added to this collection during ingestion.

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
    if chunks:  # filter invalid chunks before deciding ingest path
        chunks = _valid_chunks(chunks)
    if chunks:  # pre-chunked path — may be empty after validation → falls to else
        r2r_result = ingest_prechunked_document(chunks, report, collection_id=collection_id)
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
        r2r_result = ingest_file(file_path, collection_id=collection_id)
        ingestion_mode = "raw_file_fallback"
        # save source PDF in fallback path when pipeline provided a document_id
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
            figure_r2r_result = ingest_file(figure_manifest, collection_id=collection_id)
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
        write_chunks_manifest(report["document_id"], chunks)

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


def ingest_source_with_pipeline(
    path_or_url: str, original_filename: str | None = None, collection_id: str | None = None
) -> dict:
    """Ingest a non-PDF source (DOCX, PPTX, or web URL) via run_pipeline_for_source.

    path_or_url: file path to DOCX/PPTX or URL string to web resource.
    original_filename: original uploaded filename or URL. When provided, threads through
    to run_pipeline_for_source so quality reports show the real filename instead of temp path.
    collection_id: optional R2R collection ID to associate the document with.

    Returns combined result: R2R response + quality report + figures list.
    For DOCX/PPTX, figures list is empty and no source PDF is saved.
    For URLs, source_url is None (no local PDF to serve).
    """
    from packages.ingestion.pipeline import run_pipeline_for_source

    log = logging.getLogger(__name__)
    pipeline_result: dict = {}
    try:
        pipeline_result = run_pipeline_for_source(
            path_or_url, source_file=original_filename or path_or_url, collection_id=collection_id
        )
        log.info(
            "Pipeline complete: %d chunks, classifier=%s",
            len(pipeline_result.get("chunks", [])),
            pipeline_result.get("classifier", "unknown"),
        )
    except RuntimeError:
        raise  # Re-raise pipeline errors so the route handler can catch them

    chunks = pipeline_result.get("chunks", [])
    report = pipeline_result.get("report", {})
    source_url = None
    r2r_document_ids: list[str] = []

    if chunks:
        chunks = _valid_chunks(chunks)
    if chunks:
        r2r_result = ingest_prechunked_document(chunks, report, collection_id=collection_id)
        primary_r2r_id = _r2r_document_id_from_response(r2r_result)
        if primary_r2r_id:
            r2r_document_ids.append(primary_r2r_id)
        document_id = report.get("document_id")
        if document_id and chunks:
            write_document_manifest(
                document_id,
                source_file=original_filename or path_or_url,
                r2r_document_ids=r2r_document_ids,
            )
            write_chunks_manifest(document_id, chunks)
    else:
        r2r_result = None
        document_id = report.get("document_id")

    # Extract ingestion_mode as a string from the classifier dict
    classifier = pipeline_result.get("classifier", {})
    if isinstance(classifier, dict):
        ingestion_mode = classifier.get("document_type", "unknown")
    else:
        ingestion_mode = str(classifier)

    return {
        "r2r": str(r2r_result) if r2r_result else None,
        "quality_report": report,
        "document_id": document_id,
        "ingestion_mode": ingestion_mode,
        "source_url": source_url,
        "r2r_document_ids": r2r_document_ids,
        "figures": [],
        "figures_r2r": None,
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
