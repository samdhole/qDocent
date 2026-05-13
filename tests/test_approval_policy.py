"""Tests for approval policy rules."""
from packages.workflows.approval_policy import requires_approval


class TestRequiresApproval:
    """Test requires_approval() business logic."""

    def test_requires_approval_no_citations(self):
        """requires_approval returns True when citations list is empty."""
        result = requires_approval(
            draft_response="Here is the refund info.",
            citations=[],
            confidence_label="high",
        )
        assert result is True

    def test_requires_approval_sensitive_topic_refund(self):
        """requires_approval returns True when draft mentions refund."""
        result = requires_approval(
            draft_response="We can offer a refund.",
            citations=[{"chunk_id": "1"}],
            confidence_label="high",
        )
        assert result is True

    def test_requires_approval_sensitive_topic_discount(self):
        """requires_approval returns True when draft mentions discount."""
        result = requires_approval(
            draft_response="We can offer a discount on your plan.",
            citations=[{"chunk_id": "1"}],
            confidence_label="high",
        )
        assert result is True

    def test_requires_approval_sensitive_topic_pricing(self):
        """requires_approval returns True when draft mentions pricing exception."""
        result = requires_approval(
            draft_response="This is a pricing exception case.",
            citations=[{"chunk_id": "1"}],
            confidence_label="high",
        )
        assert result is True

    def test_requires_approval_sensitive_topic_legal(self):
        """requires_approval returns True when draft mentions legal."""
        result = requires_approval(
            draft_response="This is a legal matter.",
            citations=[{"chunk_id": "1"}],
            confidence_label="high",
        )
        assert result is True

    def test_requires_approval_low_confidence(self):
        """requires_approval returns True when confidence_label is 'low'."""
        result = requires_approval(
            draft_response="The office opens at 9am.",
            citations=[{"chunk_id": "1"}],
            confidence_label="low",
        )
        assert result is True

    def test_requires_approval_needs_review_confidence(self):
        """requires_approval returns True when confidence_label is 'needs_review'."""
        result = requires_approval(
            draft_response="The office opens at 9am.",
            citations=[{"chunk_id": "1"}],
            confidence_label="needs_review",
        )
        assert result is True

    def test_requires_approval_external_action(self):
        """requires_approval returns True when proposes_external_action is True."""
        result = requires_approval(
            draft_response="The office opens at 9am.",
            citations=[{"chunk_id": "1"}],
            confidence_label="high",
            proposes_external_action=True,
        )
        assert result is True

    def test_no_approval_needed_clean_high_confidence(self):
        """requires_approval returns False for clean high-confidence answers."""
        result = requires_approval(
            draft_response="The office opens at 9am.",
            citations=[{"chunk_id": "1"}],
            confidence_label="high",
        )
        assert result is False

    def test_no_approval_needed_medium_confidence(self):
        """requires_approval returns False for medium confidence without sensitive topics."""
        result = requires_approval(
            draft_response="Our office hours are 9am to 5pm.",
            citations=[{"chunk_id": "1"}],
            confidence_label="medium",
        )
        assert result is False


