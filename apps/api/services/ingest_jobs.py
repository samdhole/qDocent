# pattern: Imperative Shell
import logging
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from apps.api.services import ingest_job_store, r2r_client

log = logging.getLogger(__name__)

IngestFunc = Callable[[str, str], dict[str, Any]]


def create_ingest_job(filename: str) -> dict[str, Any]:
    job_id = uuid4().hex
    ingest_job_store.create_job(job_id, filename)
    return ingest_job_store.get_job(job_id)


def get_ingest_job(job_id: str) -> dict[str, Any] | None:
    return ingest_job_store.get_job(job_id)


def run_ingest_job(
    job_id: str,
    tmp_path: Path,
    original_filename: str,
    ingest_func: IngestFunc | None = None,
) -> None:
    job_log = logging.LoggerAdapter(log, {"job_id": job_id})
    ingest_job_store.update_job(job_id, status="running")
    try:
        if ingest_func is None:
            ingest_func = r2r_client.ingest_file_with_pipeline
        result = ingest_func(str(tmp_path), original_filename=original_filename)
        ingest_job_store.update_job(job_id, status="completed", result=result, error=None)
        job_log.info("Ingest completed for '%s'", original_filename)
    except Exception as exc:
        # Catch all exceptions (not just RuntimeError) so job status is always updated
        job_log.warning("Ingest failed for '%s': %s", original_filename, exc)
        ingest_job_store.update_job(job_id, status="failed", error=str(exc), result=None)
    finally:
        tmp_path.unlink(missing_ok=True)
