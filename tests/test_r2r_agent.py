"""Tests for R2R agent service (conversation-aware queries)."""
import json
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
                # Create a fake agent response matching actual spike shape:
                # aggregated_search_result is a JSON string, not a dict
                mock_message = mock.MagicMock()
                mock_message.content = "The policy is 30 days."
                mock_message.metadata = {
                    "citations": [],
                    "aggregated_search_result": json.dumps({
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
                    })
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
                    "aggregated_search_result": json.dumps({"chunk_search_results": []})
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
                    "aggregated_search_result": json.dumps({"chunk_search_results": []})
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

    def test_agent_query_handles_empty_list_from_json_parse(self):
        """agent_query() handles when json.loads returns a list (e.g., '[]')."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory:
            with mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures:
                # This is the critical C1 scenario: aggregated_search_result is "[]" string
                # which parses to a Python list, not a dict
                mock_message = mock.MagicMock()
                mock_message.content = "Please specify which document you are referring to."
                mock_message.metadata = {
                    "citations": [],
                    "aggregated_search_result": "[]"  # Empty array JSON string
                }

                mock_response = mock.MagicMock()
                mock_response.results.messages = [mock_message]
                mock_response.results.conversation_id = "conv-empty"

                mock_client_factory.return_value.retrieval.agent.return_value = mock_response
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_query

                result = agent_query("What does the document say?", "conv-empty")

                assert result["answer"] == "Please specify which document you are referring to."
                assert result["citations"] == []
                assert result["retrieved_contexts"] == []
                assert result["conversation_id"] == "conv-empty"

    def test_agent_query_handles_dict_response_shape(self):
        """agent_query() extracts from plain dict response (no .results attribute)."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory:
            with mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures:
                # Return a plain dict instead of an object with .results attribute
                response_dict = {
                    "results": {
                        "messages": [
                            {
                                "content": "The answer is here.",
                                "metadata": {
                                    "aggregated_search_result": json.dumps({
                                        "chunk_search_results": [
                                            {
                                                "text": "DocQuery Citation: document_id=doc2; source_file=guide.pdf; page_start=5; page_end=5; section_path=Overview; chunk_index=0\n\nGuide text",
                                                "metadata": {
                                                    "chunk_id": "chunk-2",
                                                    "source_file": "guide.pdf",
                                                    "page_start": 5,
                                                },
                                                "score": 0.92,
                                                "id": "chunk-2",
                                            }
                                        ]
                                    })
                                }
                            }
                        ],
                        "conversation_id": "conv-dict"
                    }
                }

                mock_client_factory.return_value.retrieval.agent.return_value = response_dict
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_query

                result = agent_query("What is the guide?", "conv-dict")

                assert result["answer"] == "The answer is here."
                assert len(result["citations"]) == 1
                assert result["citations"][0]["document"] == "guide.pdf"
                assert result["conversation_id"] == "conv-dict"
