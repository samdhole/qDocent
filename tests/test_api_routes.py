"""Tests for FastAPI routes."""
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_health():
    """GET /health returns 200 {"status": "ok"}"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("apps.api.services.r2r_client.rag_query")
def test_ask_success(mock_rag_query):
    """POST /ask with mocked rag_query returns 200 with expected fields"""
    mock_rag_query.return_value = {
        "question": "What is the refund policy?",
        "answer": "30 days",
        "citations": [{"document": "policy.pdf", "page": 1, "section": "Returns", "chunk_id": "chunk_1"}],
        "retrieved_contexts": [{"chunk_id": "chunk_1", "text": "30-day refund policy", "score": 0.85}],
        "confidence_label": "high",
        "needs_human_review": False,
    }
    response = client.post("/ask", json={"question": "What is the refund policy?"})
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "30 days"
    assert data["confidence_label"] == "high"
    assert len(data["citations"]) > 0
    assert len(data["retrieved_contexts"]) > 0


@patch("apps.api.services.r2r_client.rag_query")
def test_ask_r2r_unavailable(mock_rag_query):
    """POST /ask when rag_query raises RuntimeError returns 503"""
    mock_rag_query.side_effect = RuntimeError("R2R unavailable: Connection refused")
    response = client.post("/ask", json={"question": "What is the refund policy?"})
    assert response.status_code == 503
    assert "R2R unavailable" in response.json()["detail"]


def test_eval_results_not_found():
    """GET /eval/results returns 404 when no CSVs in reports/evals/"""
    # This test assumes reports/evals/ is empty initially or we can mock it
    with patch("apps.api.services.report_writer.latest_eval_results") as mock_latest:
        mock_latest.return_value = []
        response = client.get("/eval/results")
        assert response.status_code == 404
        assert "No eval results found" in response.json()["detail"]


@patch("apps.api.services.report_writer.latest_eval_results")
def test_eval_results_with_data(mock_latest):
    """GET /eval/results returns rows when CSV exists"""
    mock_latest.return_value = [
        {
            "question_id": "q1",
            "answer_relevancy": 0.85,
            "context_precision": 0.90,
            "faithfulness": 0.88,
        }
    ]
    response = client.get("/eval/results")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["question_id"] == "q1"


@patch("apps.api.services.ragas_runner.run_and_save")
def test_eval_run_success(mock_run):
    """POST /eval/run executes synchronously and returns success"""
    mock_run.return_value = None
    response = client.post("/eval/run")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    mock_run.assert_called_once()


@patch("apps.api.services.ragas_runner.run_and_save")
def test_eval_run_error(mock_run):
    """POST /eval/run returns 503 when eval fails"""
    mock_run.side_effect = Exception("Dataset load failed")
    response = client.post("/eval/run")
    assert response.status_code == 503
    assert "Eval failed" in response.json()["detail"]
