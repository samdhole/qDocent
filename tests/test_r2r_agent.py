"""Tests for R2R agent service (conversation-aware queries)."""
from unittest import mock

import pytest


class TestCreateConversation:
    """Test conversation creation."""

    def test_create_conversation_returns_id(self):
        """create_conversation() returns conversation ID from R2R response."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory:
            mock_response = mock.MagicMock()
            mock_response.results.id = "conv-1"
            mock_client_factory.return_value.conversations.create.return_value = mock_response

            from apps.api.services.r2r_agent import create_conversation

            result = create_conversation()

            assert result == "conv-1"

    def test_create_conversation_raises_when_r2r_down(self):
        """create_conversation() raises RuntimeError with R2R unavailable message."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory:
            import httpx

            mock_client_factory.return_value.conversations.create.side_effect = (
                httpx.ConnectError("Connection failed")
            )

            from apps.api.services.r2r_agent import create_conversation

            with pytest.raises(RuntimeError, match="R2R unavailable"):
                create_conversation()


class TestAgentQuery:
    """Test agent query and response adaptation."""

    def test_agent_query_extracts_answer_and_citations(self):
        """agent_query() extracts answer, citations, and retrieved_contexts from agent response."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory:
            with mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures:
                # Create a fake agent response
                mock_message = mock.MagicMock()
                mock_message.content = "The policy is 30 days."
                mock_message.metadata = {
                    "aggregated_search_results": {
                        "chunk_search_results": [
                            {
                                "text": "DocQuery Citation: document_id=doc1; source_file=policy.pdf; page_start=1; page_end=1; section_path=Refunds; chunk_index=0\n\nRefund policy details",
                                "metadata": {
                                    "chunk_id": "chunk-1",
                                    "source_file": "policy.pdf",
                                    "page_start": 1,
                                },
                                "score": 0.85,
                                "id": "chunk-1",
                            }
                        ]
                    }
                }

                mock_response = mock.MagicMock()
                mock_response.results.messages = [mock_message]
                mock_response.results.conversation_id = "conv-1"

                mock_client_factory.return_value.retrieval.agent.return_value = mock_response
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_query

                result = agent_query("What is the refund policy?", "conv-1")

                assert result["answer"] == "The policy is 30 days."
                assert len(result["citations"]) == 1
                assert result["citations"][0]["document_id"] == "doc1"
                assert result["citations"][0]["document"] == "policy.pdf"
                assert result["conversation_id"] == "conv-1"
                assert len(result["retrieved_contexts"]) == 1
                assert "Refund policy details" in result["retrieved_contexts"][0]["text"]

    def test_agent_query_returns_conversation_id(self):
        """agent_query() includes conversation_id in response dict."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory:
            with mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures:
                mock_message = mock.MagicMock()
                mock_message.content = "Answer"
                mock_message.metadata = {
                    "aggregated_search_results": {"chunk_search_results": []}
                }

                mock_response = mock.MagicMock()
                mock_response.results.messages = [mock_message]
                mock_response.results.conversation_id = "conv-abc-123"

                mock_client_factory.return_value.retrieval.agent.return_value = mock_response
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_query

                result = agent_query("question", "conv-abc-123")

                assert result["conversation_id"] == "conv-abc-123"

    def test_agent_query_handles_no_chunks(self):
        """agent_query() handles empty chunk_search_results gracefully."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory:
            with mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures:
                mock_message = mock.MagicMock()
                mock_message.content = "I don't have enough information."
                mock_message.metadata = {
                    "aggregated_search_results": {"chunk_search_results": []}
                }

                mock_response = mock.MagicMock()
                mock_response.results.messages = [mock_message]
                mock_response.results.conversation_id = "conv-1"

                mock_client_factory.return_value.retrieval.agent.return_value = mock_response
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_query

                result = agent_query("question", "conv-1")

                assert result["citations"] == []
                assert result["retrieved_contexts"] == []
                assert result["confidence_label"] == "low"
                assert result["needs_human_review"] is True
