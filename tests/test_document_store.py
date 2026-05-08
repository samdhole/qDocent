"""Tests for persisted source PDF lookup."""
import os
from pathlib import Path

import pytest

import apps.api.services.document_store as document_store_mod
from apps.api.services.document_store import (
    delete_source_document,
    load_document_manifest,
    list_source_documents,
    save_source_pdf,
    source_pdf_path,
    write_document_manifest,
)


def test_save_source_pdf_uses_document_id_and_sanitized_filename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Uploaded PDFs are copied under data/documents/<document_id>/ safely."""
    monkeypatch.setattr(document_store_mod, "DOCUMENTS_DIR", tmp_path / "documents")
    source = tmp_path / "upload.pdf"
    source.write_bytes(b"%PDF-1.4 fake")

    saved = save_source_pdf(source, document_id="doc123", source_file="../Policy Report.pdf")

    assert saved == tmp_path / "documents" / "doc123" / "Policy_Report.pdf"
    assert saved.read_bytes() == b"%PDF-1.4 fake"


def test_source_pdf_path_returns_none_for_missing_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Unknown document IDs do not produce a path."""
    monkeypatch.setattr(document_store_mod, "DOCUMENTS_DIR", tmp_path / "documents")

    assert source_pdf_path("missing") is None


def test_source_pdf_path_returns_first_pdf_for_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Stored PDF for a document ID is discoverable by the route layer."""
    monkeypatch.setattr(document_store_mod, "DOCUMENTS_DIR", tmp_path / "documents")
    doc_dir = tmp_path / "documents" / "doc123"
    doc_dir.mkdir(parents=True)
    pdf = doc_dir / "report.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")

    assert source_pdf_path("doc123") == pdf


def test_list_source_documents_returns_stored_pdfs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Stored PDFs are listed newest first with source URLs."""
    monkeypatch.setattr(document_store_mod, "DOCUMENTS_DIR", tmp_path / "documents")
    upload_a = tmp_path / "a.pdf"
    upload_b = tmp_path / "b.pdf"
    upload_a.write_bytes(b"%PDF-1.4 alpha")
    upload_b.write_bytes(b"%PDF-1.4 beta")
    first = save_source_pdf(
        upload_a, document_id="doc_a", source_file="Alpha.pdf"
    )
    old_time = first.stat().st_mtime - 10
    os.utime(first, (old_time, old_time))
    second = save_source_pdf(
        upload_b, document_id="doc_b", source_file="Beta.pdf"
    )

    documents = list_source_documents()

    assert [d["document_id"] for d in documents] == ["doc_b", "doc_a"]
    assert documents[0]["source_file"] == "Beta.pdf"
    assert documents[0]["source_url"] == "/documents/doc_b/source"
    assert documents[0]["size_bytes"] == len(b"%PDF-1.4 beta")
    assert documents[0]["updated_at"]


def test_delete_source_document_removes_document_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Deleting a stored source removes its local document directory."""
    monkeypatch.setattr(document_store_mod, "DOCUMENTS_DIR", tmp_path / "documents")
    source = tmp_path / "upload.pdf"
    source.write_bytes(b"%PDF-1.4 fake")
    saved = save_source_pdf(source, document_id="doc123", source_file="report.pdf")

    deleted = delete_source_document("doc123")

    assert deleted is True
    assert not saved.exists()
    assert source_pdf_path("doc123") is None


def test_delete_source_document_returns_false_for_missing_document(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Deleting an unknown source reports that nothing was removed."""
    monkeypatch.setattr(document_store_mod, "DOCUMENTS_DIR", tmp_path / "documents")

    assert delete_source_document("missing") is False


def test_document_manifest_round_trips_r2r_ids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Document manifests persist R2R document IDs beside stored sources."""
    monkeypatch.setattr(document_store_mod, "DOCUMENTS_DIR", tmp_path / "documents")

    manifest = write_document_manifest(
        "doc123",
        source_file="report.pdf",
        r2r_document_ids=["r2r-primary", "r2r-figures"],
    )

    assert manifest == {
        "document_id": "doc123",
        "source_file": "report.pdf",
        "r2r_document_ids": ["r2r-primary", "r2r-figures"],
    }
    assert load_document_manifest("doc123") == manifest


def test_load_document_manifest_returns_none_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Missing manifest files are optional for older local sources."""
    monkeypatch.setattr(document_store_mod, "DOCUMENTS_DIR", tmp_path / "documents")

    assert load_document_manifest("missing") is None
