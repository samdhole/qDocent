# pattern: Imperative Shell
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from apps.api.services import r2r_client
from apps.api.services.document_store import (
    delete_source_document,
    load_chunks_manifest,
    load_document_manifest,
    list_source_documents,
    source_pdf_path,
)
from apps.api.services.question_generator import generate_questions

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


@router.get("/{document_id}/chunks")
def get_document_chunks(document_id: str) -> dict:
    """Return chunk metadata (bbox, page, section) for the source panel."""
    chunks = load_chunks_manifest(document_id)
    return {"document_id": document_id, "chunks": chunks or []}


@router.delete("/{document_id}")
def delete_document(document_id: str) -> dict:
    """Delete DocQuery's locally stored source PDF for a document."""
    manifest = load_document_manifest(document_id)
    r2r_ids = (manifest or {}).get("r2r_document_ids", [])
    r2r_delete: dict = {"deleted": [], "failed": []}
    if r2r_ids:
        r2r_delete = r2r_client.delete_r2r_documents(r2r_ids)
    deleted = delete_source_document(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No source PDF for '{document_id}'.")
    return {
        "status": "deleted",
        "document_id": document_id,
        "r2r_delete": r2r_delete,
    }


@router.get("/{document_id}/questions")
def get_document_questions(document_id: str) -> dict:
    """Generate suggested questions from a document's chunk previews via LLM."""
    chunks = load_chunks_manifest(document_id)
    if chunks is None:
        raise HTTPException(status_code=404, detail=f"No chunk manifest for '{document_id}'.")
    text_previews = [
        chunk["text_preview"]
        for chunk in chunks
        if isinstance(chunk.get("text_preview"), str) and chunk["text_preview"].strip()
    ]
    questions = generate_questions(text_previews)
    return {"document_id": document_id, "questions": questions}
