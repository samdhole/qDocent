# pattern: Functional Core
"""Pure function: rewrite R2R [shortid] markers → ordered [N] in answer text."""
from __future__ import annotations

import re
from typing import Any

_SHORTID_RE = re.compile(r"\[([0-9a-f]{6,8})\]")


def _shortid_from_chunk_id(chunk_id: str) -> str:
    """Derive the 7-char hex shortid R2R embeds in answer text from a full chunk UUID."""
    return chunk_id.replace("-", "")[:7]


def rewrite_brackets(
    answer: str,
    citations: list[dict[str, Any]],
    retrieved_contexts: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    """Replace [shortid] markers with [N]; reorder citations and retrieved_contexts in lockstep.

    - Known shortids → [N] (1-based, prose-order).
    - Unknown shortids pass through unchanged.
    - Empty citations → no-op, returns inputs unchanged.
    - Uses chunk_id-keyed lookup for retrieved_contexts (not positional) to handle
      the known_citations filter in r2r_agent that may have already shortened citations
      relative to retrieved_contexts.
    """
    if not citations:
        return answer, citations, retrieved_contexts

    # Build shortid → original-index map from citations
    shortid_to_orig_idx: dict[str, int] = {}
    for i, citation in enumerate(citations):
        cid = citation.get("chunk_id") or ""
        if cid:
            shortid_to_orig_idx[_shortid_from_chunk_id(cid)] = i

    # First pass: collect cited citations in first-seen prose order
    prose_order: list[int] = []  # original indices, first-seen order
    seen: set[int] = set()
    for m in _SHORTID_RE.finditer(answer):
        orig_idx = shortid_to_orig_idx.get(m.group(1))
        if orig_idx is not None and orig_idx not in seen:
            prose_order.append(orig_idx)
            seen.add(orig_idx)

    # Uncited citations appended at end in original relevance order
    uncited = [i for i in range(len(citations)) if i not in seen]
    new_order = prose_order + uncited

    # Build shortid → "[N]" replacement map for cited chunks only
    shortid_to_n: dict[str, str] = {}
    for new_idx, orig_idx in enumerate(new_order, start=1):
        if orig_idx in seen:
            cid = citations[orig_idx].get("chunk_id") or ""
            if cid:
                shortid_to_n[_shortid_from_chunk_id(cid)] = f"[{new_idx}]"

    def _replace(m: re.Match) -> str:  # type: ignore[type-arg]
        return shortid_to_n.get(m.group(1), m.group(0))

    rewritten = _SHORTID_RE.sub(_replace, answer)
    reordered_citations = [citations[i] for i in new_order]

    # Align retrieved_contexts by chunk_id (robust to pre-filter length mismatch)
    ctx_by_chunk_id: dict[str, dict[str, Any]] = {
        ctx["chunk_id"]: ctx
        for ctx in retrieved_contexts
        if ctx.get("chunk_id")
    }
    _empty_ctx: dict[str, Any] = {"chunk_id": None, "text": "", "score": 0.0}
    reordered_contexts = [
        ctx_by_chunk_id.get(citations[i].get("chunk_id") or "", _empty_ctx)
        for i in new_order
    ]

    return rewritten, reordered_citations, reordered_contexts
