"""Tests for /conversations route."""
from unittest import mock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from apps.api.main import app

    return TestClient(app)


class TestCreateConversation:
    """Test POST /conversations endpoint."""

    def test_create_conversation_returns_id(self, client):
        """POST /conversations returns 200 with conversation_id."""
        with mock.patch("apps.api.routes.conversations.r2r_agent.create_conversation") as mock_create:
            mock_create.return_value = "conv-1"

            response = client.post("/conversations", json={})

            assert response.status_code == 200
            assert response.json() == {"conversation_id": "conv-1"}

    def test_create_conversation_returns_503_when_r2r_down(self, client):
        """POST /conversations returns 503 when R2R is unavailable."""
        with mock.patch("apps.api.routes.conversations.r2r_agent.create_conversation") as mock_create:
            mock_create.side_effect = RuntimeError("R2R unavailable: Connection refused")

            response = client.post("/conversations", json={})

            assert response.status_code == 503
            assert "R2R unavailable" in response.json()["detail"]


class TestPostMessage:
    """Test POST /conversations/{conversation_id}/messages endpoint."""

    def test_post_message_returns_agent_response(self, client):
        """POST /conversations/{id}/messages returns 200 with agent response."""
        with mock.patch("apps.api.routes.conversations.r2r_agent.agent_query") as mock_query:
            mock_response = {
                "question": "What is the refund policy?",
                "answer": "30 days.",
                "citations": [{"document": "policy.pdf", "page": 1}],
                "retrieved_contexts": [{"text": "...", "score": 0.9}],
                "figures": [],
                "confidence_label": "high",
                "needs_human_review": False,
                "conversation_id": "conv-1",
            }
            mock_query.return_value = mock_response

            response = client.post(
                "/conversations/conv-1/messages",
                json={"message": "What is the refund policy?"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["answer"] == "30 days."
            assert data["conversation_id"] == "conv-1"

    def test_post_message_returns_503_when_r2r_down(self, client):
        """POST /conversations/{id}/messages returns 503 when R2R is unavailable."""
        with mock.patch("apps.api.routes.conversations.r2r_agent.agent_query") as mock_query:
            mock_query.side_effect = RuntimeError("R2R unavailable: Timeout")

            response = client.post(
                "/conversations/conv-1/messages",
                json={"message": "Question?"},
            )

            assert response.status_code == 503
            assert "R2R unavailable" in response.json()["detail"]


class TestPostMessageStream:
    """Test POST /conversations/{conversation_id}/messages/stream endpoint."""

    def test_post_message_stream_returns_event_stream_content_type(self, client):
        """POST /conversations/{id}/messages/stream returns text/event-stream."""
        with mock.patch("apps.api.routes.conversations.r2r_agent.agent_stream") as mock_stream:
            mock_stream.return_value = iter([f'data: {{"type":"status"}}\n\n'])

            response = client.post(
                "/conversations/conv-1/messages/stream",
                json={"message": "hi"},
            )

            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")

    def test_post_message_stream_yields_frames_in_order(self, client):
        """POST /conversations/{id}/messages/stream yields SSE frames in order."""
        with mock.patch("apps.api.routes.conversations.r2r_agent.agent_stream") as mock_stream:
            mock_stream.return_value = iter([
                'data: {"type":"status","phase":"searching"}\n\n',
                'data: {"type":"token","text":"Hello"}\n\n',
                'data: {"type":"token","text":" world"}\n\n',
            ])

            response = client.post(
                "/conversations/conv-1/messages/stream",
                json={"message": "hi"},
            )

            assert response.status_code == 200
            content = response.text
            # Verify all frames are present and in order
            assert "searching" in content
            assert content.index("searching") < content.index("Hello")
            assert content.index("Hello") < content.index("world")

    def test_post_message_stream_passes_through_error_frames(self, client):
        """POST /conversations/{id}/messages/stream passes through error frames."""
        with mock.patch("apps.api.routes.conversations.r2r_agent.agent_stream") as mock_stream:
            mock_stream.return_value = iter([
                'data: {"type":"error","detail":"R2R unavailable"}\n\n'
            ])

            response = client.post(
                "/conversations/conv-1/messages/stream",
                json={"message": "hi"},
            )

            assert response.status_code == 200
            assert "R2R unavailable" in response.text


class TestPostMessageWithNotebook:
    """Test POST /conversations/{conversation_id}/messages with notebook_id."""

    def test_scoped_message_passes_collection_id(self, client):
        """POST /conversations/{id}/messages with notebook_id passes collection_id to agent_query."""
        fake_nb = {"id": "nb-1", "r2r_collection_id": "col-xyz"}
        fake_result = {"answer": "scoped", "citations": []}

        with mock.patch("apps.api.routes.conversations.notebook_store.get_notebook", return_value=fake_nb), \
             mock.patch("apps.api.routes.conversations.r2r_agent.agent_query", return_value=fake_result) as mock_agent:
            response = client.post(
                "/conversations/conv-abc/messages",
                json={"message": "hello", "notebook_id": "nb-1"},
            )

        assert response.status_code == 200
        call_kwargs = mock_agent.call_args[1]
        assert call_kwargs.get("collection_id") == "col-xyz"

    def test_unscoped_message_no_collection_id(self, client):
        """POST /conversations/{id}/messages without notebook_id passes collection_id=None."""
        fake_result = {"answer": "unscoped", "citations": []}
        with mock.patch("apps.api.routes.conversations.r2r_agent.agent_query", return_value=fake_result) as mock_agent:
            response = client.post(
                "/conversations/conv-abc/messages",
                json={"message": "hello"},
            )
        assert response.status_code == 200
        call_kwargs = mock_agent.call_args[1]
        assert call_kwargs.get("collection_id") is None

    def test_message_with_unknown_notebook_returns_404(self, client):
        """POST /conversations/{id}/messages with non-existent notebook_id returns 404."""
        with mock.patch("apps.api.routes.conversations.notebook_store.get_notebook", return_value=None):
            response = client.post(
                "/conversations/conv-abc/messages",
                json={"message": "hello", "notebook_id": "ghost"},
            )
        assert response.status_code == 404

    def test_scoped_message_stream_passes_collection_id(self, client):
        """POST /conversations/{id}/messages/stream with notebook_id passes collection_id to agent_stream."""
        fake_nb = {"id": "nb-2", "r2r_collection_id": "col-stream"}

        with mock.patch("apps.api.routes.conversations.notebook_store.get_notebook", return_value=fake_nb), \
             mock.patch("apps.api.routes.conversations.r2r_agent.agent_stream") as mock_stream:
            mock_stream.return_value = iter([f'data: {{"type":"status"}}\n\n'])

            response = client.post(
                "/conversations/conv-stream/messages/stream",
                json={"message": "hello", "notebook_id": "nb-2"},
            )

        assert response.status_code == 200
        call_kwargs = mock_stream.call_args[1]
        assert call_kwargs.get("collection_id") == "col-stream"

    def test_message_stream_with_unknown_notebook_returns_404(self, client):
        """POST /conversations/{id}/messages/stream with non-existent notebook_id returns 404."""
        with mock.patch("apps.api.routes.conversations.notebook_store.get_notebook", return_value=None):
            response = client.post(
                "/conversations/conv-abc/messages/stream",
                json={"message": "hello", "notebook_id": "ghost"},
            )
        assert response.status_code == 404
