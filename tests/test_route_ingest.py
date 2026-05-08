"""Tests for /ingest API route."""
from io import BytesIO
from pathlib import Path
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_pdf():
    """Create a minimal valid PDF for testing."""
    # Minimal PDF structure
    pdf_content = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n"
        b"2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n"
        b"3 0 obj\n<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>\nendobj\n"
        b"xref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n"
        b"trailer\n<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"
    )
    return BytesIO(pdf_content)


class TestIngestRoute:
    """Test /ingest API endpoint."""

    @mock.patch("apps.api.services.r2r_client.ingest_file_with_pipeline")
    def test_post_ingest_pdf_success(self, mock_ingest, client, sample_pdf):
        """POST /ingest with PDF returns 200 with status."""
        mock_ingest.return_value = {
            "r2r": "Document ingested",
            "quality_report": {
                "document_id": "test_123",
                "source_file": "test.pdf",
                "tables_detected": 0,
            },
            "document_id": "test_123",
        }

        response = client.post(
            "/ingest",
            files={"file": ("test.pdf", sample_pdf, "application/pdf")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "result" in data

    def test_post_ingest_non_pdf_rejected(self, client):
        """POST /ingest with non-PDF returns 400."""
        response = client.post(
            "/ingest",
            files={"file": ("test.txt", BytesIO(b"text content"), "text/plain")},
        )

        assert response.status_code == 400
        assert "Only PDF" in response.json()["detail"]

    @mock.patch("apps.api.services.r2r_client.ingest_file_with_pipeline")
    def test_post_ingest_service_error_returns_503(self, mock_ingest, client, sample_pdf):
        """POST /ingest returns 503 when service raises RuntimeError."""
        mock_ingest.side_effect = RuntimeError("R2R unavailable")

        response = client.post(
            "/ingest",
            files={"file": ("test.pdf", sample_pdf, "application/pdf")},
        )

        assert response.status_code == 503

    @mock.patch("apps.api.services.r2r_client.ingest_file_with_pipeline")
    def test_post_ingest_passes_original_filename(self, mock_ingest, client, sample_pdf):
        """POST /ingest passes file.filename as original_filename to ingest_file_with_pipeline."""
        mock_ingest.return_value = {
            "r2r": "ok",
            "quality_report": None,
            "document_id": None,
            "figures": [],
            "figures_r2r": None,
        }

        client.post(
            "/ingest",
            files={"file": ("my_report.pdf", sample_pdf, "application/pdf")},
        )

        mock_ingest.assert_called_once()
        _, kwargs = mock_ingest.call_args
        assert kwargs.get("original_filename") == "my_report.pdf"

    @mock.patch("apps.api.services.r2r_client.ingest_file_with_pipeline")
    def test_post_ingest_job_returns_completed_job(self, mock_ingest, client, sample_pdf):
        """POST /ingest/jobs returns a tracked async ingest job."""
        mock_ingest.return_value = {
            "r2r": "ok",
            "quality_report": None,
            "document_id": "job_doc",
            "figures": [],
            "figures_r2r": None,
        }

        response = client.post(
            "/ingest/jobs",
            files={"file": ("job.pdf", sample_pdf, "application/pdf")},
        )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] in {"queued", "running", "completed"}
        assert data["job_id"]

        job_response = client.get(f"/ingest/jobs/{data['job_id']}")
        assert job_response.status_code == 200
        job = job_response.json()
        assert job["status"] == "completed"
        assert job["result"]["document_id"] == "job_doc"

    def test_post_ingest_job_non_pdf_rejected(self, client):
        """POST /ingest/jobs with non-PDF returns 400."""
        response = client.post(
            "/ingest/jobs",
            files={"file": ("test.txt", BytesIO(b"text content"), "text/plain")},
        )

        assert response.status_code == 400
        assert "Only PDF" in response.json()["detail"]

    def test_get_ingest_job_missing_returns_404(self, client):
        """GET /ingest/jobs/{job_id} returns 404 for unknown jobs."""
        response = client.get("/ingest/jobs/not-a-real-job")

        assert response.status_code == 404

    @mock.patch("apps.api.routes.ingest.ingest_jobs.create_ingest_job")
    def test_create_ingest_job_cleans_up_tmpfile_on_exception(
        self, mock_create_job, client, sample_pdf
    ):
        """When create_ingest_job raises, the tmp file is deleted (arfix.AC5.1)."""
        import tempfile as real_tempfile

        captured_tmp_paths = []

        # Capture the real tmp file path and then raise
        original_ntf = real_tempfile.NamedTemporaryFile

        def spy_ntf(*args, **kwargs):
            tmp = original_ntf(*args, **kwargs)
            captured_tmp_paths.append(tmp.name)
            return tmp

        mock_create_job.side_effect = RuntimeError("Job creation failed")

        with mock.patch("apps.api.routes.ingest.tempfile.NamedTemporaryFile", side_effect=spy_ntf):
            with pytest.raises(RuntimeError):
                client.post(
                    "/ingest/jobs",
                    files={"file": ("test.pdf", sample_pdf, "application/pdf")},
                )

        # Verify the tmp file was created and then cleaned up
        assert len(captured_tmp_paths) == 1
        tmp_path = Path(captured_tmp_paths[0])
        assert not tmp_path.exists(), f"Tmp file {tmp_path} was not cleaned up on exception"
