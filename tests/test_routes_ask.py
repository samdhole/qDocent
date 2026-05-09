"""Tests for the /ask route."""
from unittest import mock

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


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

    response = client.post("/ask", json={"question": "What is the refund policy?"})

    assert response.status_code == 200
    data = response.json()
    citations = data.get("citations", [])
    assert len(citations) >= 1
    assert citations[0]["document_id"] == "tmpl_test_doc_id"
    assert citations[0]["page"] == 1
