"""Tests for support triage workflow graph."""
from unittest import mock

import pytest

from packages.workflows.support_triage_graph import run_support_triage

_HIGH_CONFIDENCE_RESULT = {
    "retrieved_contexts": [{"chunk_id": "chunk_1", "text": "Policy text.", "score": 0.90}],
    "citations": [{"document": "policy.pdf", "page": 1, "chunk_id": "chunk_1"}],
    "answer": "We will process your refund within 30 days of purchase.",
    "confidence_label": "high",
}

_NO_CONTEXT_RESULT = {
    "retrieved_contexts": [],
    "citations": [],
    "answer": "",
    "confidence_label": "low",
}


class TestSupportTriageWorkflow:
    """Test support triage workflow graph execution."""

    @mock.patch("packages.workflows.support_triage_graph.r2r_client.rag_query")
    @mock.patch("packages.workflows.support_triage_graph.ChatGoogleGenerativeAI")
    def test_support_triage_returns_full_state(self, mock_llm_class, mock_rag_query):
        """run_support_triage returns dict with all 8 SupportState fields."""
        mock_rag_query.return_value = _HIGH_CONFIDENCE_RESULT

        result = run_support_triage("I need a refund")

        assert isinstance(result, dict)
        assert "customer_message" in result
        assert "intent" in result
        assert "retrieved_contexts" in result
        assert "draft_response" in result
        assert "citations" in result
        assert "confidence_label" in result
        assert "requires_human_approval" in result
        assert "final_response" in result

        # Refund is a sensitive topic — approval required; final_response is the draft
        assert result["requires_human_approval"] is True
        assert result["final_response"] == _HIGH_CONFIDENCE_RESULT["answer"]

    @mock.patch("packages.workflows.support_triage_graph.r2r_client.rag_query")
    @mock.patch("packages.workflows.support_triage_graph.ChatGoogleGenerativeAI")
    def test_support_triage_refund_requires_approval(self, mock_llm_class, mock_rag_query):
        """Refund requests trigger requires_human_approval; final_response is the draft."""
        mock_rag_query.return_value = {
            "retrieved_contexts": [{"chunk_id": "c1", "text": "Refund policy info", "score": 0.90}],
            "citations": [{"document": "policy.pdf", "page": 1, "chunk_id": "c1"}],
            "answer": "We offer a refund within 30 days.",
            "confidence_label": "high",
        }

        result = run_support_triage("I need a refund")

        assert result["requires_human_approval"] is True
        assert result["final_response"] == "We offer a refund within 30 days."

    @mock.patch("packages.workflows.support_triage_graph.r2r_client.rag_query")
    @mock.patch("packages.workflows.support_triage_graph.ChatGoogleGenerativeAI")
    def test_support_triage_high_confidence_clean_no_approval(self, mock_llm_class, mock_rag_query):
        """Clean high-confidence answer does not require approval; final_response is the draft."""
        mock_rag_query.return_value = {
            "retrieved_contexts": [{"chunk_id": "c2", "text": "Business hours info", "score": 0.92}],
            "citations": [{"document": "info.pdf", "page": 1, "chunk_id": "c2"}],
            "answer": "Our office hours are 9am to 5pm Monday through Friday.",
            "confidence_label": "high",
        }
        mock_llm = mock.Mock()
        mock_llm.invoke.return_value.content = "general"
        mock_llm_class.return_value = mock_llm

        result = run_support_triage("What are your business hours?")

        assert result["requires_human_approval"] is False
        assert "9am to 5pm" in result["final_response"]

    @mock.patch("packages.workflows.support_triage_graph.r2r_client.rag_query")
    @mock.patch("packages.workflows.support_triage_graph.ChatGoogleGenerativeAI")
    def test_support_triage_no_contexts_requires_approval(self, mock_llm_class, mock_rag_query):
        """No retrieved contexts triggers approval requirement; final_response is empty draft."""
        mock_rag_query.return_value = _NO_CONTEXT_RESULT

        result = run_support_triage("What is your policy on something unusual?")

        assert result["requires_human_approval"] is True
        assert result["confidence_label"] == "low"
        # final_response is the (empty) draft — no placeholder string
        assert result["final_response"] == ""

    @mock.patch("packages.workflows.support_triage_graph.r2r_client.rag_query")
    @mock.patch("packages.workflows.support_triage_graph.ChatGoogleGenerativeAI")
    def test_support_triage_r2r_failure_graceful(self, mock_llm_class, mock_rag_query):
        """Support triage handles R2R connection failures gracefully."""
        mock_rag_query.side_effect = RuntimeError("R2R unavailable")

        result = run_support_triage("Can I get a discount?")

        assert result["retrieved_contexts"] == []
        assert result["citations"] == []
        assert result["confidence_label"] == "low"
        assert result["requires_human_approval"] is True
