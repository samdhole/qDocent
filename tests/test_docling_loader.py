"""Tests for docling_loader — converts DOCX/PPTX to page dicts."""
import pytest
from pathlib import Path
from packages.ingestion.docling_loader import load_document_with_docling

FIXTURE_DOCX = Path("tests/fixtures/sample_policy.docx")


@pytest.mark.skipif(not FIXTURE_DOCX.exists(), reason="DOCX fixture not present")
class TestDoclingLoader:
    def test_returns_list_of_page_dicts(self):
        pages = load_document_with_docling(str(FIXTURE_DOCX))
        assert isinstance(pages, list)
        assert len(pages) >= 1

    def test_each_page_has_required_fields(self):
        pages = load_document_with_docling(str(FIXTURE_DOCX))
        required = {"page_number", "text", "tables", "confidence", "bbox", "text_lines", "parser"}
        for page in pages:
            assert required <= set(page.keys()), f"missing fields: {required - set(page.keys())}"

    def test_text_is_non_empty(self):
        pages = load_document_with_docling(str(FIXTURE_DOCX))
        all_text = " ".join(p["text"] for p in pages)
        assert "refund" in all_text.lower(), "expected fixture content in output"

    def test_parser_field_is_docling(self):
        pages = load_document_with_docling(str(FIXTURE_DOCX))
        assert all(p["parser"] == "docling" for p in pages)

    def test_bbox_is_synthetic_page_size(self):
        pages = load_document_with_docling(str(FIXTURE_DOCX))
        for p in pages:
            assert p["bbox"] == [0, 0, 612, 792], "DOCX pages use synthetic letter-page bbox"

    def test_text_lines_is_empty_list(self):
        # DOCX has no per-line bboxes — text_lines is always [] for Docling output
        pages = load_document_with_docling(str(FIXTURE_DOCX))
        for p in pages:
            assert p["text_lines"] == []
