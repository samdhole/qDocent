"""Tests for async ingest job tracking."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from apps.api.services import ingest_jobs, ingest_job_store


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Redirect ingest_job_store._DB_PATH to a temporary test database."""
    db_file = tmp_path / "test_jobs.db"
    monkeypatch.setattr("apps.api.services.ingest_job_store._DB_PATH", db_file)
    yield db_file


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


def test_expired_completed_job_is_pruned():
    """Terminal job (completed) older than 60 minutes is pruned and returns None."""
    job = ingest_jobs.create_ingest_job("sample.pdf")
    job_id = job["job_id"]

    two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)
    ingest_job_store.update_job(job_id, status="completed", updated_at=two_hours_ago.isoformat())

    assert ingest_jobs.get_ingest_job(job_id) is None


def test_expired_failed_job_is_pruned():
    """Terminal job (failed) older than 60 minutes is pruned and returns None."""
    job = ingest_jobs.create_ingest_job("sample.pdf")
    job_id = job["job_id"]

    two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)
    ingest_job_store.update_job(job_id, status="failed", updated_at=two_hours_ago.isoformat())

    assert ingest_jobs.get_ingest_job(job_id) is None


def test_non_terminal_job_is_never_pruned():
    """Non-terminal job (running) older than 60 minutes is NOT pruned."""
    job = ingest_jobs.create_ingest_job("sample.pdf")
    job_id = job["job_id"]

    two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)
    ingest_job_store.update_job(job_id, status="running", updated_at=two_hours_ago.isoformat())

    result = ingest_jobs.get_ingest_job(job_id)
    assert result is not None
    assert result["status"] == "running"


def test_recent_completed_job_is_not_pruned():
    """Terminal job (completed) within 60 minutes is NOT pruned."""
    job = ingest_jobs.create_ingest_job("sample.pdf")
    job_id = job["job_id"]

    thirty_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=30)
    ingest_job_store.update_job(job_id, status="completed", updated_at=thirty_minutes_ago.isoformat())

    result = ingest_jobs.get_ingest_job(job_id)
    assert result is not None
    assert result["status"] == "completed"


def test_is_expired_handles_none_updated_at():
    """get_job returns the job (not pruned) when updated_at is None."""
    job = ingest_jobs.create_ingest_job("sample.pdf")
    job_id = job["job_id"]

    ingest_job_store.update_job(job_id, status="completed", updated_at=None)

    result = ingest_jobs.get_ingest_job(job_id)
    assert result is not None  # safe fallback — None updated_at is not expired
