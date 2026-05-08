# pattern: Imperative Shell
import tempfile
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from apps.api.services import ingest_jobs
from apps.api.services import r2r_client

router = APIRouter()


@router.post("/ingest")
async def ingest(file: UploadFile) -> JSONResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        result = r2r_client.ingest_file_with_pipeline(tmp_path, original_filename=file.filename)
        return JSONResponse(content={"status": "ok", "result": result})
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.post("/ingest/jobs", status_code=202)
async def create_ingest_job(file: UploadFile, background_tasks: BackgroundTasks) -> JSONResponse:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    content = await file.read()
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        # NOTE: In-memory background tasks are not persisted. A process restart between
        # this 202 response and task execution will orphan tmp_path on disk.
        # Acceptable for demo; fix would require a persistent task queue.
        job = ingest_jobs.create_ingest_job(file.filename)
        background_tasks.add_task(
            ingest_jobs.run_ingest_job,
            job["job_id"],
            tmp_path,
            file.filename,
        )
        return JSONResponse(status_code=202, content=job)
    except Exception:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
        raise


@router.get("/ingest/jobs/{job_id}")
def get_ingest_job(job_id: str) -> dict:
    job = ingest_jobs.get_ingest_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Ingest job not found.")
    return job
