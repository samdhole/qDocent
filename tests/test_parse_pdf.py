"""Tests for PDF parsing functions."""
from pathlib import Path

import pytest

from packages.ingestion.parse_pdf import _parse_fast_text, _parse_table_aware


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
