"""Business rules for when human approval is required before sending a response.

These are pure functions — no side effects, no LLM calls.
Rules are from packages/workflows/CONTEXT.md invariants.
"""
# pattern: Functional Core
from __future__ import annotations

import re

# Keywords that trigger mandatory human review
_SENSITIVE_TOPICS = re.compile(
    r"\b(refund|discount|legal|pricing exception|account change|crm|email|cancel)\b",
    re.IGNORECASE,
)


def requires_approval(
    *,
    draft_response: str,
    citations: list,
    confidence_label: str,
    proposes_external_action: bool = False,
) -> bool:
    """Return True if the draft requires human approval before sending.

    Rules (from CONTEXT.md):
    1. Proposing external actions (email send, CRM write)
    2. No citation found
    3. Answer involves refunds, discounts, legal, pricing exceptions, or account changes
    4. confidence_label is 'low' or 'needs_review'
    """
    if proposes_external_action:
        return True
    if not citations:
        return True
    if confidence_label in ("low", "needs_review"):
        return True
    if _SENSITIVE_TOPICS.search(draft_response):
        return True
    return False


