# pattern: Imperative Shell
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Callable
from uuid import uuid4

from apps.api.services import r2r_client

IngestFunc = Callable[[str, str], dict[str, Any]]

_JOBS: dict[str, dict[str, Any]] = {}
_LOCK = Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_ingest_job(filename: str) -> dict[str, Any]:
    job_id = uuid4().hex
    job = {
        "job_id": job_id,
        "filename": filename,
        "status": "queued",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "result": None,
        "error": None,
    }
    with _LOCK:
        _JOBS[job_id] = job
    return dict(job)


def get_ingest_job(job_id: str) -> dict[str, Any] | None:
    with _LOCK:
        job = _JOBS.get(job_id)
        return dict(job) if job else None


def _update_job(job_id: str, **changes: Any) -> None:
    with _LOCK:
        if job_id not in _JOBS:
            return
        _JOBS[job_id] = {**_JOBS[job_id], **changes, "updated_at": _now_iso()}


def run_ingest_job(
    job_id: str,
    tmp_path: Path,
    original_filename: str,
    ingest_func: IngestFunc | None = None,
) -> None:
    _update_job(job_id, status="running")
    try:
        if ingest_func is None:
            ingest_func = r2r_client.ingest_file_with_pipeline
        result = ingest_func(str(tmp_path), original_filename=original_filename)
        _update_job(job_id, status="completed", result=result, error=None)
    except RuntimeError as exc:
        _update_job(job_id, status="failed", error=str(exc), result=None)
    finally:
        tmp_path.unlink(missing_ok=True)
