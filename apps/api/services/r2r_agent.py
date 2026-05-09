# pattern: Imperative Shell
"""R2R agent wrapper — multi-turn conversation path.

Kept separate from r2r_client.rag_query() so the simpler RAG path remains
available for RAGAS eval, smoke scripts, and the legacy /ask route. The agent
path adds conversation memory at the cost of a different response shape.
"""
from __future__ import annotations

import json
import logging
from collections.abc import Generator
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


def agent_stream(message: str, conversation_id: str) -> Generator[str, None, None]:
    """Stream agent events as SSE-formatted strings.

    Yields raw SSE frames (each a `data: <json>\\n\\n` line) so the route can
    pass them to `StreamingResponse` without further transformation.

    Event types we emit (matches R2R's typed events plus a final `done`):
    - `status`: synthesized progress beat ("searching" / "generating") for the UI
    - `token`: a token delta from the message stream
    - `final`: the final adapter-shaped dict (same as agent_query() return value)
    - `error`: if R2R errors mid-stream
    """
    try:
        stream = get_client().retrieval.agent(
            message={"role": "user", "content": message},
            conversation_id=conversation_id,
            search_settings=DEFAULT_SEARCH_SETTINGS,
            rag_generation_config={"stream": True},
        )
    except (httpx.HTTPError, R2RException) as exc:
        yield _sse({"type": "error", "detail": f"R2R unavailable: {exc}"})
        return

    yield _sse({"type": "status", "phase": "searching"})

    full_text_parts: list[str] = []
    last_search_results: dict[str, Any] = {}
    citations_seen = False
    generation_started = False

    try:
        for event in stream:
            event_type = type(event).__name__
            if event_type == "SearchResultsEvent":
                payload = _event_payload(event)
                last_search_results = payload.get("data", payload) or {}
                yield _sse({"type": "status", "phase": "found_results"})
            elif event_type == "MessageEvent":
                payload = _event_payload(event)
                delta = (payload.get("data", {}) or {}).get("delta", {}) or {}
                content_parts = delta.get("content") or []
                for part in content_parts:
                    text = (part or {}).get("payload", {}).get("value", "") or ""
                    if text:
                        if not generation_started:
                            generation_started = True
                            yield _sse({"type": "status", "phase": "generating"})
                        full_text_parts.append(text)
                        yield _sse({"type": "token", "text": text})
            elif event_type == "CitationEvent":
                citations_seen = True
            elif event_type == "FinalAnswerEvent":
                # The final event contains the assembled answer + citations.
                payload = _event_payload(event)
                yield _sse(
                    {
                        "type": "final",
                        "result": _adapt_final_event(
                            question=message,
                            payload=payload,
                            fallback_text="".join(full_text_parts),
                            search_results=last_search_results,
                        ),
                    }
                )
                return
    except (httpx.HTTPError, R2RException) as exc:
        yield _sse({"type": "error", "detail": f"R2R stream interrupted: {exc}"})
        return

    # If we exited the loop without a FinalAnswerEvent, synthesize one from
    # what we collected (defensive — the SDK is documented to always emit one).
    yield _sse(
        {
            "type": "final",
            "result": _adapt_final_event(
                question=message,
                payload={},
                fallback_text="".join(full_text_parts),
                search_results=last_search_results,
            ),
        }
    )


def _sse(data: dict) -> str:
    """Format a dict as an SSE data frame."""
    return f"data: {json.dumps(data)}\n\n"


def _event_payload(event: Any) -> dict[str, Any]:
    """Extract payload from an R2R event (pydantic model or dict)."""
    if hasattr(event, "model_dump"):
        return event.model_dump()
    if isinstance(event, dict):
        return event
    return {}


def _adapt_final_event(
    question: str,
    payload: dict[str, Any],
    fallback_text: str,
    search_results: dict[str, Any],
) -> dict[str, Any]:
    """Build the same dict shape `agent_query` returns, from streaming events.

    Re-uses the citation/header/figure logic from _adapt_agent_response by
    constructing a synthetic 'response' object — keeps the adapter logic in
    one place (DRY).
    """
    final_answer = (
        (payload.get("data") or {}).get("generated_answer")
        or (payload.get("data") or {}).get("answer")
        or fallback_text
    )

    # Build a fake "messages[-1].metadata.aggregated_search_results" so we can
    # call the same adapter the non-streaming path uses. SearchResultsEvent
    # already has the same structure under .data.
    fake_response = {
        "results": {
            "messages": [
                {
                    "role": "assistant",
                    "content": final_answer,
                    "metadata": {"aggregated_search_results": search_results},
                }
            ],
            "conversation_id": (payload.get("data") or {}).get("conversation_id"),
        }
    }
    return _adapt_agent_response(question, fake_response)
