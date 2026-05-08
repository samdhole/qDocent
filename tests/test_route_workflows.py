"""Tests for /workflows API routes."""
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


class TestWorkflowsRoutes:
    """Test /workflows API endpoints."""

    def test_post_support_triage_success(self, client):
        """POST /workflows/support/triage returns 200 with workflow result."""
        with mock.patch("apps.api.routes.workflows.run_support_triage") as mock_triage:
            mock_triage.return_value = {
                "customer_message": "I need a refund",
                "intent": "refund_request",
                "retrieved_contexts": [{"score": 0.85}],
                "draft_response": "Refunds are available within 30 days.",
                "citations": [{"document": "policy.pdf"}],
                "confidence_label": "high",
                "requires_human_approval": True,
                "final_response": "[Awaiting human approval]",
            }

            response = client.post(
                "/workflows/support/triage",
                json={"message": "I need a refund"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["requires_human_approval"] is True
            assert data["final_response"] == "[Awaiting human approval]"

    def test_post_support_triage_503_on_error(self, client):
        """POST /workflows/support/triage returns 503 when workflow fails."""
        with mock.patch("apps.api.routes.workflows.run_support_triage") as mock_triage:
            mock_triage.side_effect = RuntimeError("R2R unavailable")

            response = client.post(
                "/workflows/support/triage",
                json={"message": "I need a refund"},
            )

            assert response.status_code == 503

    def test_post_email_draft_success(self, client):
        """POST /workflows/support/email-draft returns 200 with workflow result."""
        with mock.patch("apps.api.routes.workflows.run_email_draft") as mock_draft:
            mock_draft.return_value = {
                "customer_message": "Draft a reply",
                "intent": "email_draft",
                "retrieved_contexts": [],
                "draft_response": "Subject: RE: Your inquiry\n\nDear customer,",
                "citations": [],
                "confidence_label": "low",
                "requires_human_approval": True,
                "final_response": "[Awaiting human approval before sending email]",
            }

            response = client.post(
                "/workflows/support/email-draft",
                json={"message": "Draft a reply"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["requires_human_approval"] is True
            assert "[Awaiting human approval" in data["final_response"]

    def test_post_email_draft_503_on_error(self, client):
        """POST /workflows/support/email-draft returns 503 when workflow fails."""
        with mock.patch("apps.api.routes.workflows.run_email_draft") as mock_draft:
            mock_draft.side_effect = Exception("LLM unavailable")

            response = client.post(
                "/workflows/support/email-draft",
                json={"message": "Draft a reply"},
            )

            assert response.status_code == 503
