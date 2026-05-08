import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile
from fastapi.responses import JSONResponse

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
        result = r2r_client.ingest_file(tmp_path)
        return JSONResponse(content={
            "status": "ok",
            "document_id": getattr(result, "id", None),
            "message": "Document ingested successfully"
        })
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)
