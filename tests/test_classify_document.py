"""Tests for document classification module."""
from pathlib import Path

import pytest

from packages.ingestion.classify_document import (
    _classify_type,
    classify_document,
)


class TestClassifyType:
    """Test _classify_type() rule-based detection with synthetic inputs."""

    def test_table_heavy_threshold(self):
        """table_ratio >= 0.25 should return 'table_heavy'."""
        result = _classify_type("some generic text", table_ratio=0.25, has_columns=False)
        assert result == "table_heavy"

        result = _classify_type("some generic text", table_ratio=0.5, has_columns=False)
        assert result == "table_heavy"

    def test_contract_keywords(self):
        """Text containing contract keywords should return 'legal_contract'."""
        text = "This agreement outlines terms and conditions as per the governing law."
        result = _classify_type(text, table_ratio=0.0, has_columns=False)
        assert result == "legal_contract"

        text = "Indemnification clause in the MSA document."
        result = _classify_type(text, table_ratio=0.0, has_columns=False)
        assert result == "legal_contract"

    def test_paper_keywords(self):
        """Text containing paper keywords should return 'paper'."""
        text = "Abstract. Introduction. Methodology. Conclusion. References."
        result = _classify_type(text, table_ratio=0.0, has_columns=False)
        assert result == "paper"

        text = "doi: 10.1234/example. This work was published on arxiv."
        result = _classify_type(text, table_ratio=0.0, has_columns=False)
        assert result == "paper"

    def test_slide_keywords(self):
        """Text containing slide keywords should return 'slide_deck'."""
        text = "Agenda for today. Slide 1 overview. Click to edit master text."
        result = _classify_type(text, table_ratio=0.0, has_columns=False)
        assert result == "slide_deck"

        text = "Confidential — do not distribute. This is a presentation deck."
        result = _classify_type(text, table_ratio=0.0, has_columns=False)
        assert result == "slide_deck"

    def test_generic_fallback(self):
        """Text without keywords should return 'general'."""
        text = "This is a simple document with some basic information."
        result = _classify_type(text, table_ratio=0.0, has_columns=False)
        assert result == "general"

    def test_keywords_take_priority_over_table_ratio(self):
        """Keyword-based types take priority over the table_heavy structural heuristic."""
        # A contract with many tables is still a legal_contract
        text = "This is a contract with agreement terms."
        result = _classify_type(text, table_ratio=0.25, has_columns=False)
        assert result == "legal_contract"

    def test_paper_with_tables_classified_as_paper(self):
        """A research paper with >25% table pages must be classified as paper, not table_heavy."""
        text = "Abstract. Introduction. Methodology. Conclusion. References."
        result = _classify_type(text, table_ratio=0.5, has_columns=False)
        assert result == "paper"

    def test_table_heavy_fires_when_no_keyword_match(self):
        """table_heavy is the fallback for high-table documents with no keyword signature."""
        text = "Q1 revenue breakdown by region and segment."
        result = _classify_type(text, table_ratio=0.25, has_columns=False)
        assert result == "table_heavy"


class TestClassifyDocument:
    """Test classify_document() with a real sample PDF."""

    @pytest.fixture
    def sample_pdf(self):
        """Return path to sample PDF."""
        pdf_path = Path("data/sample_docs/company_policy.pdf")
        if not pdf_path.exists():
            pytest.skip(f"Sample PDF not found at {pdf_path}")
        return pdf_path

    def test_classify_document_required_fields(self, sample_pdf):
        """Result should have all 7 required fields."""
        result = classify_document(sample_pdf)

        # Check all required fields present
        required_keys = {
            "file_name",
            "is_scanned",
            "has_tables",
            "has_columns",
            "document_type",
            "recommended_template",
            "recommended_parser",
        }
        assert set(result.keys()) == required_keys

        # Check field types
        assert isinstance(result["file_name"], str)
        assert isinstance(result["is_scanned"], bool)
        assert isinstance(result["has_tables"], bool)
        assert isinstance(result["has_columns"], bool)
        assert isinstance(result["document_type"], str)
        assert isinstance(result["recommended_template"], str)
        assert isinstance(result["recommended_parser"], str)

        # Check document_type is valid
        assert result["document_type"] in {
            "general",
            "paper",
            "legal_contract",
            "table_heavy",
            "slide_deck",
            "manual",
        }

        # Check recommended_parser is valid
        assert result["recommended_parser"] in {
            "fast_text",
            "table_aware",
            "ocr",
        }

    def test_classify_document_file_name(self, sample_pdf):
        """Result file_name should match input filename."""
        result = classify_document(sample_pdf)
        assert result["file_name"] == sample_pdf.name
