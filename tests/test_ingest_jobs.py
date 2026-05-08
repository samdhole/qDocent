"""Tests for async ingest job tracking."""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from apps.api.services import ingest_jobs
from apps.api.services.ingest_jobs import _JOBS


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
    _JOBS.clear()
    job = ingest_jobs.create_ingest_job("sample.pdf")
    job_id = job["job_id"]

    # Simulate a completed job 2 hours in the past
    two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)
    _JOBS[job_id]["status"] = "completed"
    _JOBS[job_id]["updated_at"] = two_hours_ago.isoformat()

    result = ingest_jobs.get_ingest_job(job_id)

    assert result is None
    assert job_id not in _JOBS


def test_expired_failed_job_is_pruned():
    """Terminal job (failed) older than 60 minutes is pruned and returns None."""
    _JOBS.clear()
    job = ingest_jobs.create_ingest_job("sample.pdf")
    job_id = job["job_id"]

    # Simulate a failed job 2 hours in the past
    two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)
    _JOBS[job_id]["status"] = "failed"
    _JOBS[job_id]["updated_at"] = two_hours_ago.isoformat()

    result = ingest_jobs.get_ingest_job(job_id)

    assert result is None
    assert job_id not in _JOBS


def test_non_terminal_job_is_never_pruned():
    """Non-terminal job (running) older than 60 minutes is NOT pruned."""
    _JOBS.clear()
    job = ingest_jobs.create_ingest_job("sample.pdf")
    job_id = job["job_id"]

    # Simulate a running job 2 hours in the past
    two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)
    _JOBS[job_id]["status"] = "running"
    _JOBS[job_id]["updated_at"] = two_hours_ago.isoformat()

    result = ingest_jobs.get_ingest_job(job_id)

    assert result is not None
    assert result["status"] == "running"
    assert job_id in _JOBS


def test_recent_completed_job_is_not_pruned():
    """Terminal job (completed) within 60 minutes is NOT pruned."""
    _JOBS.clear()
    job = ingest_jobs.create_ingest_job("sample.pdf")
    job_id = job["job_id"]

    # Simulate a completed job 30 minutes ago
    thirty_minutes_ago = datetime.now(timezone.utc) - timedelta(minutes=30)
    _JOBS[job_id]["status"] = "completed"
    _JOBS[job_id]["updated_at"] = thirty_minutes_ago.isoformat()

    result = ingest_jobs.get_ingest_job(job_id)

    assert result is not None
    assert result["status"] == "completed"
    assert job_id in _JOBS
