"""Tests for /reports API routes."""
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


class TestReportsRoutes:
    """Test /reports API endpoints."""

    @mock.patch("apps.api.services.report_writer.ingestion_report")
    def test_get_ingestion_report_success(self, mock_get_report, client):
        """GET /reports/ingestion/{document_id} returns 200 with report data."""
        mock_report = {
            "document_id": "test_doc_123",
            "source_file": "test_document.pdf",
            "tables_detected": 2,
            "chunks_generated": 15,
            "parser": "table_aware",
        }
        mock_get_report.return_value = mock_report

        response = client.get("/reports/ingestion/test_doc_123")

        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == "test_doc_123"
        assert data["tables_detected"] == 2

    @mock.patch("apps.api.services.report_writer.ingestion_report")
    def test_get_ingestion_report_not_found(self, mock_get_report, client):
        """GET /reports/ingestion/{document_id} returns 404 when report not found."""
        mock_get_report.return_value = None

        response = client.get("/reports/ingestion/nonexistent_doc")

        assert response.status_code == 404
        assert "No ingestion report" in response.json()["detail"]
