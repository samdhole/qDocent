"""Tests for ingestion pipeline."""
from pathlib import Path
from unittest.mock import patch

import pytest

from packages.ingestion.pipeline import run_pipeline


class TestPipeline:
    """Test ingestion pipeline end-to-end."""

    def test_pipeline_processes_sample_doc(self):
        """Pipeline successfully processes company_policy.pdf."""
        sample_doc = Path("data/sample_docs/company_policy.pdf")
        if not sample_doc.exists():
            pytest.skip("Sample doc not found; run scripts/create_sample_docs.py")

        result = run_pipeline(str(sample_doc))

        # Verify result structure
        assert isinstance(result, dict)
        assert "chunks" in result
        assert "report" in result
        assert "classifier" in result
        assert "document_id" in result["report"]

    def test_pipeline_chunks_have_full_schema(self):
        """Each chunk in pipeline output has all 9 schema fields."""
        sample_doc = Path("data/sample_docs/company_policy.pdf")
        if not sample_doc.exists():
            pytest.skip("Sample doc not found")

        result = run_pipeline(str(sample_doc))
        chunks = result.get("chunks", [])

        required_fields = {
            "document_id",
            "source_file",
            "page_start",
            "page_end",
            "section_path",
            "bbox",
            "parser",
            "chunk_template",
            "confidence",
        }

        # Skip test if no chunks generated
        if not chunks:
            pytest.skip("No chunks generated from sample doc")

        for chunk in chunks:
            for field in required_fields:
                assert field in chunk, f"Missing field '{field}' in chunk"

    def test_pipeline_creates_ingestion_report_files(self):
        """Pipeline creates JSON and MD report files."""
        sample_doc = Path("data/sample_docs/company_policy.pdf")
        if not sample_doc.exists():
            pytest.skip("Sample doc not found")

        result = run_pipeline(str(sample_doc))
        document_id = result.get("report", {}).get("document_id")

        if not document_id:
            pytest.skip("No document_id in result")

        # Both JSON and MD files should exist
        json_report = Path("reports/ingestion") / f"{document_id}.json"
        md_report = Path("reports/ingestion") / f"{document_id}.md"

        assert json_report.exists(), f"JSON report not found at {json_report}"
        assert md_report.exists(), f"MD report not found at {md_report}"

    def test_pipeline_report_has_required_fields(self):
        """Report JSON contains expected quality metrics."""
        sample_doc = Path("data/sample_docs/company_policy.pdf")
        if not sample_doc.exists():
            pytest.skip("Sample doc not found")

        result = run_pipeline(str(sample_doc))
        report = result.get("report", {})

        # Check for expected fields
        assert "document_id" in report
        assert isinstance(report.get("tables_detected", 0), int)
        assert "document_type" in report

    def test_pipeline_returns_figures_key(self):
        """run_pipeline return dict must include 'figures' key (list)."""
        sample_doc = Path("data/sample_docs/company_policy.pdf")
        if not sample_doc.exists():
            pytest.skip("Sample doc not found; run scripts/create_sample_docs.py")

        result = run_pipeline(str(sample_doc))

        assert "figures" in result
        assert isinstance(result["figures"], list)

    def test_pipeline_returns_figure_manifest_key(self):
        """run_pipeline return dict must include 'figure_manifest' key (str or None)."""
        sample_doc = Path("data/sample_docs/company_policy.pdf")
        if not sample_doc.exists():
            pytest.skip("Sample doc not found; run scripts/create_sample_docs.py")

        result = run_pipeline(str(sample_doc))

        assert "figure_manifest" in result
        assert result["figure_manifest"] is None or isinstance(result["figure_manifest"], str)

    def test_figures_detected_matches_figures_list(self):
        """quality_report['figures_detected'] must equal len(result['figures'])."""
        sample_doc = Path("data/sample_docs/company_policy.pdf")
        if not sample_doc.exists():
            pytest.skip("Sample doc not found; run scripts/create_sample_docs.py")

        result = run_pipeline(str(sample_doc))

        assert result["report"]["figures_detected"] == len(result["figures"])

    def test_pipeline_source_file_param(self):
        """source_file param flows into chunk records instead of the temp path."""
        sample_doc = Path("data/sample_docs/company_policy.pdf")
        if not sample_doc.exists():
            pytest.skip("Sample doc not found; run scripts/create_sample_docs.py")

        result = run_pipeline(str(sample_doc), source_file="original_upload.pdf")

        # AC6.3: original filename must appear in every chunk record, not a temp path
        assert len(result["chunks"]) > 0, "Expected at least one chunk from sample doc"
        for chunk in result["chunks"]:
            assert chunk.get("source_file") == "original_upload.pdf", (
                f"chunk source_file={chunk.get('source_file')!r}, expected 'original_upload.pdf'"
            )


class TestRunPipelineForSource:
    """run_pipeline_for_source routes DOCX/URL to the right loader."""

    def _make_pages(self):
        return [
            {
                "page_number": 1,
                "text": "This is a policy document with refund details.",
                "tables": [],
                "confidence": 100.0,
                "bbox": [0, 0, 612, 792],
                "text_lines": [],
                "parser": "docling",
            }
        ]

    def test_docx_routes_to_docling(self, tmp_path):
        fake_docx = tmp_path / "test.docx"
        fake_docx.write_bytes(b"PK")  # minimal zip magic bytes
        with patch("packages.ingestion.docling_loader.load_document_with_docling", return_value=self._make_pages()) as mock_load:
            from packages.ingestion.pipeline import run_pipeline_for_source
            result = run_pipeline_for_source(str(fake_docx), source_file="test.docx")
        mock_load.assert_called_once_with(str(fake_docx))
        assert "chunks" in result
        assert "report" in result
        assert result["figures"] == []
        assert result["figure_manifest"] is None

    def test_url_routes_to_web_loader(self):
        with patch("packages.ingestion.web_loader.load_url", return_value=self._make_pages()) as mock_load:
            from packages.ingestion.pipeline import run_pipeline_for_source
            result = run_pipeline_for_source("https://example.com/docs", source_file="example.com")
        mock_load.assert_called_once_with("https://example.com/docs")
        assert "chunks" in result
        assert result["figures"] == []

    def test_pdf_raises_value_error(self, tmp_path):
        """PDF files must go through run_pipeline, not run_pipeline_for_source."""
        fake_pdf = tmp_path / "test.pdf"
        fake_pdf.write_bytes(b"%PDF-")
        from packages.ingestion.pipeline import run_pipeline_for_source
        with pytest.raises(ValueError, match="PDF files must use run_pipeline"):
            run_pipeline_for_source(str(fake_pdf), source_file="test.pdf")


class TestMakeDocumentId:
    """Test _make_document_id() for URL collision prevention."""

    def test_url_document_ids_are_unique(self):
        """Two URLs with same stem produce different document_ids."""
        from packages.ingestion.pipeline import _make_document_id

        url1 = "https://example.com/docs"
        url2 = "https://other.com/docs"

        id1 = _make_document_id("docs", path_or_url=url1)
        id2 = _make_document_id("docs", path_or_url=url2)

        assert id1 != id2, f"URLs with same stem should produce different IDs: {id1} vs {id2}"
        assert "docs" in id1, "ID should contain the stem"
        assert "docs" in id2, "ID should contain the stem"

    def test_file_based_document_ids_unchanged(self):
        """File-based source IDs still work as before."""
        from packages.ingestion.pipeline import _make_document_id

        id1 = _make_document_id("report.pdf")
        id2 = _make_document_id("report.pdf")

        assert id1 == id2, "Same filename should produce same ID"
        assert id1 == "report"
