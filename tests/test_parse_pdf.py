"""Tests for PDF parsing functions."""
from pathlib import Path

import pytest

from packages.ingestion.parse_pdf import _parse_fast_text, _parse_table_aware, parse_pdf


@pytest.fixture
def sample_pdf_path():
    """Path to a fixture PDF. Uses the first PDF found in data/sample_docs/ or data/documents/."""
    for pattern in ["data/sample_docs/*.pdf", "data/documents/**/*.pdf"]:
        pdfs = list(Path().glob(pattern))
        if pdfs:
            return str(pdfs[0])
    pytest.skip("No sample PDF available")


class TestParseFastText:
    """Test fast text parser."""

    def test_parse_fast_text_returns_list(self):
        """_parse_fast_text returns a list of dicts."""
        sample_doc = Path("data/sample_docs/company_policy.pdf")
        if not sample_doc.exists():
            pytest.skip("Sample doc not found; run scripts/create_sample_docs.py")

        result = _parse_fast_text(str(sample_doc))

        assert isinstance(result, list)
        assert len(result) > 0

    def test_parse_fast_text_has_required_keys(self):
        """Each result has text, page_number, and bbox."""
        sample_doc = Path("data/sample_docs/company_policy.pdf")
        if not sample_doc.exists():
            pytest.skip("Sample doc not found")

        result = _parse_fast_text(str(sample_doc))

        for item in result:
            assert "text" in item
            assert "page_number" in item
            assert "bbox" in item

    def test_parse_fast_text_extracts_content(self):
        """_parse_fast_text extracts readable text from policy document."""
        sample_doc = Path("data/sample_docs/company_policy.pdf")
        if not sample_doc.exists():
            pytest.skip("Sample doc not found")

        result = _parse_fast_text(str(sample_doc))

        # Should have extracted some text
        all_text = " ".join(item.get("text", "") for item in result)
        assert len(all_text) > 0


class TestParseTableAware:
    """Test table-aware parser."""

    def test_parse_table_aware_returns_list(self):
        """_parse_table_aware returns a list of dicts."""
        sample_doc = Path("data/sample_docs/pricing_table.pdf")
        if not sample_doc.exists():
            pytest.skip("Sample doc not found; run scripts/create_sample_docs.py")

        result = _parse_table_aware(str(sample_doc))

        assert isinstance(result, list)
        assert len(result) > 0

    def test_parse_table_aware_extracts_content(self):
        """_parse_table_aware extracts content from pricing table."""
        sample_doc = Path("data/sample_docs/pricing_table.pdf")
        if not sample_doc.exists():
            pytest.skip("Sample doc not found")

        result = _parse_table_aware(str(sample_doc))

        # Should extract some content
        all_content = " ".join(str(item.get("text", "")) for item in result)
        assert len(all_content) > 0

    def test_parse_table_aware_has_required_keys(self):
        """Results have required keys."""
        sample_doc = Path("data/sample_docs/pricing_table.pdf")
        if not sample_doc.exists():
            pytest.skip("Sample doc not found")

        result = _parse_table_aware(str(sample_doc))

        for item in result:
            # Should have text key at minimum
            assert "text" in item or "raw_table_markdown" in item


class TestTextLines:
    """parse_pdf must include text_lines with per-line tight bboxes."""

    def test_fast_text_page_has_text_lines(self, sample_pdf_path):
        pages = parse_pdf(sample_pdf_path, parser="fast_text")
        assert pages, "expected at least one page"
        page = pages[0]
        assert "text_lines" in page, "page dict must have 'text_lines' key"
        assert isinstance(page["text_lines"], list), "text_lines must be a list"

    def test_text_lines_have_bbox_fields(self, sample_pdf_path):
        pages = parse_pdf(sample_pdf_path, parser="fast_text")
        lines = pages[0]["text_lines"]
        if lines:  # skip if page has no extractable text
            line = lines[0]
            for key in ("text", "x0", "top", "x1", "bottom"):
                assert key in line, f"text_line missing key '{key}'"

    def test_table_aware_page_has_text_lines(self, sample_pdf_path):
        pages = parse_pdf(sample_pdf_path, parser="table_aware")
        assert "text_lines" in pages[0]

    def test_text_line_bbox_within_page(self, sample_pdf_path):
        pages = parse_pdf(sample_pdf_path, parser="fast_text")
        page = pages[0]
        page_bbox = page["bbox"]
        for line in page["text_lines"]:
            assert line["x0"] >= page_bbox[0] - 1, "line x0 must be >= page x0"
            assert line["top"] >= page_bbox[1] - 1, "line top must be >= page top"
            assert line["x1"] <= page_bbox[2] + 1, "line x1 must be <= page x1"
            assert line["bottom"] <= page_bbox[3] + 1, "line bottom must be <= page bottom"
