"""Tests for email draft workflow graph."""
from unittest import mock

import pytest

from packages.workflows.email_draft_graph import run_email_draft


def _make_r2r_response(search_results: list) -> mock.Mock:
    """Build a mock matching the new R2R SDK response shape: response.results.*"""
    resp = mock.Mock()
    resp.results.search_results.chunk_search_results = search_results
    return resp


class TestEmailDraftWorkflow:
    """Test email draft workflow."""

    @mock.patch("packages.workflows.email_draft_graph.R2RClient")
    @mock.patch("packages.workflows.email_draft_graph.ChatGoogleGenerativeAI")
    def test_email_draft_always_requires_approval(self, mock_llm_class, mock_r2r_class):
        """Email draft always returns requires_human_approval=True."""
        mock_search_result = mock.Mock()
        mock_search_result.text = "Policy context"
        mock_search_result.score = 0.85
        mock_search_result.metadata = {"source_file": "policy.pdf"}

        mock_r2r = mock.Mock()
        mock_r2r.retrieval.rag.return_value = _make_r2r_response([mock_search_result])
        mock_r2r_class.return_value = mock_r2r

        mock_llm = mock.Mock()
        mock_llm_response = mock.Mock()
        mock_llm_response.content = "Dear customer,\n\nThank you for your inquiry."
        mock_llm.invoke.return_value = mock_llm_response
        mock_llm_class.return_value = mock_llm

        result = run_email_draft("Draft a reply to customer@example.com")

        assert result["requires_human_approval"] is True
        assert result["final_response"] == "[Awaiting human approval before sending email]"

    @mock.patch("packages.workflows.email_draft_graph.R2RClient")
    @mock.patch("packages.workflows.email_draft_graph.ChatGoogleGenerativeAI")
    def test_email_draft_returns_full_state(self, mock_llm_class, mock_r2r_class):
        """Email draft returns complete workflow state."""
        mock_r2r = mock.Mock()
        mock_r2r.retrieval.rag.return_value = _make_r2r_response([])
        mock_r2r_class.return_value = mock_r2r

        mock_llm = mock.Mock()
        mock_llm_response = mock.Mock()
        mock_llm_response.content = "Draft email body"
        mock_llm.invoke.return_value = mock_llm_response
        mock_llm_class.return_value = mock_llm

        result = run_email_draft("Write a reply")

        assert "customer_message" in result
        assert "intent" in result
        assert "draft_response" in result
        assert "citations" in result
        assert "confidence_label" in result
        assert "requires_human_approval" in result
        assert "final_response" in result

    @mock.patch("packages.workflows.email_draft_graph.R2RClient")
    @mock.patch("packages.workflows.email_draft_graph.ChatGoogleGenerativeAI")
    def test_email_draft_r2r_connection_failure(self, mock_llm_class, mock_r2r_class):
        """Email draft handles R2R connection errors gracefully."""
        import httpx

        mock_r2r = mock.Mock()
        mock_r2r.retrieval.rag.side_effect = httpx.ConnectError("Connection failed")
        mock_r2r_class.return_value = mock_r2r

        mock_llm = mock.Mock()
        mock_llm_response = mock.Mock()
        mock_llm_response.content = "Draft"
        mock_llm.invoke.return_value = mock_llm_response
        mock_llm_class.return_value = mock_llm

        result = run_email_draft("Draft a reply")

        assert result["requires_human_approval"] is True
        assert result["retrieved_contexts"] == []
