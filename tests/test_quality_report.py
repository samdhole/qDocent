"""Tests for quality report generation."""
from pathlib import Path

import pytest

from packages.ingestion.quality_report import generate_report


class TestGenerateReport:
    """Test generate_report() output and file generation."""

    @pytest.fixture
    def tmp_reports_dir(self, tmp_path, monkeypatch):
        """Override REPORTS_DIR to use temp directory."""
        from packages.ingestion import quality_report

        reports_dir = tmp_path / "ingestion"
        monkeypatch.setattr(quality_report, "REPORTS_DIR", reports_dir)
        return reports_dir

    def test_generate_report_required_fields(self, tmp_reports_dir):
        """Report should have all 9 required fields."""
        pages = [
            {
                "page_number": 1,
                "text": "Some text",
                "tables": [],
                "confidence": 100.0,
                "bbox": [0, 0, 612, 792],
            },
            {
                "page_number": 2,
                "text": "More text",
                "tables": [{"df": None}],  # Count tables
                "confidence": 100.0,
                "bbox": [0, 0, 612, 792],
            },
        ]
        chunks = [
            {"confidence": 0.9, "text": "chunk 1"},
            {"confidence": 0.85, "text": "chunk 2"},
        ]
        classifier_result = {
            "document_type": "general",
            "recommended_parser": "fast_text",
        }

        report = generate_report(
            document_id="test_doc",
            source_file="test.pdf",
            pages=pages,
            chunks=chunks,
            classifier_result=classifier_result,
        )

        # Check all required fields
        required_fields = {
            "document_id",
            "document_type",
            "parser_used",
            "pages",
            "chunks",
            "tables_detected",
            "figures_detected",
            "low_confidence_pages",
            "citation_coverage_estimate",
        }
        assert set(report.keys()) >= required_fields

        # Check field types and values
        assert report["document_id"] == "test_doc"
        assert report["document_type"] == "general"
        assert report["parser_used"] == "fast_text"
        assert report["pages"] == 2
        assert report["chunks"] == 2
        assert report["tables_detected"] == 1
        assert report["figures_detected"] == 0
        assert isinstance(report["low_confidence_pages"], list)
        assert isinstance(report["citation_coverage_estimate"], float)

    def test_low_confidence_page_threshold(self, tmp_reports_dir):
        """Pages with confidence < 70.0 should appear in low_confidence_pages."""
        pages = [
            {
                "page_number": 1,
                "text": "Text",
                "tables": [],
                "confidence": 50.0,  # Below threshold
            },
            {
                "page_number": 2,
                "text": "Text",
                "tables": [],
                "confidence": 70.0,  # At threshold (not low)
            },
            {
                "page_number": 3,
                "text": "Text",
                "tables": [],
                "confidence": 75.0,  # Above threshold
            },
        ]
        chunks = [
            {"confidence": 0.9, "text": "chunk 1"},
        ]
        classifier_result = {
            "document_type": "general",
            "recommended_parser": "fast_text",
        }

        report = generate_report(
            document_id="test",
            source_file="test.pdf",
            pages=pages,
            chunks=chunks,
            classifier_result=classifier_result,
        )

        # Page 1 should be in low_confidence_pages (50.0 < 70.0)
        assert 1 in report["low_confidence_pages"]
        # Page 2 and 3 should NOT be in low_confidence_pages
        assert 2 not in report["low_confidence_pages"]
        assert 3 not in report["low_confidence_pages"]

    def test_citation_coverage_estimate(self, tmp_reports_dir):
        """Citation coverage should be ratio of high-confidence chunks."""
        chunks = [
            {"confidence": 0.9, "text": "chunk 1"},   # high (>= 0.80)
            {"confidence": 0.85, "text": "chunk 2"},  # high
            {"confidence": 0.5, "text": "chunk 3"},   # low
        ]
        pages = [
            {
                "page_number": 1,
                "text": "Text",
                "tables": [],
                "confidence": 100.0,
            }
        ]
        classifier_result = {
            "document_type": "general",
            "recommended_parser": "fast_text",
        }

        report = generate_report(
            document_id="test",
            source_file="test.pdf",
            pages=pages,
            chunks=chunks,
            classifier_result=classifier_result,
        )

        # 2 high-confidence chunks out of 3 total = ~0.6667
        assert report["citation_coverage_estimate"] == pytest.approx(2 / 3, abs=0.01)

    def test_json_file_written(self, tmp_reports_dir):
        """JSON report file should be written to REPORTS_DIR."""
        pages = [
            {"page_number": 1, "text": "Text", "tables": [], "confidence": 100.0}
        ]
        chunks = [{"confidence": 0.9, "text": "chunk"}]
        classifier_result = {
            "document_type": "general",
            "recommended_parser": "fast_text",
        }

        generate_report(
            document_id="test_doc",
            source_file="test.pdf",
            pages=pages,
            chunks=chunks,
            classifier_result=classifier_result,
        )

        json_file = tmp_reports_dir / "test_doc.json"
        assert json_file.exists()

        # Should be valid JSON
        import json
        content = json.loads(json_file.read_text())
        assert content["document_id"] == "test_doc"

    def test_markdown_file_written(self, tmp_reports_dir):
        """Markdown report file should be written to REPORTS_DIR."""
        pages = [
            {"page_number": 1, "text": "Text", "tables": [], "confidence": 100.0}
        ]
        chunks = [{"confidence": 0.9, "text": "chunk"}]
        classifier_result = {
            "document_type": "general",
            "recommended_parser": "fast_text",
        }

        generate_report(
            document_id="test_doc",
            source_file="test.pdf",
            pages=pages,
            chunks=chunks,
            classifier_result=classifier_result,
        )

        md_file = tmp_reports_dir / "test_doc.md"
        assert md_file.exists()

        # Should contain markdown headers
        content = md_file.read_text()
        assert "# Ingestion Quality Report:" in content
        assert "## Summary" in content

    def test_warnings_section_with_low_confidence(self, tmp_reports_dir):
        """Warnings section should list low-confidence pages."""
        pages = [
            {"page_number": 1, "text": "Text", "tables": [], "confidence": 50.0},
            {"page_number": 2, "text": "Text", "tables": [], "confidence": 75.0},
        ]
        chunks = [{"confidence": 0.9, "text": "chunk"}]
        classifier_result = {
            "document_type": "general",
            "recommended_parser": "fast_text",
        }

        generate_report(
            document_id="test_doc",
            source_file="test.pdf",
            pages=pages,
            chunks=chunks,
            classifier_result=classifier_result,
        )

        md_file = tmp_reports_dir / "test_doc.md"
        content = md_file.read_text()

        # Should mention low-confidence page
        assert "Page 1" in content
        assert "low OCR confidence" in content

    def test_no_warnings_with_all_high_confidence(self, tmp_reports_dir):
        """Warnings section should say 'None' if all pages high confidence."""
        pages = [
            {"page_number": 1, "text": "Text", "tables": [], "confidence": 100.0},
            {"page_number": 2, "text": "Text", "tables": [], "confidence": 90.0},
        ]
        chunks = [{"confidence": 0.9, "text": "chunk"}]
        classifier_result = {
            "document_type": "general",
            "recommended_parser": "fast_text",
        }

        generate_report(
            document_id="test_doc",
            source_file="test.pdf",
            pages=pages,
            chunks=chunks,
            classifier_result=classifier_result,
        )

        md_file = tmp_reports_dir / "test_doc.md"
        content = md_file.read_text()

        # Should mention no warnings (check for core phrase, avoiding em-dash encoding issues)
        assert "all pages parsed with high confidence" in content
