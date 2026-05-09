# pattern: Imperative Shell
"""R2R agent wrapper — multi-turn conversation path.

Kept separate from r2r_client.rag_query() so the simpler RAG path remains
available for RAGAS eval, smoke scripts, and the legacy /ask route. The agent
path adds conversation memory at the cost of a different response shape.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from shared.abstractions.exception import R2RException

from apps.api.services.figure_store import figures_for_response
from apps.api.services.r2r_chunk_adapter import citation_from_retrieved_text
from apps.api.services.r2r_client import DEFAULT_SEARCH_SETTINGS, get_client
from apps.api.services.r2r_client_helpers import _label_from_score

log = logging.getLogger(__name__)


def create_conversation(name: str | None = None) -> str:
    """Create a new R2R conversation, return its ID."""
    try:
        response = get_client().conversations.create(name=name)
    except (httpx.HTTPError, R2RException) as exc:
        raise RuntimeError(f"R2R unavailable: {exc}") from exc
    inner = getattr(response, "results", response)
    conversation_id = getattr(inner, "id", None) or (
        inner.get("id") if isinstance(inner, dict) else None
    )
    if not conversation_id:
        raise RuntimeError("R2R returned a conversation without an ID.")
    return str(conversation_id)


def agent_query(message: str, conversation_id: str) -> dict[str, Any]:
    """Send one user message in a conversation. Returns the same response
    shape as r2r_client.rag_query() so the frontend can render it identically.
    """
    try:
        response = get_client().retrieval.agent(
            message={"role": "user", "content": message},
            conversation_id=conversation_id,
            search_settings=DEFAULT_SEARCH_SETTINGS,
        )
    except (httpx.HTTPError, R2RException) as exc:
        raise RuntimeError(f"R2R unavailable: {exc}") from exc
    return _adapt_agent_response(message, response)


def _adapt_agent_response(question: str, response: Any) -> dict[str, Any]:
    """Map the agent response (messages + metadata) to the same dict shape
    rag_query() returns. Keeps the frontend renderer unchanged.

    Expected shape (verified by Task 1 spike):
        results.messages[-1].content                                          → answer text
        results.messages[-1].metadata.aggregated_search_result (singular,
            JSON string or dict).chunk_search_results                         → list of retrieved chunks
        results.conversation_id                                               → conversation_id
    """
    # Extract inner dict/object from response.results or use response directly
    inner = (
        getattr(response, "results", None)
        or (response.get("results") if isinstance(response, dict) else None)
        or response
    )

    messages = getattr(inner, "messages", None) or (
        inner.get("messages") if isinstance(inner, dict) else []
    )
    last_message = messages[-1] if messages else None
    answer = ""
    metadata: dict[str, Any] = {}
    if last_message is not None:
        answer = (
            getattr(last_message, "content", None)
            or (last_message.get("content") if isinstance(last_message, dict) else "")
            or ""
        )
        metadata = (
            getattr(last_message, "metadata", None)
            or (last_message.get("metadata") if isinstance(last_message, dict) else {})
            or {}
        )

    # Handle both singular (aggregated_search_result) and plural (aggregated_search_results)
    # The spike found singular; this handles both for forward compatibility
    aggregated = metadata.get("aggregated_search_results") or metadata.get("aggregated_search_result") or {}

    # If aggregated is a JSON string (as found in spike), parse it
    if isinstance(aggregated, str):
        try:
            parsed = json.loads(aggregated)
        except (json.JSONDecodeError, TypeError):
            parsed = {}
        aggregated = parsed if isinstance(parsed, dict) else {}
    elif not isinstance(aggregated, dict):
        # Defensive: if it's neither string nor dict (e.g., list from json.loads("[]")), reset
        aggregated = {}

    chunk_results = aggregated.get("chunk_search_results") or []

    citations: list[dict[str, Any]] = []
    retrieved_contexts: list[dict[str, Any]] = []
    for r in chunk_results:
        meta = (r.get("metadata") if isinstance(r, dict) else getattr(r, "metadata", {})) or {}
        score = (r.get("score") if isinstance(r, dict) else getattr(r, "score", 0.0)) or 0.0
        raw_text = (r.get("text") if isinstance(r, dict) else getattr(r, "text", "")) or ""
        header_citation, clean_text = citation_from_retrieved_text(raw_text)
        chunk_id = meta.get("chunk_id") or (
            r.get("id") if isinstance(r, dict) else getattr(r, "id", None)
        )
        citations.append(
            {
                "document": (
                    header_citation.get("document")
                    or meta.get("source_file")
                    or meta.get("title")
                    or "unknown"
                ),
                "page": header_citation.get("page") or meta.get("page_start"),
                "page_end": header_citation.get("page_end") or meta.get("page_end"),
                "section": header_citation.get("section") or meta.get("section_path"),
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

    top_score = retrieved_contexts[0]["score"] if retrieved_contexts else 0.0
    confidence_label, needs_review = _label_from_score(top_score)

    known_citations = [
        c for c in citations
        if c.get("document") != "unknown" or c.get("page") is not None
    ]
    if known_citations:
        citations = known_citations

    figures = figures_for_response(citations, retrieved_contexts)

    conversation_id = (
        getattr(inner, "conversation_id", None)
        or (inner.get("conversation_id") if isinstance(inner, dict) else None)
    )

    return {
        "question": question,
        "answer": answer,
        "citations": citations,
        "retrieved_contexts": retrieved_contexts,
        "figures": figures,
        "confidence_label": confidence_label,
        "needs_human_review": needs_review,
        "conversation_id": str(conversation_id) if conversation_id else None,
    }
