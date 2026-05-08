"""Tests for async ingest job tracking."""
from pathlib import Path

from apps.api.services import ingest_jobs


def test_ingest_job_completes_with_result(tmp_path):
    """run_ingest_job stores completed status and service result."""
    source = tmp_path / "sample.pdf"
    source.write_bytes(b"%PDF-1.4\n%%EOF")

    job = ingest_jobs.create_ingest_job("sample.pdf")

    ingest_jobs.run_ingest_job(
        job["job_id"],
        source,
        "sample.pdf",
        ingest_func=lambda path, original_filename: {
            "document_id": "sample",
            "source_file": original_filename,
            "tmp_path_seen": str(path),
        },
    )

    current = ingest_jobs.get_ingest_job(job["job_id"])
    assert current["status"] == "completed"
    assert current["result"]["document_id"] == "sample"
    assert current["result"]["source_file"] == "sample.pdf"


def test_ingest_job_failure_records_error_and_deletes_temp_file(tmp_path):
    """run_ingest_job records failures and removes the temporary upload file."""
    source = tmp_path / "bad.pdf"
    source.write_bytes(b"%PDF-1.4\n%%EOF")
    job = ingest_jobs.create_ingest_job("bad.pdf")

    def fail_ingest(path, original_filename):
        raise RuntimeError("R2R unavailable")

    ingest_jobs.run_ingest_job(job["job_id"], source, "bad.pdf", ingest_func=fail_ingest)

    current = ingest_jobs.get_ingest_job(job["job_id"])
    assert current["status"] == "failed"
    assert current["error"] == "R2R unavailable"
    assert not source.exists()


def test_unknown_ingest_job_returns_none():
    """get_ingest_job returns None for missing job IDs."""
    assert ingest_jobs.get_ingest_job("missing") is None
