"""Tests for persisted source PDF lookup."""
import logging
import os
from pathlib import Path

import pytest

import apps.api.services.document_store as document_store_mod
from apps.api.services.document_store import (
    _safe_segment,
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


# Tests for _safe_segment() empty-input safety (arfix.AC3.1, arfix.AC3.2)


def test_safe_segment_raises_on_empty_string():
    """Empty string sanitizes to empty, raising ValueError."""
    with pytest.raises(ValueError, match="sanitizes to empty string"):
        _safe_segment("")


def test_safe_segment_raises_on_dot_only():
    """Dot-only string sanitizes to empty, raising ValueError."""
    with pytest.raises(ValueError, match="sanitizes to empty string"):
        _safe_segment(".")


def test_safe_segment_raises_on_slash_only():
    """Slash-only string sanitizes to empty, raising ValueError."""
    with pytest.raises(ValueError, match="sanitizes to empty string"):
        _safe_segment("/")


def test_safe_segment_raises_on_dots_only():
    """Multiple dots sanitize to empty, raising ValueError."""
    with pytest.raises(ValueError, match="sanitizes to empty string"):
        _safe_segment("...")


def test_safe_segment_raises_on_special_chars_only():
    """String with only special characters sanitizes to empty, raising ValueError."""
    with pytest.raises(ValueError, match="sanitizes to empty string"):
        _safe_segment("!@#$%")


def test_safe_segment_accepts_alphanumeric():
    """Alphanumeric strings pass through unchanged."""
    assert _safe_segment("abc123") == "abc123"


def test_safe_segment_accepts_with_allowed_chars():
    """Strings with allowed special chars (hyphen, underscore, dot) pass through."""
    assert _safe_segment("a-b_c.d") == "a-b_c.d"


def test_safe_segment_accepts_uuid_format():
    """UUID-format strings pass through unchanged."""
    assert _safe_segment("550e8400-e29b-41d4-a716-446655440000") == "550e8400-e29b-41d4-a716-446655440000"


def test_safe_segment_sanitizes_spaces_to_underscores():
    """Spaces and other disallowed chars are replaced with underscores."""
    assert _safe_segment("hello world") == "hello_world"


def test_safe_segment_strips_leading_trailing_dots():
    """Leading/trailing dots are stripped."""
    assert _safe_segment(".abc.") == "abc"


def test_safe_segment_strips_leading_trailing_underscores():
    """Leading/trailing underscores are stripped."""
    assert _safe_segment("_abc_") == "abc"


# Tests for load_document_manifest() schema validation (arfix.AC4.1, arfix.AC4.2, arfix.AC4.3)


def test_load_document_manifest_returns_none_on_corrupt_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    """Corrupt JSON in manifest.json returns None with warning logged."""
    monkeypatch.setattr(document_store_mod, "DOCUMENTS_DIR", tmp_path / "documents")
    doc_dir = tmp_path / "documents" / "doc123"
    doc_dir.mkdir(parents=True)
    (doc_dir / "manifest.json").write_text("not json", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="apps.api.services.document_store"):
        result = load_document_manifest("doc123")

    assert result is None
    assert "Corrupt manifest" in caplog.text


def test_load_document_manifest_returns_none_when_json_is_null(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    """Manifest with JSON null (valid JSON, not a dict) returns None with warning logged."""
    monkeypatch.setattr(document_store_mod, "DOCUMENTS_DIR", tmp_path / "documents")
    doc_dir = tmp_path / "documents" / "doc123"
    doc_dir.mkdir(parents=True)
    (doc_dir / "manifest.json").write_text("null", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="apps.api.services.document_store"):
        result = load_document_manifest("doc123")

    assert result is None
    assert "is not a JSON object" in caplog.text


def test_load_document_manifest_returns_none_when_json_is_array(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    """Manifest with JSON array (valid JSON, not a dict) returns None with warning logged."""
    monkeypatch.setattr(document_store_mod, "DOCUMENTS_DIR", tmp_path / "documents")
    doc_dir = tmp_path / "documents" / "doc123"
    doc_dir.mkdir(parents=True)
    (doc_dir / "manifest.json").write_text("[1, 2, 3]", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="apps.api.services.document_store"):
        result = load_document_manifest("doc123")

    assert result is None
    assert "is not a JSON object" in caplog.text


def test_load_document_manifest_returns_none_when_r2r_ids_is_null(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Manifest with r2r_document_ids set to null (JSON null) returns None."""
    monkeypatch.setattr(document_store_mod, "DOCUMENTS_DIR", tmp_path / "documents")
    doc_dir = tmp_path / "documents" / "doc123"
    doc_dir.mkdir(parents=True)
    (doc_dir / "manifest.json").write_text(
        '{"document_id": "doc123", "r2r_document_ids": null}',
        encoding="utf-8",
    )

    result = load_document_manifest("doc123")

    assert result is None


def test_load_document_manifest_returns_none_when_r2r_ids_is_string(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Manifest with r2r_document_ids as string instead of list returns None."""
    monkeypatch.setattr(document_store_mod, "DOCUMENTS_DIR", tmp_path / "documents")
    doc_dir = tmp_path / "documents" / "doc123"
    doc_dir.mkdir(parents=True)
    (doc_dir / "manifest.json").write_text(
        '{"document_id": "doc123", "r2r_document_ids": "abc"}',
        encoding="utf-8",
    )

    result = load_document_manifest("doc123")

    assert result is None


def test_load_document_manifest_returns_none_when_r2r_ids_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
):
    """Manifest missing r2r_document_ids field returns None."""
    monkeypatch.setattr(document_store_mod, "DOCUMENTS_DIR", tmp_path / "documents")
    doc_dir = tmp_path / "documents" / "doc123"
    doc_dir.mkdir(parents=True)
    (doc_dir / "manifest.json").write_text(
        '{"document_id": "doc123", "source_file": "report.pdf"}',
        encoding="utf-8",
    )

    with caplog.at_level(logging.WARNING, logger="apps.api.services.document_store"):
        result = load_document_manifest("doc123")

    assert result is None
    assert "missing valid r2r_document_ids" in caplog.text


def test_load_document_manifest_round_trips_with_valid_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Well-formed manifest round-trips correctly (unchanged behavior)."""
    monkeypatch.setattr(document_store_mod, "DOCUMENTS_DIR", tmp_path / "documents")

    manifest = write_document_manifest(
        "doc123",
        source_file="report.pdf",
        r2r_document_ids=["r2r-primary", "r2r-figures"],
    )

    loaded = load_document_manifest("doc123")

    assert loaded == manifest
    assert loaded is not None
    assert isinstance(loaded.get("r2r_document_ids"), list)
