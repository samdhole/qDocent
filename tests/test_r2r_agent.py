"""Tests for R2R agent service (conversation-aware queries)."""
import asyncio
import json
from unittest import mock
from unittest.mock import AsyncMock

import pytest


async def _collect(agen):
    """Drain an async generator into a list for synchronous test assertions."""
    return [item async for item in agen]


def _async_iter(*events):
    """Return an async generator over *events, for mocking async streaming returns."""
    async def _gen():
        for e in events:
            yield e
    return _gen()


def _rag_response(answer: str, chunk_results=None):
    """Build a mock retrieval.rag() response with the RAG response shape.

    RAG response shape (R2R 3.6.x):
        results.completion          → answer string
        results.search_results      → dict with chunk_search_results
    """
    resp = mock.MagicMock()
    resp.results.completion = answer
    resp.results.search_results = {"chunk_search_results": chunk_results or []}
    return resp


def _agent_response(answer: str, chunk_results=None):
    """Build a mock retrieval.agent() response with AgentResponse shape.

    AgentResponse shape:
        results.messages            → list of message dicts with role/content
        results.conversation_id     → string ID
    """
    resp = mock.MagicMock()
    resp.results.messages = [{"role": "assistant", "content": answer}]
    resp.results.conversation_id = "conv-1"

    # Also mock the search response (called separately for citations)
    # The search response needs a results object with chunk_search_results
    search_resp = mock.MagicMock()
    search_results_obj = mock.MagicMock()
    search_results_obj.chunk_search_results = chunk_results or []
    # Mock model_dump() to return a dict representation
    search_results_obj.model_dump.return_value = {"chunk_search_results": chunk_results or []}
    search_resp.results = search_results_obj
    return resp, search_resp


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
        chunks = [
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
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                agent_resp, search_resp = _agent_response("The policy is 30 days.", chunks)
                mock_client_factory.return_value.retrieval.agent.return_value = agent_resp
                mock_client_factory.return_value.retrieval.search.return_value = search_resp
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
                agent_resp, search_resp = _agent_response("Answer")
                mock_client_factory.return_value.retrieval.agent.return_value = agent_resp
                mock_client_factory.return_value.retrieval.search.return_value = search_resp
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_query

                result = agent_query("question", "conv-abc-123")

                assert result["conversation_id"] == "conv-abc-123"

    def test_agent_query_handles_no_chunks(self):
        """agent_query() handles empty chunk_search_results gracefully."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                agent_resp, search_resp = _agent_response("I don't have enough information.")
                mock_client_factory.return_value.retrieval.agent.return_value = agent_resp
                mock_client_factory.return_value.retrieval.search.return_value = search_resp
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_query

                result = agent_query("question", "conv-1")

                assert result["citations"] == []
                assert result["retrieved_contexts"] == []
                assert result["confidence_label"] == "low"
                assert result["needs_human_review"] is True

    def test_agent_query_handles_string_completion(self):
        """agent_query() handles when answer is a plain string."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                agent_resp, search_resp = _agent_response("Please specify which document you are referring to.")
                mock_client_factory.return_value.retrieval.agent.return_value = agent_resp
                mock_client_factory.return_value.retrieval.search.return_value = search_resp
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
                agent_dict = {
                    "results": {
                        "messages": [{"role": "assistant", "content": "The answer is here."}],
                        "conversation_id": "conv-dict"
                    }
                }
                search_dict = {
                    "results": {
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
                    }
                }

                mock_client_factory.return_value.retrieval.agent.return_value = agent_dict
                mock_client_factory.return_value.retrieval.search.return_value = search_dict
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_query

                result = agent_query("What is the guide?", "conv-dict")

                assert result["answer"] == "The answer is here."
                assert len(result["citations"]) == 1
                assert result["citations"][0]["document"] == "guide.pdf"
                assert result["conversation_id"] == "conv-dict"

    def test_agent_query_includes_chunk_index_from_header(self):
        """Task 1: chunk_index from DocQuery citation header is included in citations."""
        chunks = [
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
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                agent_resp, search_resp = _agent_response("The policy is 30 days.", chunks)
                mock_client_factory.return_value.retrieval.agent.return_value = agent_resp
                mock_client_factory.return_value.retrieval.search.return_value = search_resp
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


class ToolCallEvent:
    """Fake ToolCallEvent for testing agent_stream."""

    def __init__(self):
        pass

    def model_dump(self):
        return {"data": {}}


class ToolResultEvent:
    """Fake ToolResultEvent for testing agent_stream."""

    def __init__(self):
        pass

    def model_dump(self):
        return {"data": {}}


class ThinkingEvent:
    """Fake ThinkingEvent for testing agent_stream."""

    def __init__(self):
        pass

    def model_dump(self):
        return {"data": {}}


class CitationEvent:
    """Fake CitationEvent for testing agent_stream."""

    def __init__(self):
        pass

    def model_dump(self):
        return {"data": {}}


def _make_search_response(scores: list[float]) -> mock.Mock:
    """Build a mock WrappedSearchResponse with chunks at given scores."""
    resp = mock.Mock()
    chunks = [mock.Mock(score=s) for s in scores]
    resp.results.chunk_search_results = chunks
    return resp


class TestDocOnly:
    """Test doc_only pre-flight + defense-in-depth post-hoc check for strict document-only mode."""

    def test_ac3_2_doc_only_empty_retrieval(self):
        """AC3.2: doc_only=True with empty retrieval → pre-flight blocks rag, returns not-found."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                mock_client_factory.return_value.retrieval.search.return_value = _make_search_response([])
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_query

                result = agent_query("What is the refund policy?", "conv-1", doc_only=True)

                mock_client_factory.return_value.retrieval.rag.assert_not_called()
                assert result["answer"] == "I couldn't find this in your documents."
                assert result["confidence_label"] == "low"
                assert result["needs_human_review"] is True
                assert result["doc_only_not_found"] is True

    def test_ac3_3_doc_only_low_score_chunk(self):
        """AC3.3: doc_only=True with low-score chunk → pre-flight blocks rag, returns not-found."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                mock_client_factory.return_value.retrieval.search.return_value = _make_search_response([0.003])
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_query

                result = agent_query("What is the refund policy?", "conv-1", doc_only=True)

                mock_client_factory.return_value.retrieval.rag.assert_not_called()
                assert result["answer"] == "I couldn't find this in your documents."
                assert result["confidence_label"] == "low"
                assert result["needs_human_review"] is True
                assert result["doc_only_not_found"] is True

    def test_ac3_4_doc_only_high_score_chunk(self):
        """AC3.4: doc_only=True with high-score chunk → pre-flight passes, agent called, answer preserved."""
        chunks = [
            {
                "text": "DocQuery Citation: document_id=doc1; source_file=policy.pdf; page_start=1; page_end=1; section_path=Refunds; chunk_index=0\n\nRefund policy details: 30 days",
                "metadata": {
                    "chunk_id": "chunk-1",
                    "source_file": "policy.pdf",
                    "page_start": 1,
                },
                "score": 0.016,
                "id": "chunk-1",
            }
        ]
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                # score 0.016 >= 0.015 → needs_review=False → agent IS called
                agent_resp, search_resp = _agent_response("The refund policy is 30 days.", chunks)
                mock_client_factory.return_value.retrieval.agent.return_value = agent_resp
                # search_response is called twice: once in pre-flight, once in agent_query
                mock_client_factory.return_value.retrieval.search.side_effect = [
                    _make_search_response([0.016]),  # pre-flight
                    search_resp,  # agent query search call
                ]
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_query

                result = agent_query("What is the refund policy?", "conv-1", doc_only=True)

                mock_client_factory.return_value.retrieval.agent.assert_called_once()
                assert result["answer"] == "The refund policy is 30 days."
                assert result["confidence_label"] == "high"
                assert result["needs_human_review"] is False
                assert not result.get("doc_only_not_found")

    def test_ac3_5_doc_only_false_empty_retrieval(self):
        """AC3.5: doc_only=False (general mode) with empty retrieval → no pre-flight, original LLM answer."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                agent_resp, search_resp = _agent_response("Based on general knowledge, refund periods vary by industry.")
                mock_client_factory.return_value.retrieval.agent.return_value = agent_resp
                mock_client_factory.return_value.retrieval.search.return_value = search_resp
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_query

                result = agent_query("What is the refund policy?", "conv-1", doc_only=False)

                # doc_only=False → no pre-flight, no substitution
                assert result["answer"] == "Based on general knowledge, refund periods vary by industry."
                assert result["confidence_label"] == "low"
                assert result["needs_human_review"] is True
                assert not result.get("doc_only_not_found")

    def test_ac3_2_doc_only_stream_empty_retrieval(self):
        """AC3.2 stream path: doc_only=True with empty retrieval → pre-flight blocks stream, single final SSE."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.get_async_client") as mock_async_client, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                mock_client_factory.return_value.retrieval.search.return_value = _make_search_response([])
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_stream

                frames = asyncio.run(_collect(agent_stream("What is the refund policy?", "conv-1", doc_only=True)))

                # _make_streaming_request must NOT be called (pre-flight blocked it)
                mock_async_client.return_value._make_streaming_request.assert_not_called()

                final_frames = [
                    json.loads(f.split("data: ")[1])
                    for f in frames
                    if "data: " in f and json.loads(f.split("data: ")[1]).get("type") == "final"
                ]

                assert len(final_frames) == 1
                result = final_frames[0]["result"]
                assert result["answer"] == "I couldn't find this in your documents."
                assert result["confidence_label"] == "low"
                assert result["needs_human_review"] is True
                assert result.get("doc_only_not_found") is True

    def test_ac3_4_doc_only_stream_high_score(self):
        """AC3.4 stream path: doc_only=True with high-score chunk → pre-flight passes, stream called, answer preserved."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.get_async_client") as mock_async_client, \
             mock.patch("apps.api.services.r2r_agent.parse_retrieval_event", side_effect=lambda x: x), \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                # score 0.016 → pre-flight passes, stream IS called
                mock_client_factory.return_value.retrieval.search.return_value = _make_search_response([0.016])

                events = [
                    SearchResultsEvent([
                        {
                            "text": "DocQuery Citation: document_id=doc1; source_file=policy.pdf; page_start=1; page_end=1; section_path=Refunds; chunk_index=0\n\nRefund policy details: 30 days",
                            "metadata": {
                                "chunk_id": "chunk-1",
                                "source_file": "policy.pdf",
                                "page_start": 1,
                            },
                            "score": 0.016,
                            "id": "chunk-1",
                        }
                    ]),
                    MessageEvent("The refund policy is 30 days."),
                    FinalAnswerEvent("The refund policy is 30 days.", "conv-1"),
                ]
                mock_async_client.return_value._make_streaming_request.return_value = _async_iter(*events)
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_stream

                frames = asyncio.run(_collect(agent_stream("What is the refund policy?", "conv-1", doc_only=True)))

                final_frames = [
                    json.loads(f.split("data: ")[1])
                    for f in frames
                    if "data: " in f and json.loads(f.split("data: ")[1]).get("type") == "final"
                ]

                assert len(final_frames) == 1
                result = final_frames[0]["result"]
                assert result["answer"] == "The refund policy is 30 days."
                assert result["confidence_label"] == "high"
                assert result["needs_human_review"] is False
                assert not result.get("doc_only_not_found")

    def test_doc_only_preflight_blocks_rag_call(self):
        """Core guarantee: when pre-flight score is low, agent is never called."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory:
            mock_client_factory.return_value.retrieval.search.return_value = _make_search_response([])

            from apps.api.services.r2r_agent import agent_query

            result = agent_query("Unrelated question about Jupiter", "conv-x", doc_only=True)

            mock_client_factory.return_value.retrieval.agent.assert_not_called()
            assert result["doc_only_not_found"] is True
            assert result["answer"] == "I couldn't find this in your documents."


class TestAgentStream:
    """Test agent_stream generator for SSE-formatted event streaming."""

    def test_agent_stream_yields_status_first(self):
        """agent_stream() yields status=searching as first frame."""
        with mock.patch("apps.api.services.r2r_agent.get_async_client") as mock_async_client, \
             mock.patch("apps.api.services.r2r_agent.parse_retrieval_event", side_effect=lambda x: x):
                mock_async_client.return_value._make_streaming_request.return_value = _async_iter()

                from apps.api.services.r2r_agent import agent_stream

                frames = asyncio.run(_collect(agent_stream("test?", "conv-1")))

                assert len(frames) >= 1
                first_frame = json.loads(frames[0].split("data: ")[1])
                assert first_frame["type"] == "status"
                assert first_frame["phase"] == "searching"

    def test_agent_stream_emits_token_events_per_message_event(self):
        """agent_stream() yields token frame for each MessageEvent content delta."""
        with mock.patch("apps.api.services.r2r_agent.get_async_client") as mock_async_client, \
             mock.patch("apps.api.services.r2r_agent.parse_retrieval_event", side_effect=lambda x: x), \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                events = [
                    MessageEvent("Hello "),
                    MessageEvent("world"),
                ]
                mock_async_client.return_value._make_streaming_request.return_value = _async_iter(*events)
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_stream

                frames = asyncio.run(_collect(agent_stream("test?", "conv-1")))

                token_frames = [
                    json.loads(f.split("data: ")[1])
                    for f in frames
                    if "data: " in f
                ]
                token_frames = [f for f in token_frames if f.get("type") == "token"]

                assert len(token_frames) == 2
                assert token_frames[0]["text"] == "Hello "
                assert token_frames[1]["text"] == "world"

                # Verify streaming request was called with correct URL and message shape
                call_args = mock_async_client.return_value._make_streaming_request.call_args
                assert call_args.args[1] == "retrieval/agent", "Second positional arg should be URL"
                assert "task_prompt" not in call_args.kwargs["json"], "task_prompt must not be in request body"
                assert "message" in call_args.kwargs["json"], "message must be in request body"

    def test_agent_stream_emits_final_event_with_adapted_dict(self):
        """agent_stream() yields final frame with adapted response dict."""
        with mock.patch("apps.api.services.r2r_agent.get_async_client") as mock_async_client, \
             mock.patch("apps.api.services.r2r_agent.parse_retrieval_event", side_effect=lambda x: x), \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                events = [
                    MessageEvent("The answer is 42."),
                    FinalAnswerEvent("The answer is 42.", "conv-1"),
                ]
                mock_async_client.return_value._make_streaming_request.return_value = _async_iter(*events)
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_stream

                frames = asyncio.run(_collect(agent_stream("What is the answer?", "conv-1")))

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
        """agent_stream() yields error frame when _make_streaming_request raises."""
        with mock.patch("apps.api.services.r2r_agent.get_async_client") as mock_async_client:
            import httpx

            async def _failing():
                raise httpx.ConnectError("R2R connection failed")
                yield  # make it an async generator

            mock_async_client.return_value._make_streaming_request.return_value = _failing()

            from apps.api.services.r2r_agent import agent_stream

            frames = asyncio.run(_collect(agent_stream("test?", "conv-1")))

            frame_list = [json.loads(f.split("data: ")[1]) for f in frames if "data: " in f]
            error_frames = [f for f in frame_list if f.get("type") == "error"]
            assert len(error_frames) == 1
            assert "stream interrupted" in error_frames[0]["detail"]

    def test_agent_stream_emits_error_mid_stream(self):
        """agent_stream() yields tokens then error frame when stream raises mid-iteration."""
        with mock.patch("apps.api.services.r2r_agent.get_async_client") as mock_async_client, \
             mock.patch("apps.api.services.r2r_agent.parse_retrieval_event", side_effect=lambda x: x):
            import httpx

            async def failing_async_generator():
                yield MessageEvent("Partial ")
                yield MessageEvent("answer")
                raise httpx.ReadError("Network error")

            mock_async_client.return_value._make_streaming_request.return_value = failing_async_generator()

            from apps.api.services.r2r_agent import agent_stream

            frames = asyncio.run(_collect(agent_stream("test?", "conv-1")))

            frame_list = [json.loads(f.split("data: ")[1]) for f in frames if "data: " in f]

            token_frames = [f for f in frame_list if f.get("type") == "token"]
            error_frames = [f for f in frame_list if f.get("type") == "error"]

            assert len(token_frames) >= 2
            assert token_frames[0]["text"] == "Partial "
            assert token_frames[1]["text"] == "answer"
            assert len(error_frames) == 1
            assert "stream interrupted" in error_frames[0]["detail"]

    def test_agent_stream_citation_event_between_tokens_does_not_regress_phase(self):
        """CitationEvent does not emit a status frame that regresses phase order."""
        with mock.patch("apps.api.services.r2r_agent.get_async_client") as mock_async_client, \
             mock.patch("apps.api.services.r2r_agent.parse_retrieval_event", side_effect=lambda x: x), \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                events = [
                    SearchResultsEvent([]),  # Announces "found_results"
                    MessageEvent("hello"),   # Start generation
                    CitationEvent(),         # Should NOT emit a status frame
                    MessageEvent(" world"),  # Continue generation
                    FinalAnswerEvent("hello world", "conv-1"),
                ]
                mock_async_client.return_value._make_streaming_request.return_value = _async_iter(*events)
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_stream

                frames = asyncio.run(_collect(agent_stream("test?", "conv-1")))
                frame_list = [json.loads(f.split("data: ")[1]) for f in frames if "data: " in f]

                status_frames = [f for f in frame_list if f.get("type") == "status"]
                token_frames = [f for f in frame_list if f.get("type") == "token"]

                status_phases = [s.get("phase") for s in status_frames]
                assert status_phases == ["searching", "found_results", "generating"], (
                    f"Phase order must be monotonically forward. Got: {status_phases}"
                )

                assert len(token_frames) == 2
                assert token_frames[0]["text"] == "hello"
                assert token_frames[1]["text"] == " world"

                found_results_count = status_phases.count("found_results")
                assert found_results_count == 1, (
                    f"'found_results' phase should appear exactly once. "
                    f"Got {found_results_count} occurrences."
                )

    def test_agent_stream_synthesizes_final_frame_when_no_final_event(self):
        """Defensive branch: loop exits without FinalAnswerEvent; synthesizes final frame from accumulated text."""
        with mock.patch("apps.api.services.r2r_agent.get_async_client") as mock_async_client, \
             mock.patch("apps.api.services.r2r_agent.parse_retrieval_event", side_effect=lambda x: x), \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
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
                mock_async_client.return_value._make_streaming_request.return_value = _async_iter(*events)
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_stream

                frames = asyncio.run(_collect(agent_stream("What is the refund policy?", "conv-1")))

                frame_list = [json.loads(f.split("data: ")[1]) for f in frames if "data: " in f]
                final_frames = [f for f in frame_list if f.get("type") == "final"]

                assert len(final_frames) == 1, "Should emit exactly one final frame (synthesized)"
                result = final_frames[0]["result"]
                assert result["answer"] == "The refund policy is 30 days."
                assert result["question"] == "What is the refund policy?"
                assert "citations" in result
                assert "retrieved_contexts" in result

    def test_ac2_2_tool_call_event_emits_searching_beat_silent_skip(self):
        """AC2.2: ToolCallEvent emits status:searching SSE beat; ToolResultEvent and ThinkingEvent produce no output."""
        with mock.patch("apps.api.services.r2r_agent.get_async_client") as mock_async_client, \
             mock.patch("apps.api.services.r2r_agent.parse_retrieval_event", side_effect=lambda x: x), \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                events = [
                    SearchResultsEvent([]),  # Initial search results (no chunks)
                    ToolCallEvent(),         # Agent invokes search tool → emit "searching" beat
                    ToolResultEvent(),       # Tool result comes back → silently skip (no SSE)
                    ToolCallEvent(),         # Agent invokes another tool → emit another "searching" beat
                    ThinkingEvent(),         # Agent thinking → silently skip (no SSE)
                    MessageEvent("hi"),      # Start generation
                    FinalAnswerEvent("hi", "conv-1"),
                ]
                mock_async_client.return_value._make_streaming_request.return_value = _async_iter(*events)
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_stream

                frames = asyncio.run(_collect(agent_stream("test?", "conv-1")))

                # Parse all SSE frames
                frame_list = [json.loads(f.split("data: ")[1]) for f in frames if "data: " in f]

                # Extract status frames and verify "searching" appears at least 3 times:
                # 1. Initial pre-loop beat
                # 2. After first ToolCallEvent
                # 3. After second ToolCallEvent
                status_frames = [f for f in frame_list if f.get("type") == "status"]
                status_phases = [s.get("phase") for s in status_frames]

                assert status_phases.count("searching") >= 3, (
                    f"Expected at least 3 'searching' beats (initial + 2 ToolCallEvents), "
                    f"got: {status_phases}"
                )

                # Verify that status frames only contain expected phases
                # (no spurious phases from ToolResultEvent or ThinkingEvent)
                expected_phases = {"searching", "found_results", "generating"}
                for phase in status_phases:
                    assert phase in expected_phases, (
                        f"Unexpected phase '{phase}' from ToolResultEvent or ThinkingEvent. "
                        f"These events should produce no SSE content."
                    )

                # Verify no SSE frame contains data attributed to ToolResultEvent or ThinkingEvent
                for frame in frame_list:
                    # Token frames should only come from MessageEvent
                    if frame.get("type") == "token":
                        assert frame.get("text") == "hi", (
                            f"Token frame should only contain 'hi' from MessageEvent. "
                            f"Got: {frame.get('text')}"
                        )

                # Verify final frame is present
                final_frames = [f for f in frame_list if f.get("type") == "final"]
                assert len(final_frames) == 1, "Should emit exactly one final frame"


class TestDocumentFilter:
    """Test document_id filter behavior for AC4.3 and AC4.7."""

    def test_ac4_3_agent_query_with_document_id_applies_filter(self):
        """AC4.3: agent_query with document_id applies r2r document ID filter."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.load_document_manifest") as mock_manifest, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                mock_manifest.return_value = {"r2r_document_ids": ["r2r-uuid-1", "r2r-uuid-2"]}
                agent_resp, search_resp = _agent_response("The answer is here.")
                mock_client_factory.return_value.retrieval.agent.return_value = agent_resp
                mock_client_factory.return_value.retrieval.search.return_value = search_resp
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_query

                agent_query("What is the answer?", "conv-1", document_ids=["doc1"])

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
                mock_manifest.return_value = None
                agent_resp, search_resp = _agent_response("Fallback answer.")
                mock_client_factory.return_value.retrieval.agent.return_value = agent_resp
                mock_client_factory.return_value.retrieval.search.return_value = search_resp
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_query

                agent_query("What is the answer?", "conv-1", document_ids=["doc1"])

                call_kwargs = mock_client_factory.return_value.retrieval.agent.call_args.kwargs
                search_settings = call_kwargs["search_settings"]
                assert "filters" not in search_settings

    def test_ac4_7_agent_query_manifest_returns_empty_list(self):
        """AC4.7: agent_query with document_id where manifest has empty r2r_document_ids → no filters."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.load_document_manifest") as mock_manifest, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                mock_manifest.return_value = {"r2r_document_ids": []}
                agent_resp, search_resp = _agent_response("Fallback answer.")
                mock_client_factory.return_value.retrieval.agent.return_value = agent_resp
                mock_client_factory.return_value.retrieval.search.return_value = search_resp
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_query

                agent_query("What is the answer?", "conv-1", document_ids=["doc1"])

                call_kwargs = mock_client_factory.return_value.retrieval.agent.call_args.kwargs
                search_settings = call_kwargs["search_settings"]
                assert "filters" not in search_settings

    def test_no_op_when_document_id_is_none(self):
        """No-op: agent_query without document_id → no filters, load_document_manifest not called."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_client_factory, \
             mock.patch("apps.api.services.r2r_agent.load_document_manifest") as mock_manifest, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                agent_resp, search_resp = _agent_response("Answer.")
                mock_client_factory.return_value.retrieval.agent.return_value = agent_resp
                mock_client_factory.return_value.retrieval.search.return_value = search_resp
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_query

                agent_query("What is the answer?", "conv-1")

                mock_manifest.assert_not_called()
                call_kwargs = mock_client_factory.return_value.retrieval.agent.call_args.kwargs
                search_settings = call_kwargs["search_settings"]
                assert "filters" not in search_settings

    def test_ac4_3_agent_stream_with_document_id_applies_filter(self):
        """AC4.3 stream path: agent_stream with document_id applies r2r document ID filter."""
        with mock.patch("apps.api.services.r2r_agent.get_async_client") as mock_async_client, \
             mock.patch("apps.api.services.r2r_agent.load_document_manifest") as mock_manifest, \
             mock.patch("apps.api.services.r2r_agent.parse_retrieval_event", side_effect=lambda x: x), \
             mock.patch("apps.api.services.r2r_agent.figures_for_response") as mock_figures, \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
                mock_manifest.return_value = {"r2r_document_ids": ["r2r-uuid-1"]}

                events = [
                    SearchResultsEvent([
                        {
                            "text": "DocQuery Citation: document_id=doc1; source_file=filtered.pdf; page_start=1; page_end=1; section_path=Results; chunk_index=0\n\nFiltered result",
                            "metadata": {"chunk_id": "chunk-1", "source_file": "filtered.pdf", "page_start": 1},
                            "score": 0.016,
                            "id": "chunk-1",
                        }
                    ]),
                    MessageEvent("This is from the filtered document."),
                    FinalAnswerEvent("This is from the filtered document.", "conv-1"),
                ]
                mock_async_client.return_value._make_streaming_request.return_value = _async_iter(*events)
                mock_figures.return_value = []

                from apps.api.services.r2r_agent import agent_stream

                asyncio.run(_collect(agent_stream("What?", "conv-1", document_ids=["doc1"])))

                # Verify _make_streaming_request was called with the filter in the JSON body
                call_kwargs = mock_async_client.return_value._make_streaming_request.call_args.kwargs
                search_settings = call_kwargs["json"]["search_settings"]
                assert "filters" in search_settings
                assert search_settings["filters"] == {
                    "document_id": {"$in": ["r2r-uuid-1"]}
                }

    def test_multi_document_filter_merges_manifests(self):
        """Two document IDs produce one combined R2R $in filter."""
        manifest_a = {"r2r_document_ids": ["r2r-uuid-a1", "r2r-uuid-a2"]}
        manifest_b = {"r2r_document_ids": ["r2r-uuid-b1"]}

        with mock.patch(
            "apps.api.services.r2r_agent.load_document_manifest",
            side_effect=[manifest_a, manifest_b],
        ):
            from apps.api.services.r2r_agent import _build_search_settings

            settings = _build_search_settings(["doc-a", "doc-b"])

        assert settings["filters"] == {
            "document_id": {"$in": ["r2r-uuid-a1", "r2r-uuid-a2", "r2r-uuid-b1"]}
        }


class TestBuildSearchSettingsCollectionId:
    """Test _build_search_settings with collection_id parameter."""

    def test_collection_id_applies_overlap_filter(self):
        """collection_id uses selected_collection_ids (not $overlap which breaks streaming RAG)."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_get, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response", return_value=[]), \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
            agent_resp, search_resp = _agent_response("answer")
            mock_get.return_value.retrieval.agent.return_value = agent_resp
            mock_get.return_value.retrieval.search.return_value = search_resp

            from apps.api.services.r2r_agent import agent_query

            agent_query(
                message="q",
                conversation_id="conv-1",
                doc_only=False,
                document_ids=None,
                collection_id="col-abc",
            )

            call_kwargs = mock_get.return_value.retrieval.agent.call_args.kwargs
            assert call_kwargs["search_settings"]["selected_collection_ids"] == ["col-abc"]
            assert "filters" not in call_kwargs["search_settings"]

    def test_no_collection_id_uses_document_filter(self):
        """When collection_id=None, document_ids filter is applied."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_get, \
             mock.patch("apps.api.services.r2r_agent.load_document_manifest") as mock_manifest, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response", return_value=[]), \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
            mock_manifest.return_value = {"r2r_document_ids": ["r2r-001"]}
            agent_resp, search_resp = _agent_response("answer")
            mock_get.return_value.retrieval.agent.return_value = agent_resp
            mock_get.return_value.retrieval.search.return_value = search_resp

            from apps.api.services.r2r_agent import agent_query

            agent_query(
                message="q",
                conversation_id="conv-1",
                doc_only=False,
                document_ids=["local-doc-1"],
                collection_id=None,
            )

            call_kwargs = mock_get.return_value.retrieval.agent.call_args.kwargs
            filters = call_kwargs["search_settings"]["filters"]
            assert filters == {"document_id": {"$in": ["r2r-001"]}}

    def test_no_filter_when_both_none(self):
        """When collection_id=None and document_ids=None, no filters applied."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_get, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response", return_value=[]), \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
            agent_resp, search_resp = _agent_response("answer")
            mock_get.return_value.retrieval.agent.return_value = agent_resp
            mock_get.return_value.retrieval.search.return_value = search_resp

            from apps.api.services.r2r_agent import agent_query

            agent_query(
                message="q",
                conversation_id="conv-1",
                doc_only=False,
                document_ids=None,
                collection_id=None,
            )

            call_kwargs = mock_get.return_value.retrieval.agent.call_args.kwargs
            assert "filters" not in call_kwargs.get("search_settings", {})

    def test_collection_id_takes_precedence_over_document_ids(self):
        """When both collection_id and document_ids are set, collection_id wins."""
        with mock.patch("apps.api.services.r2r_agent.get_client") as mock_get, \
             mock.patch("apps.api.services.r2r_agent.load_document_manifest") as mock_manifest, \
             mock.patch("apps.api.services.r2r_agent.figures_for_response", return_value=[]), \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
            mock_manifest.return_value = {"r2r_document_ids": ["r2r-001"]}
            agent_resp, search_resp = _agent_response("answer")
            mock_get.return_value.retrieval.agent.return_value = agent_resp
            mock_get.return_value.retrieval.search.return_value = search_resp

            from apps.api.services.r2r_agent import agent_query

            agent_query(
                message="q",
                conversation_id="conv-1",
                doc_only=False,
                document_ids=["doc-1"],
                collection_id="col-xyz",
            )

            call_kwargs = mock_get.return_value.retrieval.agent.call_args.kwargs
            assert call_kwargs["search_settings"]["selected_collection_ids"] == ["col-xyz"]
            assert "filters" not in call_kwargs["search_settings"]
            mock_manifest.assert_not_called()

    def test_agent_stream_with_collection_id(self):
        """agent_stream() also accepts collection_id and uses selected_collection_ids."""
        with mock.patch("apps.api.services.r2r_agent.get_async_client") as mock_get, \
             mock.patch("apps.api.services.r2r_agent.parse_retrieval_event", side_effect=lambda x: x), \
             mock.patch("apps.api.services.r2r_agent.figures_for_response", return_value=[]), \
             mock.patch("apps.api.services.r2r_agent.rewrite_brackets", side_effect=lambda a, c, r: (a, c, r)):
            events = [
                MessageEvent("answer"),
                FinalAnswerEvent("answer", "conv-1"),
            ]
            mock_get.return_value._make_streaming_request.return_value = _async_iter(*events)

            from apps.api.services.r2r_agent import agent_stream

            asyncio.run(_collect(agent_stream(
                message="q",
                conversation_id="conv-1",
                doc_only=False,
                document_ids=None,
                collection_id="col-abc",
            )))

            call_kwargs = mock_get.return_value._make_streaming_request.call_args.kwargs
            ss = call_kwargs["json"]["search_settings"]
            assert ss["selected_collection_ids"] == ["col-abc"]
            assert "filters" not in ss
