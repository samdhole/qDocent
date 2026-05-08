"""R2R SDK wrapper — the only place in apps/api/ that imports r2r."""
from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv
from r2r import R2RClient

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
    except (httpx.ConnectError, Exception) as exc:
        raise RuntimeError(f"R2R unavailable: {exc}") from exc

    # Extract answer text
    answer = getattr(response, "generated_answer", None) or str(response)

    # Extract search results for citations / retrieved contexts
    search_results = getattr(response, "search_results", None) or []
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
                "text": getattr(r, "text", "")[:400],
                "score": round(score, 4),
            }
        )

    # Heuristic confidence label (0–1 score scale from R2R)
    # Thresholds: high >= 0.80, medium >= 0.50, low < 0.50 or no results
    top_score = retrieved_contexts[0]["score"] if retrieved_contexts else 0.0
    if top_score >= 0.80:
        confidence_label = "high"
    elif top_score >= 0.50:
        confidence_label = "medium"
    else:
        confidence_label = "low"

    needs_review = confidence_label in ("low", "needs_review")

    return {
        "question": query,
        "answer": answer,
        "citations": citations,
        "retrieved_contexts": retrieved_contexts,
        "confidence_label": confidence_label,
        "needs_human_review": needs_review,
    }


def ingest_file(file_path: str) -> Any:
    """Ingest a single file into R2R. Returns raw SDK response."""
    try:
        client = _client()
        return client.documents.create(file_path=file_path)
    except (httpx.ConnectError, Exception) as exc:
        raise RuntimeError(f"R2R unavailable: {exc}") from exc
