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
