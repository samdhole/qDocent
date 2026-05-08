"""Tests for source document routes."""
from pathlib import Path
from unittest import mock

import pytest
from fastapi.testclient import TestClient

import apps.api.services.document_store as document_store_mod
from apps.api.main import app
from apps.api.services.document_store import write_document_manifest


@pytest.fixture
def client():
    return TestClient(app)


def test_get_source_pdf_returns_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, client: TestClient
):
    """GET /documents/{document_id}/source serves the stored source PDF."""
    monkeypatch.setattr(document_store_mod, "DOCUMENTS_DIR", tmp_path / "documents")
    doc_dir = tmp_path / "documents" / "doc123"
    doc_dir.mkdir(parents=True)
    (doc_dir / "report.pdf").write_bytes(b"%PDF-1.4 fake")

    response = client.get("/documents/doc123/source")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == b"%PDF-1.4 fake"


def test_get_source_pdf_returns_404_for_unknown_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, client: TestClient
):
    """GET /documents/{document_id}/source 404s when no source PDF exists."""
    monkeypatch.setattr(document_store_mod, "DOCUMENTS_DIR", tmp_path / "documents")

    response = client.get("/documents/missing/source")

    assert response.status_code == 404


def test_list_documents_returns_stored_source_pdfs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, client: TestClient
):
    """GET /documents returns stored source PDFs."""
    monkeypatch.setattr(document_store_mod, "DOCUMENTS_DIR", tmp_path / "documents")
    doc_dir = tmp_path / "documents" / "doc123"
    doc_dir.mkdir(parents=True)
    (doc_dir / "report.pdf").write_bytes(b"%PDF-1.4 fake")

    response = client.get("/documents")

    assert response.status_code == 200
    assert response.json()["documents"] == [
        {
            "document_id": "doc123",
            "source_file": "report.pdf",
            "source_url": "/documents/doc123/source",
            "size_bytes": len(b"%PDF-1.4 fake"),
            "updated_at": response.json()["documents"][0]["updated_at"],
        }
    ]


def test_delete_document_removes_stored_source_pdf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, client: TestClient
):
    """DELETE /documents/{document_id} removes local source storage."""
    monkeypatch.setattr(document_store_mod, "DOCUMENTS_DIR", tmp_path / "documents")
    doc_dir = tmp_path / "documents" / "doc123"
    doc_dir.mkdir(parents=True)
    (doc_dir / "report.pdf").write_bytes(b"%PDF-1.4 fake")

    response = client.delete("/documents/doc123")

    assert response.status_code == 200
    assert response.json() == {
        "status": "deleted",
        "document_id": "doc123",
        "r2r_delete": {"deleted": [], "failed": []},
    }
    assert not doc_dir.exists()


@mock.patch("apps.api.routes.documents.r2r_client.delete_r2r_documents")
def test_delete_document_removes_r2r_documents_when_manifest_has_ids(
    mock_delete_r2r,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
):
    """DELETE /documents/{document_id} deletes R2R documents when IDs are known."""
    monkeypatch.setattr(document_store_mod, "DOCUMENTS_DIR", tmp_path / "documents")
    doc_dir = tmp_path / "documents" / "doc123"
    doc_dir.mkdir(parents=True)
    (doc_dir / "report.pdf").write_bytes(b"%PDF-1.4 fake")
    write_document_manifest(
        "doc123",
        source_file="report.pdf",
        r2r_document_ids=["r2r-primary", "r2r-figures"],
    )
    mock_delete_r2r.return_value = {"deleted": ["r2r-primary", "r2r-figures"], "failed": []}

    response = client.delete("/documents/doc123")

    assert response.status_code == 200
    assert response.json()["r2r_delete"] == {
        "deleted": ["r2r-primary", "r2r-figures"],
        "failed": [],
    }
    mock_delete_r2r.assert_called_once_with(["r2r-primary", "r2r-figures"])
    assert not doc_dir.exists()


@mock.patch("apps.api.routes.documents.r2r_client.delete_r2r_documents")
def test_delete_document_succeeds_even_when_r2r_delete_fails(
    mock_delete_r2r,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    client: TestClient,
):
    """R2R cleanup failure is reported in response but does not block local deletion."""
    monkeypatch.setattr(document_store_mod, "DOCUMENTS_DIR", tmp_path / "documents")
    doc_dir = tmp_path / "documents" / "doc123"
    doc_dir.mkdir(parents=True)
    (doc_dir / "report.pdf").write_bytes(b"%PDF-1.4 fake")
    write_document_manifest(
        "doc123",
        source_file="report.pdf",
        r2r_document_ids=["r2r-primary"],
    )
    mock_delete_r2r.return_value = {"deleted": [], "failed": ["r2r-primary"]}

    response = client.delete("/documents/doc123")

    assert response.status_code == 200
    assert response.json()["r2r_delete"] == {"deleted": [], "failed": ["r2r-primary"]}
    assert not doc_dir.exists()  # local PDF deleted despite R2R failure


def test_delete_document_returns_404_for_unknown_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, client: TestClient
):
    """DELETE /documents/{document_id} 404s when no local source exists."""
    monkeypatch.setattr(document_store_mod, "DOCUMENTS_DIR", tmp_path / "documents")

    response = client.delete("/documents/missing")

    assert response.status_code == 404
