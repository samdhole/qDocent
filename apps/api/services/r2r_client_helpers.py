# pattern: Functional Core
"""Pure function helpers for R2R client."""
import logging
from typing import Any


def _label_from_score(top_score: float) -> tuple[str, bool]:
    """Pure function to compute confidence label and review flag from a score.

    Thresholds are calibrated for RRF hybrid search with rrf_k=50, where
    the theoretical max score is 1/(1+50) ≈ 0.0196. A score near the max
    indicates the chunk ranked #1 in both full-text and semantic sub-rankings.

    Args:
        top_score: Retrieval score (RRF: ~0–0.02; cosine: 0–1).

    Returns:
        Tuple of (confidence_label, needs_human_review) where:
        - confidence_label: "high" (>= 0.015), "medium" (>= 0.008), or "low" (< 0.008)
        - needs_human_review: True if confidence is "low", False otherwise
    """
    if top_score >= 0.015:
        confidence_label = "high"
    elif top_score >= 0.008:
        confidence_label = "medium"
    else:
        confidence_label = "low"

    needs_review = confidence_label in ("low", "needs_review")

    return confidence_label, needs_review


def _valid_chunks(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter out chunks with missing or empty required fields for citation header embedding.

    Returns:
        List of chunks that have all required fields (text, document_id, source_file) populated.
        Logs a warning if any chunks are filtered out.
    """
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
