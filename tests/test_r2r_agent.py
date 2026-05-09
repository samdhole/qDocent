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
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
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
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
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
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
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
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
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
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
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

    def test_agent_query_includes_chunk_index_from_header(self):
        """Task 1: chunk_index from DocQuery citation header is included in citations."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                mock_message = mock.MagicMock()
                mock_message.content = "The policy is 30 days."
                mock_message.metadata = {
                    "citations": [],
                    "aggregated_search_result": json.dumps({
                        "chunk_search_results": [
                            {
                                "text": "DocQuery Citation: document_id=doc1; source_file=policy.pdf; page_start=1; page_end=1; section_path=Refunds; chunk_index=5\n\nRefund policy details",
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
                assert result["citations"][0]["chunk_index"] == 5


class MessageEvent:
    """Fake MessageEvent for testing agent_stream."""

    def __init__(self, text):
        self._text = text

    def model_dump(self):
        return {"data": {"delta": {"content": [{"payload": {"value": self._text}}]}}}


class SearchResultsEvent:
    """Fake SearchResultsEvent for testing agent_stream."""

    def __init__(self, chunk_search_results=None):
        self._results = chunk_search_results or []

    def model_dump(self):
        return {"data": {"chunk_search_results": self._results}}


class FinalAnswerEvent:
    """Fake FinalAnswerEvent for testing agent_stream."""

    def __init__(self, generated_answer=None, conversation_id=None):
        self._answer = generated_answer
        self._conv_id = conversation_id

    def model_dump(self):
        return {
            "data": {
                "generated_answer": self._answer,
                "conversation_id": self._conv_id,
            }
        }


class CitationEvent:
    """Fake CitationEvent for testing agent_stream."""

    def __init__(self):
        pass

    def model_dump(self):
        return {"data": {}}


class TestDocOnly:
    """Test doc_only post-hoc check for strict document-only mode."""

    def test_ac3_2_doc_only_empty_retrieval(self):
        """AC3.2: doc_only=True with empty retrieval → "I couldn't find this in your documents." + low confidence."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                # Empty chunk results — LLM still tries to answer from knowledge
                mock_message = mock.MagicMock()
                mock_message.content = "Based on my knowledge, the refund period is 30 days."
                mock_message.metadata = {
                    "aggregated_search_result": json.dumps({"chunk_search_results": []})
                }

                mock_response = mock.MagicMock()
                mock_response.results.messages = [mock_message]
                mock_response.results.conversation_id = "conv-1"

                mock_client_factory.return_value.retrieval.agent.return_value = mock_response
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_query

                result = agent_query("What is the refund policy?", "conv-1", doc_only=True)

                # Post-hoc check should replace LLM answer with strict not-found string
                assert result["answer"] == "I couldn't find this in your documents."
                assert result["confidence_label"] == "low"
                assert result["needs_human_review"] is True
                assert result["doc_only_not_found"] is True

    def test_ac3_3_doc_only_low_score_chunk(self):
        """AC3.3: doc_only=True with low-score chunk (score < 0.50) → strict not-found string."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                # Single low-score chunk (score 0.3 < 0.50 threshold)
                mock_message = mock.MagicMock()
                mock_message.content = "The policy might be related to refunds."
                mock_message.metadata = {
                    "aggregated_search_result": json.dumps({
                        "chunk_search_results": [
                            {
                                "text": "DocQuery Citation: document_id=doc1; source_file=policy.pdf; page_start=1; page_end=1; section_path=Overview; chunk_index=0\n\nGeneric text about policies",
                                "metadata": {
                                    "chunk_id": "chunk-1",
                                    "source_file": "policy.pdf",
                                    "page_start": 1,
                                },
                                "score": 0.3,  # Below 0.50 threshold → confidence_label="low"
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

                result = agent_query("What is the refund policy?", "conv-1", doc_only=True)

                # Even though we have a chunk, confidence is low, so post-hoc check triggers
                assert result["answer"] == "I couldn't find this in your documents."
                assert result["confidence_label"] == "low"
                assert result["needs_human_review"] is True
                assert result["doc_only_not_found"] is True

    def test_ac3_4_doc_only_high_score_chunk(self):
        """AC3.4: doc_only=True with high-score chunk (score >= 0.80) → original LLM answer unchanged."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                # High-score chunk (score 0.85 >= 0.80) → confidence_label="high"
                mock_message = mock.MagicMock()
                mock_message.content = "The refund policy is 30 days."
                mock_message.metadata = {
                    "aggregated_search_result": json.dumps({
                        "chunk_search_results": [
                            {
                                "text": "DocQuery Citation: document_id=doc1; source_file=policy.pdf; page_start=1; page_end=1; section_path=Refunds; chunk_index=0\n\nRefund policy details: 30 days",
                                "metadata": {
                                    "chunk_id": "chunk-1",
                                    "source_file": "policy.pdf",
                                    "page_start": 1,
                                },
                                "score": 0.85,  # Above 0.80 threshold → confidence_label="high"
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

                result = agent_query("What is the refund policy?", "conv-1", doc_only=True)

                # High confidence + doc_only=True → post-hoc check does NOT trigger, original answer preserved
                assert result["answer"] == "The refund policy is 30 days."
                assert result["confidence_label"] == "high"
                assert result["needs_human_review"] is False
                # doc_only_not_found should not be set (or be False/absent)
                assert not result.get("doc_only_not_found")

    def test_ac3_5_doc_only_false_empty_retrieval(self):
        """AC3.5: doc_only=False (general mode) with empty retrieval → original LLM answer (no substitution)."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                # Empty retrieval, but doc_only=False → LLM can answer from knowledge
                mock_message = mock.MagicMock()
                mock_message.content = "Based on general knowledge, refund periods vary by industry."
                mock_message.metadata = {
                    "aggregated_search_result": json.dumps({"chunk_search_results": []})
                }

                mock_response = mock.MagicMock()
                mock_response.results.messages = [mock_message]
                mock_response.results.conversation_id = "conv-1"

                mock_client_factory.return_value.retrieval.agent.return_value = mock_response
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_query

                result = agent_query("What is the refund policy?", "conv-1", doc_only=False)

                # No post-hoc substitution — doc_only=False means general mode
                assert result["answer"] == "Based on general knowledge, refund periods vary by industry."
                assert result["confidence_label"] == "low"  # Still low because no retrieval
                assert result["needs_human_review"] is True  # Still needs review due to low confidence
                # doc_only_not_found should not be set in general mode
                assert not result.get("doc_only_not_found")

    def test_ac3_2_doc_only_stream_empty_retrieval(self):
        """AC3.2 stream path: doc_only=True with empty retrieval → not-found string + low confidence."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                # Empty retrieval via streaming — LLM tries to answer from knowledge
                events = [
                    SearchResultsEvent([]),  # Empty retrieval
                    MessageEvent("Based on my knowledge, the refund period is 30 days."),
                    FinalAnswerEvent("Based on my knowledge, the refund period is 30 days.", "conv-1"),
                ]
                mock_client_factory.return_value.retrieval.agent.return_value = iter(events)
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_stream

                frames = list(agent_stream("What is the refund policy?", "conv-1", doc_only=True))

                # Extract final frame
                final_frames = [
                    json.loads(f.split("data: ")[1])
                    for f in frames
                    if "data: " in f and json.loads(f.split("data: ")[1]).get("type") == "final"
                ]

                assert len(final_frames) == 1
                result = final_frames[0]["result"]
                # Post-hoc check should replace LLM answer with strict not-found string
                assert result["answer"] == "I couldn't find this in your documents."
                assert result["confidence_label"] == "low"
                assert result["needs_human_review"] is True
                assert result.get("doc_only_not_found") is True

    def test_ac3_4_doc_only_stream_high_score(self):
        """AC3.4 stream path: doc_only=True with high-score chunk → original LLM answer preserved."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                # High-score chunk via streaming — post-hoc check should NOT trigger
                events = [
                    SearchResultsEvent([
                        {
                            "text": "DocQuery Citation: document_id=doc1; source_file=policy.pdf; page_start=1; page_end=1; section_path=Refunds; chunk_index=0\n\nRefund policy details: 30 days",
                            "metadata": {
                                "chunk_id": "chunk-1",
                                "source_file": "policy.pdf",
                                "page_start": 1,
                            },
                            "score": 0.85,  # High score → confidence_label="high"
                            "id": "chunk-1",
                        }
                    ]),
                    MessageEvent("The refund policy is 30 days."),
                    FinalAnswerEvent("The refund policy is 30 days.", "conv-1"),
                ]
                mock_client_factory.return_value.retrieval.agent.return_value = iter(events)
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_stream

                frames = list(agent_stream("What is the refund policy?", "conv-1", doc_only=True))

                # Extract final frame
                final_frames = [
                    json.loads(f.split("data: ")[1])
                    for f in frames
                    if "data: " in f and json.loads(f.split("data: ")[1]).get("type") == "final"
                ]

                assert len(final_frames) == 1
                result = final_frames[0]["result"]
                # High confidence + doc_only=True → post-hoc check does NOT trigger
                assert result["answer"] == "The refund policy is 30 days."
                assert result["confidence_label"] == "high"
                assert result["needs_human_review"] is False
                # doc_only_not_found should not be set (or be False/absent)
                assert not result.get("doc_only_not_found")


class TestAgentStream:
    """Test agent_stream generator for SSE-formatted event streaming."""

    def test_agent_stream_yields_status_first(self):
        """agent_stream() yields status=searching as first frame."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory:
            mock_client_factory.return_value.retrieval.agent.return_value = iter([])

            from apps.api.services.r2r_agent import agent_stream

            frames = list(agent_stream("test?", "conv-1"))

            assert len(frames) >= 1
            first_frame = json.loads(frames[0].split("data: ")[1])
            assert first_frame["type"] == "status"
            assert first_frame["phase"] == "searching"

    def test_agent_stream_emits_token_events_per_message_event(self):
        """agent_stream() yields token frame for each MessageEvent content delta."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                events = [
                    MessageEvent("Hello "),
                    MessageEvent("world"),
                ]
                mock_client_factory.return_value.retrieval.agent.return_value = iter(events)
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_stream

                frames = list(agent_stream("test?", "conv-1"))

                token_frames = [
                    json.loads(f.split("data: ")[1])
                    for f in frames
                    if "data: " in f
                ]
                token_frames = [f for f in token_frames if f.get("type") == "token"]

                assert len(token_frames) == 2
                assert token_frames[0]["text"] == "Hello "
                assert token_frames[1]["text"] == "world"

    def test_agent_stream_emits_final_event_with_adapted_dict(self):
        """agent_stream() yields final frame with adapted response dict."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                events = [
                    MessageEvent("The answer is 42."),
                    FinalAnswerEvent("The answer is 42.", "conv-1"),
                ]
                mock_client_factory.return_value.retrieval.agent.return_value = iter(events)
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_stream

                frames = list(agent_stream("What is the answer?", "conv-1"))

                final_frames = [
                    json.loads(f.split("data: ")[1])
                    for f in frames
                    if "data: " in f
                ]
                final_frames = [f for f in final_frames if f.get("type") == "final"]

                assert len(final_frames) == 1
                result = final_frames[0]["result"]
                assert result["answer"] == "The answer is 42."
                assert result["question"] == "What is the answer?"
                assert "citations" in result
                assert "retrieved_contexts" in result

    def test_agent_stream_emits_error_when_sdk_raises(self):
        """agent_stream() yields error frame when retrieval.agent raises."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory:
            import httpx

            mock_client_factory.return_value.retrieval.agent.side_effect = httpx.ConnectError(
                "R2R connection failed"
            )

            from apps.api.services.r2r_agent import agent_stream

            frames = list(agent_stream("test?", "conv-1"))

            assert len(frames) >= 1
            first_frame = json.loads(frames[0].split("data: ")[1])
            assert first_frame["type"] == "error"
            assert "R2R unavailable" in first_frame["detail"]

    def test_agent_stream_emits_error_mid_stream(self):
        """agent_stream() yields tokens then error frame when stream raises."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory:
            import httpx

            def failing_generator():
                yield MessageEvent("Partial ")
                yield MessageEvent("answer")
                raise httpx.ReadError("Network error")

            mock_client_factory.return_value.retrieval.agent.return_value = failing_generator()

            from apps.api.services.r2r_agent import agent_stream

            frames = list(agent_stream("test?", "conv-1"))

            frame_list = [json.loads(f.split("data: ")[1]) for f in frames if "data: " in f]

            token_frames = [f for f in frame_list if f.get("type") == "token"]
            error_frames = [f for f in frame_list if f.get("type") == "error"]

            assert len(token_frames) >= 2
            assert token_frames[0]["text"] == "Partial "
            assert token_frames[1]["text"] == "answer"
            assert len(error_frames) == 1
            assert "stream interrupted" in error_frames[0]["detail"]

    def test_agent_stream_citation_event_between_tokens_does_not_regress_phase(self):
        """CitationEvent does not emit a status frame that regresses phase order.

        R2R may emit CitationEvent during/after the MessageEvent token stream.
        Previously, CitationEvent yielded a status frame with phase=found_results,
        causing UI regression: "Generating answer…" → "Reading citations…" (backwards).

        This test verifies that CitationEvent does NOT yield any status frame,
        preserving monotonic forward-only phase progression:
        "Searching…" → "Reading citations…" → "Generating…"
        """
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                events = [
                    SearchResultsEvent([]),  # Announces "found_results"
                    MessageEvent("hello"),   # Start generation
                    CitationEvent(),         # Should NOT emit a status frame
                    MessageEvent(" world"),  # Continue generation
                    FinalAnswerEvent("hello world", "conv-1"),
                ]
                mock_client_factory.return_value.retrieval.agent.return_value = iter(events)
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_stream

                frames = list(agent_stream("test?", "conv-1"))
                frame_list = [json.loads(f.split("data: ")[1]) for f in frames if "data: " in f]

                # Extract status frames to verify phase order
                status_frames = [f for f in frame_list if f.get("type") == "status"]
                token_frames = [f for f in frame_list if f.get("type") == "token"]

                # Verify status frames are in forward-only order: searching → found_results → generating
                status_phases = [s.get("phase") for s in status_frames]
                assert status_phases == ["searching", "found_results", "generating"], (
                    f"Phase order must be monotonically forward. Got: {status_phases}"
                )

                # Verify tokens are streamed in order with no regressive status frames between them
                assert len(token_frames) == 2
                assert token_frames[0]["text"] == "hello"
                assert token_frames[1]["text"] == " world"

                # Verify no duplicate "found_results" phase (which would come from CitationEvent)
                found_results_count = status_phases.count("found_results")
                assert found_results_count == 1, (
                    f"'found_results' phase should appear exactly once (from SearchResultsEvent). "
                    f"Got {found_results_count} occurrences. This indicates CitationEvent is "
                    f"emitting a regressive status frame."
                )

    def test_agent_stream_synthesizes_final_frame_when_no_final_event(self):
        """Defensive branch: loop exits without FinalAnswerEvent; synthesizes final frame from accumulated text."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                # Events: search result and message delta, but no FinalAnswerEvent
                events = [
                    SearchResultsEvent([
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
                    ]),
                    MessageEvent("The refund policy is 30 days."),
                    # No FinalAnswerEvent - loop exits without it
                ]
                mock_client_factory.return_value.retrieval.agent.return_value = iter(events)
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_stream

                frames = list(agent_stream("What is the refund policy?", "conv-1"))

                # Parse all frames
                frame_list = [json.loads(f.split("data: ")[1]) for f in frames if "data: " in f]

                # Find the final frame
                final_frames = [f for f in frame_list if f.get("type") == "final"]

                assert len(final_frames) == 1, "Should emit exactly one final frame (synthesized)"
                result = final_frames[0]["result"]
                assert result["answer"] == "The refund policy is 30 days."
                assert result["question"] == "What is the refund policy?"
                assert "citations" in result
                assert "retrieved_contexts" in result


class TestDocumentFilter:
    """Test document_id filter behavior for AC4.3 and AC4.7."""

    def test_ac4_3_agent_query_with_document_id_applies_filter(self):
        """AC4.3: agent_query with document_id applies r2r document ID filter."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.load_document_manifest") as mock_manifest, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                # Mock manifest returns a list of r2r document IDs
                mock_manifest.return_value = {
                    "r2r_document_ids": ["r2r-uuid-1", "r2r-uuid-2"]
                }

                mock_message = mock.MagicMock()
                mock_message.content = "The answer is here."
                mock_message.metadata = {
                    "aggregated_search_result": json.dumps({"chunk_search_results": []})
                }

                mock_response = mock.MagicMock()
                mock_response.results.messages = [mock_message]
                mock_response.results.conversation_id = "conv-1"

                mock_client_factory.return_value.retrieval.agent.return_value = mock_response
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_query

                result = agent_query("What is the answer?", "conv-1", document_id="doc1")

                # Verify that the agent was called with filters
                call_kwargs = mock_client_factory.return_value.retrieval.agent.call_args.kwargs
                assert "search_settings" in call_kwargs
                search_settings = call_kwargs["search_settings"]
                assert "filters" in search_settings
                assert search_settings["filters"] == {
                    "document_id": {"$in": ["r2r-uuid-1", "r2r-uuid-2"]}
                }

    def test_ac4_7_agent_query_manifest_returns_none(self):
        """AC4.7: agent_query with document_id where manifest is None → no filters key."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.load_document_manifest") as mock_manifest, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                # Manifest returns None (document has no r2r_document_ids)
                mock_manifest.return_value = None

                mock_message = mock.MagicMock()
                mock_message.content = "Fallback answer without filters."
                mock_message.metadata = {
                    "aggregated_search_result": json.dumps({"chunk_search_results": []})
                }

                mock_response = mock.MagicMock()
                mock_response.results.messages = [mock_message]
                mock_response.results.conversation_id = "conv-1"

                mock_client_factory.return_value.retrieval.agent.return_value = mock_response
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_query

                result = agent_query("What is the answer?", "conv-1", document_id="doc1")

                # Verify that search_settings does NOT contain filters key
                call_kwargs = mock_client_factory.return_value.retrieval.agent.call_args.kwargs
                search_settings = call_kwargs["search_settings"]
                assert "filters" not in search_settings

    def test_ac4_7_agent_query_manifest_returns_empty_list(self):
        """AC4.7: agent_query with document_id where manifest has empty r2r_document_ids → no filters."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.load_document_manifest") as mock_manifest, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                # Manifest returns dict with empty list
                mock_manifest.return_value = {"r2r_document_ids": []}

                mock_message = mock.MagicMock()
                mock_message.content = "Fallback answer without filters."
                mock_message.metadata = {
                    "aggregated_search_result": json.dumps({"chunk_search_results": []})
                }

                mock_response = mock.MagicMock()
                mock_response.results.messages = [mock_message]
                mock_response.results.conversation_id = "conv-1"

                mock_client_factory.return_value.retrieval.agent.return_value = mock_response
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_query

                result = agent_query("What is the answer?", "conv-1", document_id="doc1")

                # Verify that search_settings does NOT contain filters key
                call_kwargs = mock_client_factory.return_value.retrieval.agent.call_args.kwargs
                search_settings = call_kwargs["search_settings"]
                assert "filters" not in search_settings

    def test_no_op_when_document_id_is_none(self):
        """No-op: agent_query without document_id → no filters, load_document_manifest not called."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.load_document_manifest") as mock_manifest, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                mock_message = mock.MagicMock()
                mock_message.content = "Answer without document scope."
                mock_message.metadata = {
                    "aggregated_search_result": json.dumps({"chunk_search_results": []})
                }

                mock_response = mock.MagicMock()
                mock_response.results.messages = [mock_message]
                mock_response.results.conversation_id = "conv-1"

                mock_client_factory.return_value.retrieval.agent.return_value = mock_response
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_query

                # Call without document_id
                result = agent_query("What is the answer?", "conv-1")

                # Verify that load_document_manifest was NOT called
                mock_manifest.assert_not_called()

                # Verify that search_settings does NOT contain filters key
                call_kwargs = mock_client_factory.return_value.retrieval.agent.call_args.kwargs
                search_settings = call_kwargs["search_settings"]
                assert "filters" not in search_settings
