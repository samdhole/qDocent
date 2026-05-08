# pattern: Imperative Shell
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from apps.api.services import r2r_client
from apps.api.services.document_store import (
    delete_source_document,
    load_document_manifest,
    list_source_documents,
    source_pdf_path,
)

router = APIRouter(prefix="/documents")


@router.get("")
def list_documents() -> dict:
    """List source PDFs stored by DocQuery."""
    return {"documents": list_source_documents()}


@router.get("/{document_id}/source")
def source_document(document_id: str) -> FileResponse:
    """Serve the original source PDF for a stored document."""
    path = source_pdf_path(document_id)
    if path is None:
        raise HTTPException(status_code=404, detail=f"No source PDF for '{document_id}'.")
    return FileResponse(path, media_type="application/pdf", filename=path.name)


@router.delete("/{document_id}")
def delete_document(document_id: str) -> dict:
    """Delete DocQuery's locally stored source PDF for a document."""
    manifest = load_document_manifest(document_id)
    r2r_ids = (manifest or {}).get("r2r_document_ids", [])
    r2r_delete: str | dict = "not_configured"
    if r2r_ids:
        try:
            r2r_delete = r2r_client.delete_r2r_documents(r2r_ids)
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    deleted = delete_source_document(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No source PDF for '{document_id}'.")
    return {
        "status": "deleted",
        "document_id": document_id,
        "r2r_delete": r2r_delete,
    }
