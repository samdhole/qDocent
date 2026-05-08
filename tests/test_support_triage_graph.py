"""Tests for support triage workflow graph."""
from unittest import mock

import pytest

from packages.workflows.support_triage_graph import run_support_triage


class TestSupportTriageWorkflow:
    """Test support triage workflow graph execution."""

    @mock.patch("packages.workflows.support_triage_graph.R2RClient")
    @mock.patch("packages.workflows.support_triage_graph.ChatOpenAI")
    def test_support_triage_returns_full_state(self, mock_llm_class, mock_r2r_class):
        """run_support_triage returns dict with all 8 SupportState fields."""
        # Mock R2R response
        mock_response = mock.Mock()
        mock_search_result = mock.Mock()
        mock_search_result.id = "chunk_1"
        mock_search_result.text = "Return policy: items can be returned within 30 days."
        mock_search_result.score = 0.85
        mock_search_result.metadata = {"source_file": "policy.pdf", "page_start": 1}

        mock_response.search_results = [mock_search_result]
        mock_response.generated_answer = "Items can be returned within 30 days of purchase."

        mock_r2r = mock.Mock()
        mock_r2r.retrieval.rag.return_value = mock_response
        mock_r2r_class.return_value = mock_r2r

        # Mock LLM (for classify_intent fallback, not needed here due to rule match)
        mock_llm = mock.Mock()
        mock_llm_class.return_value = mock_llm

        result = run_support_triage("I need a refund")

        # Verify all 8 state fields are present
        assert isinstance(result, dict)
        assert "customer_message" in result
        assert "intent" in result
        assert "retrieved_contexts" in result
        assert "draft_response" in result
        assert "citations" in result
        assert "confidence_label" in result
        assert "requires_human_approval" in result
        assert "final_response" in result

        # Verify refund triggers approval
        assert result["requires_human_approval"] is True
        assert result["final_response"] == "[Awaiting human approval]"

    @mock.patch("packages.workflows.support_triage_graph.R2RClient")
    @mock.patch("packages.workflows.support_triage_graph.ChatOpenAI")
    def test_support_triage_refund_requires_approval(self, mock_llm_class, mock_r2r_class):
        """Refund requests trigger requires_human_approval."""
        mock_response = mock.Mock()
        mock_search_result = mock.Mock()
        mock_search_result.id = "chunk_1"
        mock_search_result.text = "Refund policy information"
        mock_search_result.score = 0.90
        mock_search_result.metadata = {"source_file": "policy.pdf", "page_start": 1}

        mock_response.search_results = [mock_search_result]
        mock_response.generated_answer = "We offer refunds within 30 days."

        mock_r2r = mock.Mock()
        mock_r2r.retrieval.rag.return_value = mock_response
        mock_r2r_class.return_value = mock_r2r

        mock_llm = mock.Mock()
        mock_llm_class.return_value = mock_llm

        result = run_support_triage("I need a refund")

        # Refund keyword → approval required
        assert result["requires_human_approval"] is True
        assert result["final_response"] == "[Awaiting human approval]"

    @mock.patch("packages.workflows.support_triage_graph.R2RClient")
    @mock.patch("packages.workflows.support_triage_graph.ChatOpenAI")
    def test_support_triage_high_confidence_clean_no_approval(self, mock_llm_class, mock_r2r_class):
        """Clean high-confidence answer does not require approval."""
        mock_response = mock.Mock()
        mock_search_result = mock.Mock()
        mock_search_result.id = "chunk_2"
        mock_search_result.text = "Business hours are 9am to 5pm Monday through Friday."
        mock_search_result.score = 0.92
        mock_search_result.metadata = {"source_file": "info.pdf", "page_start": 1}

        mock_response.search_results = [mock_search_result]
        mock_response.generated_answer = "Our office hours are 9am to 5pm Monday through Friday."

        mock_r2r = mock.Mock()
        mock_r2r.retrieval.rag.return_value = mock_response
        mock_r2r_class.return_value = mock_r2r

        mock_llm = mock.Mock()
        mock_llm_class.return_value = mock_llm

        result = run_support_triage("What are your business hours?")

        # High confidence + no sensitive keywords → no approval needed
        assert result["requires_human_approval"] is False
        assert result["final_response"] != "[Awaiting human approval]"
        assert "9am to 5pm" in result["final_response"]

    @mock.patch("packages.workflows.support_triage_graph.R2RClient")
    @mock.patch("packages.workflows.support_triage_graph.ChatOpenAI")
    def test_support_triage_no_contexts_requires_approval(self, mock_llm_class, mock_r2r_class):
        """No retrieved contexts triggers approval requirement."""
        mock_response = mock.Mock()
        mock_response.search_results = []
        mock_response.generated_answer = ""

        mock_r2r = mock.Mock()
        mock_r2r.retrieval.rag.return_value = mock_response
        mock_r2r_class.return_value = mock_r2r

        mock_llm = mock.Mock()
        mock_llm_class.return_value = mock_llm

        result = run_support_triage("What is your policy on something unusual?")

        # No contexts + low confidence → approval required
        assert result["requires_human_approval"] is True
        assert result["final_response"] == "[Awaiting human approval]"
        assert result["confidence_label"] == "low"

    @mock.patch("packages.workflows.support_triage_graph.R2RClient")
    @mock.patch("packages.workflows.support_triage_graph.ChatOpenAI")
    def test_support_triage_r2r_failure_graceful(self, mock_llm_class, mock_r2r_class):
        """Support triage handles R2R connection failures gracefully."""
        import httpx

        mock_r2r = mock.Mock()
        mock_r2r.retrieval.rag.side_effect = httpx.ConnectError("Connection failed")
        mock_r2r_class.return_value = mock_r2r

        mock_llm = mock.Mock()
        mock_llm_class.return_value = mock_llm

        result = run_support_triage("Can I get a discount?")

        # Graceful failure: no contexts → low confidence → approval required
        assert result["retrieved_contexts"] == []
        assert result["citations"] == []
        assert result["confidence_label"] == "low"
        assert result["requires_human_approval"] is True
