"""Tests for approval policy rules."""
from packages.workflows.approval_policy import confidence_from_contexts, requires_approval


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


class TestConfidenceFromContexts:
    """Test confidence_from_contexts() scoring logic."""

    def test_low_confidence_empty_contexts(self):
        """confidence_from_contexts returns 'low' for empty list."""
        result = confidence_from_contexts([])
        assert result == "low"

    def test_high_confidence_high_score(self):
        """confidence_from_contexts returns 'high' for score >= 0.80."""
        result = confidence_from_contexts([{"score": 0.90}])
        assert result == "high"

    def test_high_confidence_boundary(self):
        """confidence_from_contexts returns 'high' for score == 0.80."""
        result = confidence_from_contexts([{"score": 0.80}])
        assert result == "high"

    def test_medium_confidence_high_threshold(self):
        """confidence_from_contexts returns 'medium' for score >= 0.50 and < 0.80."""
        result = confidence_from_contexts([{"score": 0.75}])
        assert result == "medium"

    def test_medium_confidence_low_threshold(self):
        """confidence_from_contexts returns 'medium' for score == 0.50."""
        result = confidence_from_contexts([{"score": 0.50}])
        assert result == "medium"

    def test_low_confidence_below_threshold(self):
        """confidence_from_contexts returns 'low' for score < 0.50."""
        result = confidence_from_contexts([{"score": 0.49}])
        assert result == "low"

    def test_low_confidence_zero_score(self):
        """confidence_from_contexts returns 'low' for score == 0.0."""
        result = confidence_from_contexts([{"score": 0.0}])
        assert result == "low"

    def test_uses_top_score_only(self):
        """confidence_from_contexts uses only the first (highest) score."""
        result = confidence_from_contexts([
            {"score": 0.90},
            {"score": 0.70},
            {"score": 0.50},
        ])
        assert result == "high"

    def test_handles_missing_score_key(self):
        """confidence_from_contexts handles missing 'score' key gracefully."""
        result = confidence_from_contexts([{"text": "some text"}])
        assert result == "low"
