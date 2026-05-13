# pattern: Imperative Shell
import ipaddress
import os
import shutil
import socket
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from apps.api.services import notebook_store, r2r_client

router = APIRouter(prefix="/notebooks", tags=["notebooks"])

_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx"}


def _is_safe_url(url: str) -> bool:
    """Return False if URL resolves to a private/loopback/link-local address.

    Prevents SSRF attacks by rejecting private IP ranges.
    """
    try:
        hostname = urlparse(url).hostname or ""
        for _, _, _, _, sockaddr in socket.getaddrinfo(hostname, None):
            ip = ipaddress.ip_address(sockaddr[0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        return True
    except Exception:
        return False


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


class UrlIngestBody(BaseModel):
    """Request body for URL ingestion."""

    url: str


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
    """Ingest a PDF, DOCX, or PPTX document into a notebook.

    The document is scoped to the notebook's R2R collection during ingestion.
    Membership is recorded in SQLite. This endpoint is synchronous — it blocks
    until ingestion completes and returns the full result. For async ingestion
    with progress polling, use POST /ingest/jobs instead (PDF only).

    Args:
        notebook_id: ID of the notebook to ingest into.
        file: PDF, DOCX, or PPTX file to ingest.

    Returns:
        Result dict with status, ingestion result, and document_id.

    Raises:
        HTTPException: 404 if notebook not found.
        HTTPException: 422 if file type is not accepted.
    """
    nb = notebook_store.get_notebook(notebook_id)
    if not nb:
        raise HTTPException(status_code=404, detail="Notebook not found")

    # Validate file type — 422 for non-accepted extensions
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Only {sorted(_ALLOWED_EXTENSIONS)} files are accepted. Got '{ext or 'no extension'}'.",
        )

    collection_id = nb.get("r2r_collection_id") or None

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp_path = tmp.name
        shutil.copyfileobj(file.file, tmp)

    try:
        if ext == ".pdf":
            # Validate PDF magic header to prevent non-PDF files with fake extensions
            with open(tmp_path, "rb") as f:
                header = f.read(5)
            if header != b"%PDF-":
                raise HTTPException(status_code=422, detail="File is not a valid PDF (invalid magic header)")
            result = r2r_client.ingest_file_with_pipeline(
                tmp_path,
                original_filename=filename,
                collection_id=collection_id,
            )
        else:
            # DOCX or PPTX — use ingest_source_with_pipeline
            result = r2r_client.ingest_source_with_pipeline(
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


@router.post("/{notebook_id}/ingest/url", status_code=201)
def ingest_notebook_url(notebook_id: str, body: UrlIngestBody) -> dict:
    """Ingest a web page URL into a notebook.

    The URL is fetched and converted to markdown via crawl4ai, then chunked.
    The document is scoped to the notebook's R2R collection during ingestion.
    Membership is recorded in SQLite.

    Args:
        notebook_id: ID of the notebook to ingest into.
        body: Request body with URL.

    Returns:
        Result dict with status, ingestion result, and document_id.

    Raises:
        HTTPException: 404 if notebook not found.
        HTTPException: 422 if URL is invalid.
        HTTPException: 502 if URL fetch fails.
    """
    nb = notebook_store.get_notebook(notebook_id)
    if not nb:
        raise HTTPException(status_code=404, detail="Notebook not found")

    url = body.url.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        raise HTTPException(status_code=422, detail="URL must start with http:// or https://")
    if not _is_safe_url(url):
        raise HTTPException(status_code=422, detail="URL resolves to a private or reserved IP address")

    collection_id = nb.get("r2r_collection_id") or None

    try:
        result = r2r_client.ingest_source_with_pipeline(
            url,
            original_filename=url,
            collection_id=collection_id,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {exc}") from exc

    # Record membership in SQLite
    document_id = (result or {}).get("document_id") or ""
    if document_id:
        notebook_store.add_document(notebook_id, document_id)

    return {"status": "ok", "result": result, "document_id": document_id}
