"""Tests for support triage workflow graph components."""
import pytest

from packages.workflows.approval_policy import confidence_from_contexts, requires_approval


class TestTriageApprovalLogic:
    """Test the approval logic used by support triage workflow."""

    def test_refund_keyword_requires_approval(self):
        """Messages containing 'refund' trigger approval requirement."""
        result = requires_approval(
            draft_response="We can approve a refund for you.",
            citations=[{"chunk_id": "1"}],
            confidence_label="high",
        )
        assert result is True

    def test_discount_keyword_requires_approval(self):
        """Messages containing 'discount' trigger approval requirement."""
        result = requires_approval(
            draft_response="We can offer a discount.",
            citations=[{"chunk_id": "1"}],
            confidence_label="high",
        )
        assert result is True

    def test_empty_contexts_requires_approval(self):
        """No contexts means approval is required."""
        result = requires_approval(
            draft_response="General answer.",
            citations=[],
            confidence_label="high",
        )
        assert result is True

    def test_low_confidence_requires_approval(self):
        """Low confidence triggers approval requirement."""
        confidence = confidence_from_contexts([{"score": 0.30}])
        assert confidence == "low"

        result = requires_approval(
            draft_response="Some answer.",
            citations=[{"chunk_id": "1"}],
            confidence_label=confidence,
        )
        assert result is True

    def test_clean_high_confidence_no_approval(self):
        """Clean high-confidence answer does not require approval."""
        result = requires_approval(
            draft_response="Office hours are 9am to 5pm.",
            citations=[{"chunk_id": "1"}],
            confidence_label="high",
        )
        assert result is False
