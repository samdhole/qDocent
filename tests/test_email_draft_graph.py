"""Tests for email draft workflow graph."""
from unittest import mock

import pytest

from packages.workflows.email_draft_graph import run_email_draft

_POLICY_RESULT = {
    "retrieved_contexts": [{"chunk_id": "c1", "text": "Refunds are available within 30 days of purchase.", "score": 0.86}],
    "citations": [{"document": "policy.pdf", "page": 1, "chunk_id": "c1"}],
    "answer": "",
    "confidence_label": "high",
}

_EMPTY_RESULT = {
    "retrieved_contexts": [],
    "citations": [],
    "answer": "",
    "confidence_label": "low",
}


class TestEmailDraftWorkflow:
    """Test email draft workflow."""

    @mock.patch("packages.workflows.email_draft_graph.r2r_client.rag_query")
    @mock.patch("packages.workflows.email_draft_graph.ChatGoogleGenerativeAI")
    def test_email_draft_without_api_key_uses_deterministic_fallback(
        self,
        mock_llm_class,
        mock_rag_query,
        monkeypatch,
    ):
        """Email draft remains demoable without a Gemini API key."""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        mock_rag_query.return_value = _POLICY_RESULT

        result = run_email_draft("Please draft a refund reply")

        mock_llm_class.assert_not_called()
        assert "Subject:" in result["draft_response"]
        assert "Please draft a refund reply" in result["draft_response"]
        assert "30 days" in result["draft_response"]
        assert result["requires_human_approval"] is True
        # final_response is the draft — no placeholder string
        assert result["final_response"] == result["draft_response"]

    @mock.patch("packages.workflows.email_draft_graph.r2r_client.rag_query")
    @mock.patch("packages.workflows.email_draft_graph.ChatGoogleGenerativeAI")
    def test_email_draft_always_requires_approval(self, mock_llm_class, mock_rag_query):
        """Email draft always returns requires_human_approval=True; final_response is the draft."""
        mock_rag_query.return_value = _POLICY_RESULT
        mock_llm = mock.Mock()
        mock_llm.invoke.return_value.content = "Dear customer,\n\nThank you for your inquiry."
        mock_llm_class.return_value = mock_llm

        result = run_email_draft("Draft a reply to customer@example.com")

        assert result["requires_human_approval"] is True
        assert result["final_response"] == result["draft_response"]
        assert result["final_response"] != ""

    @mock.patch("packages.workflows.email_draft_graph.r2r_client.rag_query")
    @mock.patch("packages.workflows.email_draft_graph.ChatGoogleGenerativeAI")
    def test_email_draft_returns_full_state(self, mock_llm_class, mock_rag_query):
        """Email draft returns complete workflow state."""
        mock_rag_query.return_value = _EMPTY_RESULT
        mock_llm = mock.Mock()
        mock_llm.invoke.return_value.content = "Draft email body"
        mock_llm_class.return_value = mock_llm

        result = run_email_draft("Write a reply")

        assert "customer_message" in result
        assert "intent" in result
        assert "draft_response" in result
        assert "citations" in result
        assert "confidence_label" in result
        assert "requires_human_approval" in result
        assert "final_response" in result

    @mock.patch("packages.workflows.email_draft_graph.r2r_client.rag_query")
    @mock.patch("packages.workflows.email_draft_graph.ChatGoogleGenerativeAI")
    def test_email_draft_r2r_connection_failure(self, mock_llm_class, mock_rag_query):
        """Email draft handles R2R connection errors gracefully."""
        mock_rag_query.side_effect = RuntimeError("R2R unavailable")
        mock_llm = mock.Mock()
        mock_llm.invoke.return_value.content = "Draft"
        mock_llm_class.return_value = mock_llm

        result = run_email_draft("Draft a reply")

        assert result["requires_human_approval"] is True
        assert result["retrieved_contexts"] == []
