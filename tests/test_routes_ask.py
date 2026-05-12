"""Tests for the /ask route."""
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@mock.patch("apps.api.routes.ask.r2r_client.rag_query")
def test_ask_citation_carries_document_id(mock_rag):
    """When rag_query returns a citation with document_id, /ask forwards it unchanged."""
    mock_rag.return_value = {
        "question": "What is the refund policy?",
        "answer": "Customers may request a refund within 30 days. [1]",
        "citations": [
            {
                "document": "company_policy.pdf",
                "document_id": "tmpl_test_doc_id",
                "page": 1,
                "page_end": 1,
                "section": "Refund Policy",
                "chunk_id": None,
                "chunk_index": 0,
            }
        ],
        "retrieved_contexts": [],
        "figures": [],
        "confidence_label": "high",
        "needs_human_review": False,
    }

    client = TestClient(app)
    response = client.post("/ask", json={"question": "What is the refund policy?"})

    assert response.status_code == 200
    data = response.json()
    citations = data.get("citations", [])
    assert len(citations) >= 1
    assert citations[0]["document_id"] == "tmpl_test_doc_id"
    assert citations[0]["page"] == 1


class TestAskWithNotebook:
    def test_scoped_ask_passes_collection_id(self, client):
        """POST /ask with notebook_id passes collection_id to rag_query."""
        fake_nb = {"id": "nb-1", "r2r_collection_id": "col-abc"}
        fake_result = {"answer": "scoped answer", "citations": []}

        with mock.patch("apps.api.routes.ask.notebook_store.get_notebook", return_value=fake_nb), \
             mock.patch("apps.api.routes.ask.r2r_client.rag_query", return_value=fake_result) as mock_rag:
            response = client.post("/ask", json={"question": "What?", "notebook_id": "nb-1"})

        assert response.status_code == 200
        mock_rag.assert_called_once_with("What?", collection_id="col-abc")

    def test_unscoped_ask_no_collection_id(self, client):
        """POST /ask without notebook_id passes collection_id=None to rag_query."""
        fake_result = {"answer": "unscoped", "citations": []}

        with mock.patch("apps.api.routes.ask.r2r_client.rag_query", return_value=fake_result) as mock_rag:
            response = client.post("/ask", json={"question": "What?"})

        assert response.status_code == 200
        mock_rag.assert_called_once_with("What?", collection_id=None)

    def test_ask_with_unknown_notebook_returns_404(self, client):
        """POST /ask with non-existent notebook_id returns 404."""
        with mock.patch("apps.api.routes.ask.notebook_store.get_notebook", return_value=None):
            response = client.post("/ask", json={"question": "?", "notebook_id": "ghost"})
        assert response.status_code == 404

    def test_ask_with_empty_notebook_returns_200_no_500(self, client):
        """AC1.5: POST /ask with a notebook_id that contains no documents returns 200."""
        fake_nb = {"id": "nb-empty", "r2r_collection_id": "col-empty"}
        fake_result = {
            "question": "?",
            "answer": "I couldn't find any relevant documents.",
            "citations": [],
            "retrieved_contexts": [],
            "figures": [],
            "confidence_label": "low",
            "needs_human_review": True,
        }
        with mock.patch("apps.api.routes.ask.notebook_store.get_notebook", return_value=fake_nb), \
             mock.patch("apps.api.routes.ask.r2r_client.rag_query", return_value=fake_result):
            response = client.post("/ask", json={"question": "?", "notebook_id": "nb-empty"})
        assert response.status_code == 200
        assert response.json()["confidence_label"] == "low"
