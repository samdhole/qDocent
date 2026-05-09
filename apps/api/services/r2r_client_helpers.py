# pattern: Functional Core
"""Pure function helpers for R2R client."""
import logging
from typing import Any


def _label_from_score(top_score: float) -> tuple[str, bool]:
    """Pure function to compute confidence label and review flag from a score.

    Args:
        top_score: Float between 0–1 representing retrieval confidence.

    Returns:
        Tuple of (confidence_label, needs_human_review) where:
        - confidence_label: "high" (>= 0.80), "medium" (>= 0.50), or "low" (< 0.50)
        - needs_human_review: True if confidence is "low", False otherwise
    """
    if top_score >= 0.80:
        confidence_label = "high"
    elif top_score >= 0.50:
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
