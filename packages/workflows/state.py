"""Shared state type for all workflow graphs."""
# pattern: Functional Core
from typing import Any, TypedDict


class SupportState(TypedDict):
    customer_message: str
    intent: str
    retrieved_contexts: list[dict[str, Any]]
    draft_response: str
    citations: list[dict[str, Any]]
    confidence_label: str          # high | medium | low | needs_review
    requires_human_approval: bool
    final_response: str
