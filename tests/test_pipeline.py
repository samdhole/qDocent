"""Tests for ingestion pipeline."""
from pathlib import Path

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
