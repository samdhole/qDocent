# pattern: Imperative Shell
"""R2R agent wrapper — multi-turn conversation path.

Kept separate from r2r_client.rag_query() so the simpler RAG path remains
available for RAGAS eval, smoke scripts, and the legacy /ask route. The agent
path adds conversation memory at the cost of a different response shape.
"""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
from shared.abstractions.exception import R2RException

from apps.api.services.citation_marker_rewriter import rewrite_brackets
from apps.api.services.document_store import load_document_manifest
from apps.api.services.figure_store import figures_for_response
from apps.api.services.r2r_chunk_adapter import citation_from_retrieved_text
from sdk.asnyc_methods.retrieval import parse_retrieval_event

from apps.api.services.r2r_client import DEFAULT_SEARCH_SETTINGS, get_async_client, get_client
from apps.api.services.r2r_client_helpers import _label_from_score
from apps.api.services import conversation_store

log = logging.getLogger(__name__)

_DOC_ONLY_NOT_FOUND = "I couldn't find this in your documents."

_HISTORY_LIMIT = 40       # messages to load (20 Q+A pairs)
_ANSWER_SNIPPET_CHARS = 2000  # truncate long assistant answers in history to save tokens


def _build_task_prompt(conversation_id: str) -> str | None:
    """Load prior messages for this conversation and format as a history block.

    Returns None when there are no prior messages (first turn).
    The block is injected via RAG's task_prompt so the LLM has context for
    follow-up questions even though /retrieval/rag is stateless.

    Long assistant answers are truncated to _ANSWER_SNIPPET_CHARS so the
    history block stays within a reasonable token budget even for long sessions.
    """
    messages = conversation_store.get_messages(conversation_id, limit=_HISTORY_LIMIT)
    if not messages:
        return None
    lines = ["Prior conversation (use this context to answer follow-up questions):"]
    for msg in messages:
        if msg["role"] == "user":
            lines.append(f"User: {msg['content']}")
        else:
            content = msg["content"]
            if len(content) > _ANSWER_SNIPPET_CHARS:
                content = content[:_ANSWER_SNIPPET_CHARS] + "…"
            lines.append(f"Assistant: {content}")
    lines.append("\nCurrent question:")
    return "\n".join(lines)


def _apply_doc_only_check(result: dict[str, Any], doc_only: bool) -> dict[str, Any]:
    """Defense-in-depth: replace answer with not-found string when doc_only=True
    and the agent returned empty or low-confidence retrieval despite the pre-flight
    passing. Mutates and returns the same dict.
    """
    if doc_only and (
        not result.get("retrieved_contexts")
        or result.get("confidence_label") == "low"
    ):
        result["answer"] = _DOC_ONLY_NOT_FOUND
        result["confidence_label"] = "low"
        result["needs_human_review"] = True
        result["doc_only_not_found"] = True
    return result


def _preflight_top_score(query: str, search_settings: dict) -> float:
    """Search-only pre-flight: return the top chunk score without calling the agent.

    Uses client.retrieval.search() — no LLM generation, nothing written to R2R
    conversation history. Returns 0.0 on any error (conservative: treat as no results).
    """
    try:
        response = get_client().retrieval.search(
            query=query,
            search_settings=search_settings,
        )
        inner = getattr(response, "results", None) or (
            response.get("results") if isinstance(response, dict) else None
        ) or response
        chunks = getattr(inner, "chunk_search_results", None) or (
            inner.get("chunk_search_results") if isinstance(inner, dict) else []
        ) or []
        if not chunks:
            return 0.0
        first = chunks[0]
        score = getattr(first, "score", None) or (
            first.get("score") if isinstance(first, dict) else 0.0
        ) or 0.0
        return float(score)
    except Exception:
        return 0.0  # conservative: treat search error as no results


def _make_not_found_result(question: str, conversation_id: str | None) -> dict[str, Any]:
    """Standard not-found response dict, matching _assemble_from_chunks() shape."""
    return {
        "question": question,
        "answer": _DOC_ONLY_NOT_FOUND,
        "citations": [],
        "retrieved_contexts": [],
        "figures": [],
        "confidence_label": "low",
        "needs_human_review": True,
        "conversation_id": str(conversation_id) if conversation_id else None,
        "doc_only_not_found": True,
    }


def _build_search_settings(
    document_ids: list[str] | None,
    collection_id: str | None = None,
) -> dict[str, Any]:
    """Return search settings with optional collection or document-level filter.

    collection_id takes priority: when set, uses selected_collection_ids (not
    $overlap which breaks streaming RAG). document_ids filter only applied
    when no collection_id is given.
    """
    settings = dict(DEFAULT_SEARCH_SETTINGS)
    if collection_id:
        # Use selected_collection_ids — $overlap on collection_ids breaks streaming RAG
        settings["selected_collection_ids"] = [collection_id]
        return settings
    if not document_ids:
        return settings
    combined_r2r_ids: list[str] = []
    for document_id in document_ids:
        manifest = load_document_manifest(document_id)
        r2r_ids = (manifest or {}).get("r2r_document_ids") or []
        combined_r2r_ids.extend(r2r_ids)
        if not r2r_ids:
            log.warning(
                "document_id %s has no r2r_document_ids in manifest; skipping filter for this document",
                document_id,
            )
    if combined_r2r_ids:
        settings["filters"] = {"document_id": {"$in": combined_r2r_ids}}
    return settings


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


def agent_query(
    message: str,
    conversation_id: str,
    doc_only: bool = False,
    document_ids: list[str] | None = None,
    collection_id: str | None = None,
) -> dict[str, Any]:
    """Send one user message in a conversation. Returns the same response
    shape as r2r_client.rag_query() so the frontend can render it identically.

    When doc_only=True, runs a search-only pre-flight first. If retrieval is
    empty or low-confidence, returns not-found without calling the agent —
    preventing R2R conversation history from containing a suppressed answer.
    """
    search_settings = _build_search_settings(document_ids, collection_id)

    if doc_only:
        top_score = _preflight_top_score(message, search_settings)
        _, needs_review = _label_from_score(top_score)
        if needs_review:  # score < 0.50 → low confidence → skip agent
            return _make_not_found_result(message, conversation_id)

    task_prompt = _build_task_prompt(conversation_id)
    try:
        rag_kwargs: dict[str, Any] = dict(
            query=message,
            search_settings=search_settings,
            rag_generation_config={"stream": False},
        )
        if task_prompt:
            rag_kwargs["task_prompt"] = task_prompt
        response = get_client().retrieval.rag(**rag_kwargs)
    except (httpx.HTTPError, R2RException) as exc:
        raise RuntimeError(f"R2R unavailable: {exc}") from exc
    result = _adapt_rag_response(message, response, conversation_id)
    result = _apply_doc_only_check(result, doc_only)
    if conversation_id:
        conversation_store.add_message(conversation_id, "user", message)
        conversation_store.add_message(conversation_id, "assistant", result.get("answer", ""))
    return result


def _assemble_from_chunks(
    question: str,
    answer: str,
    chunk_results: list,
    conversation_id: str | None,
) -> dict[str, Any]:
    """Build the standard response dict from a parsed answer and raw chunk list.

    Pure helper — no I/O. Called by both the non-streaming (_adapt_agent_response)
    and streaming (_adapt_final_event) paths so citation/figure logic lives in one place.
    """
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

    top_score = retrieved_contexts[0]["score"] if retrieved_contexts else 0.0
    confidence_label, needs_review = _label_from_score(top_score)

    known_citations = [
        c for c in citations
        if c.get("document") != "unknown" or c.get("page") is not None
    ]
    if known_citations:
        citations = known_citations

    # Rewrite [shortid] → [N] and reorder citations/contexts to match prose order
    answer, citations, retrieved_contexts = rewrite_brackets(
        answer, citations, retrieved_contexts
    )

    figures = figures_for_response(citations, retrieved_contexts)

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


def _adapt_rag_response(question: str, response: Any, conversation_id: str | None) -> dict[str, Any]:
    """Map a non-streaming retrieval/rag response to the standard response dict.

    RAG response shape (R2R 3.6.x):
        results.completion          → answer string (not an object with .choices)
        results.search_results.chunk_search_results → list of retrieved chunks
    """
    inner = (
        getattr(response, "results", None)
        or (response.get("results") if isinstance(response, dict) else None)
        or response
    )

    # completion is a plain string in the RAG response
    answer = (
        getattr(inner, "completion", None)
        or (inner.get("completion") if isinstance(inner, dict) else None)
        or ""
    )
    if not isinstance(answer, str):
        # Defensive: handle object shape if R2R version differs
        answer = str(answer)

    search_results = (
        getattr(inner, "search_results", None)
        or (inner.get("search_results") if isinstance(inner, dict) else None)
        or {}
    )
    if hasattr(search_results, "__dict__") or hasattr(search_results, "model_dump"):
        search_results = (
            search_results.model_dump() if hasattr(search_results, "model_dump")
            else vars(search_results)
        )
    chunk_results = (
        (search_results.get("chunk_search_results") if isinstance(search_results, dict) else None)
        or []
    )

    return _assemble_from_chunks(question, answer, chunk_results, conversation_id)



async def agent_stream(
    message: str,
    conversation_id: str,
    doc_only: bool = False,
    document_ids: list[str] | None = None,
    collection_id: str | None = None,
) -> AsyncIterator[str]:
    """Stream agent events as SSE-formatted strings.

    Async generator so FastAPI handles it without occupying a thread-pool
    worker for the duration of the stream (each await releases the loop).

    Yields raw SSE frames (each a `data: <json>\\n\\n` line) so the route can
    pass them to `StreamingResponse` without further transformation.

    Event types we emit (matches R2R's typed events plus a final `done`):
    - `status`: synthesized progress beat ("searching" / "generating") for the UI
    - `token`: a token delta from the message stream
    - `final`: the final adapter-shaped dict (same as agent_query() return value)
    - `error`: if R2R errors mid-stream

    When doc_only=True, runs a search-only pre-flight first (same as agent_query).
    If retrieval is poor, yields a single final SSE frame with the not-found result
    and returns without calling the agent or writing to R2R conversation history.
    """
    search_settings = _build_search_settings(document_ids, collection_id)

    if doc_only:
        top_score = _preflight_top_score(message, search_settings)
        _, needs_review = _label_from_score(top_score)
        if needs_review:
            yield _sse({"type": "final", "result": _make_not_found_result(message, conversation_id)})
            return

    # Use /retrieval/rag instead of /retrieval/agent to avoid two issues:
    # 1. R2R 3.6.x SDK bug: agent() awaits an async generator (TypeError)
    # 2. gemini-3-flash-preview thinking model breaks R2R's multi-turn tool-call loop
    #    with "Function call is missing a thought_signature"; gemini-2.0-flash avoids
    #    that error but doesn't invoke search tools. /retrieval/rag bypasses tool calls
    #    entirely — it does search via search_settings then generates in one shot.
    _client = get_async_client()
    task_prompt = _build_task_prompt(conversation_id)
    _rag_data: dict[str, Any] = {
        "query": message,
        "rag_generation_config": {"stream": True},
        "search_settings": search_settings,
        "search_mode": "custom",
        "include_title_if_available": True,
    }
    if task_prompt:
        _rag_data["task_prompt"] = task_prompt

    yield _sse({"type": "status", "phase": "searching"})

    full_text_parts: list[str] = []
    last_search_results: dict[str, Any] = {}
    generation_started = False

    # SSE arrives as alternating lines: "event: <type>" then "data: <json>"
    # _make_streaming_request yields one line at a time as raw strings.
    # Accumulate into {"event": ..., "data": ...} dicts for parse_retrieval_event.
    _sse_event_type: str | None = None

    try:
        async for raw_event in _client._make_streaming_request(
            "POST", "retrieval/rag", json=_rag_data, version="v3"
        ):
            if not isinstance(raw_event, str):
                # Already a parsed dict (shouldn't happen with current SDK, but handle defensively)
                pass
            else:
                line = raw_event.strip()
                if line.startswith("event:"):
                    _sse_event_type = line[6:].strip()
                    continue
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if not data_str or data_str == "[DONE]":
                        _sse_event_type = None
                        continue
                    raw_event = {"event": _sse_event_type or "unknown", "data": data_str}
                    _sse_event_type = None
                else:
                    continue  # blank line or unknown SSE field
            event = parse_retrieval_event(raw_event)
            if event is None:
                continue
            event_type = type(event).__name__
            if event_type == "SearchResultsEvent":
                payload = _event_payload(event)
                # SearchResultsEvent.model_dump() → {event, data: {id, object, data: {chunk_search_results,...}}}
                # Drill through the two levels of "data" to get chunk_search_results at the top level.
                outer = payload.get("data") or {}
                last_search_results = outer.get("data", outer) or {}
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
            elif event_type == "FinalAnswerEvent":
                payload = _event_payload(event)
                adapted = _adapt_final_event(
                    question=message,
                    payload=payload,
                    fallback_text="".join(full_text_parts),
                    search_results=last_search_results,
                    conversation_id=conversation_id,
                )
                adapted = _apply_doc_only_check(adapted, doc_only)
                if conversation_id:
                    conversation_store.add_message(conversation_id, "user", message)
                    conversation_store.add_message(conversation_id, "assistant", adapted.get("answer", ""))
                yield _sse({"type": "final", "result": adapted})
                return
    except (httpx.HTTPError, R2RException) as exc:
        yield _sse({"type": "error", "detail": f"R2R stream interrupted: {exc}"})
        return
    except Exception as exc:
        log.exception("Unexpected error in agent_stream: %s", exc)
        yield _sse({"type": "error", "detail": f"Stream error: {exc}"})
        return

    # If we exited the loop without a FinalAnswerEvent, synthesize one from
    # what we collected (defensive — the SDK is documented to always emit one).
    adapted = _adapt_final_event(
        question=message,
        payload={},
        fallback_text="".join(full_text_parts),
        search_results=last_search_results,
        conversation_id=conversation_id,
    )
    adapted = _apply_doc_only_check(adapted, doc_only)
    if conversation_id:
        conversation_store.add_message(conversation_id, "user", message)
        conversation_store.add_message(conversation_id, "assistant", adapted.get("answer", ""))
    yield _sse({"type": "final", "result": adapted})


def _sse(data: dict) -> str:
    """Format a dict as an SSE data frame."""
    return f"data: {json.dumps(data, default=str)}\n\n"


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
    conversation_id: str | None = None,
) -> dict[str, Any]:
    """Build the standard response dict from streaming events."""
    final_answer = (
        (payload.get("data") or {}).get("generated_answer")
        or (payload.get("data") or {}).get("answer")
        or fallback_text
    )
    chunk_results = search_results.get("chunk_search_results") or []
    # Use caller-supplied conversation_id (RAG endpoint doesn't echo it back)
    event_conversation_id = (payload.get("data") or {}).get("conversation_id") or conversation_id
    return _assemble_from_chunks(question, final_answer, chunk_results, event_conversation_id)

