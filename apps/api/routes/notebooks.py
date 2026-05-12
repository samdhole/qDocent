# pattern: Imperative Shell
import os
import shutil
import tempfile
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from apps.api.services import notebook_store, r2r_client

router = APIRouter(prefix="/notebooks", tags=["notebooks"])


def resolve_collection_id(notebook_id: str | None) -> str | None:
    """Look up r2r_collection_id for notebook_id, raise 404 if not found.

    Returns None if notebook_id is None.
    """
    if not notebook_id:
        return None
    nb = notebook_store.get_notebook(notebook_id)
    if not nb:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return nb.get("r2r_collection_id") or None


class NotebookCreate(BaseModel):
    """Request body for creating a notebook."""

    name: str
    description: str | None = None


class NotebookUpdate(BaseModel):
    """Request body for updating a notebook."""

    name: str | None = None
    description: str | None = None


@router.get("")
def list_notebooks() -> list[dict]:
    """List all notebooks.

    Returns:
        List of notebook dictionaries, ordered by creation date.
    """
    return notebook_store.list_notebooks()


@router.post("", status_code=201)
def create_notebook(body: NotebookCreate) -> dict:
    """Create a new notebook.

    Args:
        body: NotebookCreate with name and optional description.

    Returns:
        Created notebook dictionary with id and r2r_collection_id.
    """
    return notebook_store.create_notebook(name=body.name, description=body.description)


@router.get("/{notebook_id}")
def get_notebook(notebook_id: str) -> dict:
    """Get a notebook by ID.

    Args:
        notebook_id: ID of the notebook to retrieve.

    Returns:
        Notebook dictionary.

    Raises:
        HTTPException: 404 if notebook not found.
    """
    nb = notebook_store.get_notebook(notebook_id)
    if not nb:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return nb


@router.patch("/{notebook_id}")
def update_notebook(notebook_id: str, body: NotebookUpdate) -> dict:
    """Update a notebook.

    Args:
        notebook_id: ID of the notebook to update.
        body: NotebookUpdate with fields to change (name, description).

    Returns:
        Updated notebook dictionary.

    Raises:
        HTTPException: 404 if notebook not found.
    """
    nb = notebook_store.update_notebook(
        notebook_id,
        **{k: v for k, v in body.model_dump().items() if v is not None},
    )
    if not nb:
        raise HTTPException(status_code=404, detail="Notebook not found")
    return nb


@router.delete("/{notebook_id}", status_code=204)
def delete_notebook(notebook_id: str) -> None:
    """Delete a notebook.

    Args:
        notebook_id: ID of the notebook to delete.

    Raises:
        HTTPException: 404 if notebook not found.
    """
    deleted = notebook_store.delete_notebook(notebook_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Notebook not found")


@router.get("/{notebook_id}/documents")
def list_notebook_documents(notebook_id: str) -> list[dict]:
    """List all documents in a notebook.

    Args:
        notebook_id: ID of the notebook.

    Returns:
        List of document membership records, ordered by addition date.

    Raises:
        HTTPException: 404 if notebook not found.
    """
    if not notebook_store.get_notebook(notebook_id):
        raise HTTPException(status_code=404, detail="Notebook not found")
    return notebook_store.list_documents(notebook_id)


@router.post("/{notebook_id}/documents", status_code=201)
def ingest_notebook_document(notebook_id: str, file: UploadFile = File(...)) -> dict:
    """Ingest a PDF document into a notebook.

    The document is scoped to the notebook's R2R collection during ingestion.
    Membership is recorded in SQLite.

    Args:
        notebook_id: ID of the notebook to ingest into.
        file: PDF file to ingest.

    Returns:
        Result dict with status, ingestion result, and document_id.

    Raises:
        HTTPException: 404 if notebook not found.
        HTTPException: 422 if file is not a PDF.
    """
    nb = notebook_store.get_notebook(notebook_id)
    if not nb:
        raise HTTPException(status_code=404, detail="Notebook not found")

    # Validate file type — 422 for non-PDF
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="Only PDF files are accepted")

    # Validate PDF magic header to prevent non-PDF files with fake extensions
    header = file.file.read(5)
    if header != b"%PDF-":
        raise HTTPException(status_code=422, detail="File is not a valid PDF (invalid magic header)")
    file.file.seek(0)  # Rewind to start for the actual ingest

    collection_id = resolve_collection_id(notebook_id)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name
        shutil.copyfileobj(file.file, tmp)

    try:
        result = r2r_client.ingest_file_with_pipeline(
            tmp_path,
            original_filename=filename,
            collection_id=collection_id,
        )
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)

    # Record membership in SQLite
    document_id = (result or {}).get("document_id") or ""
    if document_id:
        notebook_store.add_document(notebook_id, document_id)

    return {"status": "ok", "result": result, "document_id": document_id}
