"""Tests for R2R client behavior and confidence heuristic."""
from unittest import mock

import pytest

from apps.api.services.r2r_client_helpers import _label_from_score


def test_high_confidence():
    """top_score=0.80 -> confidence_label='high', needs_human_review=False."""
    confidence_label, needs_review = _label_from_score(0.80)
    assert confidence_label == "high"
    assert needs_review is False


def test_medium_boundary():
    """top_score=0.79 -> confidence_label='medium', needs_human_review=False."""
    confidence_label, needs_review = _label_from_score(0.79)
    assert confidence_label == "medium"
    assert needs_review is False


def test_medium_lower():
    """top_score=0.50 -> confidence_label='medium', needs_human_review=False."""
    confidence_label, needs_review = _label_from_score(0.50)
    assert confidence_label == "medium"
    assert needs_review is False


def test_low_boundary():
    """top_score=0.49 -> confidence_label='low', needs_human_review=True."""
    confidence_label, needs_review = _label_from_score(0.49)
    assert confidence_label == "low"
    assert needs_review is True


def test_no_results():
    """top_score=0.0 -> confidence_label='low', needs_human_review=True."""
    confidence_label, needs_review = _label_from_score(0.0)
    assert confidence_label == "low"
    assert needs_review is True


class TestIngestFileWithPipeline:
    """Test ingest_file_with_pipeline() pre-chunk and figure-manifest wiring."""

    @mock.patch("apps.api.services.r2r_client.write_document_manifest")
    @mock.patch("apps.api.services.r2r_client.ingest_prechunked_document")
    @mock.patch("apps.api.services.r2r_client.save_source_pdf")
    @mock.patch("apps.api.services.r2r_client.ingest_file")
    @mock.patch("apps.api.services.r2r_client.run_pipeline")
    def test_original_filename_passed_to_pipeline(
        self, mock_pipeline, mock_ingest, mock_save_source, mock_ingest_chunks, mock_manifest
    ):
        """original_filename is forwarded to run_pipeline as source_file."""
        mock_pipeline.return_value = {
            "report": {"document_id": "doc", "tables_detected": 0},
            "chunks": [{"text": "body", "document_id": "doc", "source_file": "report.pdf"}],
            "classifier": {},
            "figures": [],
            "figure_manifest": None,
        }
        mock_ingest_chunks.return_value = "ok"
        mock_ingest.return_value = "ok"

        from apps.api.services.r2r_client import ingest_file_with_pipeline

        ingest_file_with_pipeline("/tmp/tmpXXXX.pdf", original_filename="report.pdf")

        mock_pipeline.assert_called_once_with("/tmp/tmpXXXX.pdf", source_file="report.pdf")

    @mock.patch("apps.api.services.r2r_client.write_document_manifest")
    @mock.patch("apps.api.services.r2r_client.ingest_prechunked_document")
    @mock.patch("apps.api.services.r2r_client.save_source_pdf")
    @mock.patch("apps.api.services.r2r_client.run_pipeline")
    def test_pipeline_chunks_ingested_instead_of_raw_pdf(
        self, mock_pipeline, mock_save_source, mock_ingest_chunks, mock_manifest
    ):
        """Successful pipeline output is sent to R2R as pre-built DocQuery chunks."""
        chunks = [{"text": "Refunds are available.", "document_id": "doc", "source_file": "report.pdf"}]
        report = {"document_id": "doc", "source_file": "report.pdf", "tables_detected": 0}
        mock_pipeline.return_value = {
            "report": report,
            "chunks": chunks,
            "classifier": {},
            "figures": [],
            "figure_manifest": None,
        }
        mock_ingest_chunks.return_value = "ok"

        from apps.api.services.r2r_client import ingest_file_with_pipeline

        result = ingest_file_with_pipeline("/tmp/tmpXXXX.pdf", original_filename="report.pdf")

        mock_ingest_chunks.assert_called_once_with(chunks, report)
        mock_save_source.assert_called_once_with(
            "/tmp/tmpXXXX.pdf", document_id="doc", source_file="report.pdf"
        )
        assert result["ingestion_mode"] == "pre_chunked"
        assert result["source_url"] == "/documents/doc/source"

    @mock.patch("apps.api.services.r2r_client.write_document_manifest")
    @mock.patch("apps.api.services.r2r_client.ingest_prechunked_document")
    @mock.patch("apps.api.services.r2r_client.save_source_pdf")
    @mock.patch("apps.api.services.r2r_client.run_pipeline")
    def test_source_pdf_uses_original_filename_when_report_lacks_source_file(
        self, mock_pipeline, mock_save_source, mock_ingest_chunks, mock_manifest
    ):
        """Source storage uses upload filename when quality report omits source_file."""
        chunks = [{"text": "Refunds are available.", "document_id": "doc", "source_file": "report.pdf"}]
        report = {"document_id": "doc", "tables_detected": 0}
        mock_pipeline.return_value = {
            "report": report,
            "chunks": chunks,
            "classifier": {},
            "figures": [],
            "figure_manifest": None,
        }
        mock_ingest_chunks.return_value = "ok"

        from apps.api.services.r2r_client import ingest_file_with_pipeline

        result = ingest_file_with_pipeline("/tmp/tmpXXXX.pdf", original_filename="report.pdf")

        mock_save_source.assert_called_once_with(
            "/tmp/tmpXXXX.pdf", document_id="doc", source_file="report.pdf"
        )
        assert result["source_url"] == "/documents/doc/source"

    @mock.patch("apps.api.services.r2r_client.write_document_manifest")
    @mock.patch("apps.api.services.r2r_client.ingest_file")
    @mock.patch("apps.api.services.r2r_client.ingest_prechunked_document")
    @mock.patch("apps.api.services.r2r_client.save_source_pdf")
    @mock.patch("apps.api.services.r2r_client.run_pipeline")
    def test_figure_manifest_ingested_after_prechunked_doc(
        self, mock_pipeline, mock_save_source, mock_ingest_chunks, mock_ingest, mock_manifest
    ):
        """Figure manifest is ingested after the primary pre-chunked document."""
        mock_pipeline.return_value = {
            "report": {"document_id": "doc", "tables_detected": 0},
            "chunks": [{"text": "body", "document_id": "doc", "source_file": "test.pdf"}],
            "classifier": {},
            "figures": [{"figure_id": "fig1"}],
            "figure_manifest": "/data/figures/doc/figures.md",
        }
        mock_ingest_chunks.return_value = "ok"
        mock_ingest.return_value = "ok"

        from apps.api.services.r2r_client import ingest_file_with_pipeline

        result = ingest_file_with_pipeline("/tmp/tmpXXXX.pdf")

        mock_ingest_chunks.assert_called_once()
        mock_ingest.assert_called_once_with("/data/figures/doc/figures.md")
        assert result["figures_r2r"] is not None

    @mock.patch("apps.api.services.r2r_client.write_document_manifest")
    @mock.patch("apps.api.services.r2r_client.ingest_file")
    @mock.patch("apps.api.services.r2r_client.ingest_prechunked_document")
    @mock.patch("apps.api.services.r2r_client.save_source_pdf")
    @mock.patch("apps.api.services.r2r_client.run_pipeline")
    def test_figure_manifest_ingest_failure_is_nonfatal(
        self, mock_pipeline, mock_save_source, mock_ingest_chunks, mock_ingest, mock_manifest
    ):
        """Manifest ingest failure does not raise; returns figures_r2r=None."""
        mock_pipeline.return_value = {
            "report": {"document_id": "doc", "tables_detected": 0},
            "chunks": [{"text": "body", "document_id": "doc", "source_file": "test.pdf"}],
            "classifier": {},
            "figures": [{"figure_id": "fig1"}],
            "figure_manifest": "/data/figures/doc/figures.md",
        }
        mock_ingest_chunks.return_value = "ok"
        mock_ingest.side_effect = RuntimeError("R2R unavailable")

        from apps.api.services.r2r_client import ingest_file_with_pipeline

        result = ingest_file_with_pipeline("/tmp/tmpXXXX.pdf")

        assert result["figures_r2r"] is None
        assert "figures" in result

    @mock.patch("apps.api.services.r2r_client.write_document_manifest")
    @mock.patch("apps.api.services.r2r_client.ingest_file")
    @mock.patch("apps.api.services.r2r_client.ingest_prechunked_document")
    @mock.patch("apps.api.services.r2r_client.save_source_pdf")
    @mock.patch("apps.api.services.r2r_client.run_pipeline")
    def test_no_manifest_ingest_when_empty_figures(
        self, mock_pipeline, mock_save_source, mock_ingest_chunks, mock_ingest, mock_manifest
    ):
        """When figure_manifest is None, only pre-chunked document ingest runs."""
        mock_pipeline.return_value = {
            "report": {"document_id": "doc", "tables_detected": 0},
            "chunks": [{"text": "body", "document_id": "doc", "source_file": "test.pdf"}],
            "classifier": {},
            "figures": [],
            "figure_manifest": None,
        }
        mock_ingest_chunks.return_value = "ok"

        from apps.api.services.r2r_client import ingest_file_with_pipeline

        result = ingest_file_with_pipeline("/tmp/tmpXXXX.pdf")

        mock_ingest_chunks.assert_called_once()
        mock_ingest.assert_not_called()
        assert result["figures_r2r"] is None

    @mock.patch("apps.api.services.r2r_client.ingest_file")
    @mock.patch("apps.api.services.r2r_client.run_pipeline")
    def test_pipeline_failure_falls_back_to_raw_pdf(self, mock_pipeline, mock_ingest):
        """If pipeline fails, raw PDF ingest remains the fallback path."""
        mock_pipeline.side_effect = ValueError("parse failed")
        mock_ingest.return_value = "ok"

        from apps.api.services.r2r_client import ingest_file_with_pipeline

        result = ingest_file_with_pipeline("/tmp/tmpXXXX.pdf")

        mock_ingest.assert_called_once_with("/tmp/tmpXXXX.pdf")
        assert result["ingestion_mode"] == "raw_file_fallback"

    @mock.patch("apps.api.services.r2r_client.save_source_pdf")
    @mock.patch("apps.api.services.r2r_client.ingest_file")
    @mock.patch("apps.api.services.r2r_client.run_pipeline")
    def test_fallback_path_saves_source_pdf_when_pipeline_provides_document_id(
        self, mock_pipeline, mock_ingest, mock_save_source
    ):
        """When fallback path is taken and pipeline provided a document_id, save_source_pdf is called (arfix.AC6.1)."""
        mock_pipeline.return_value = {
            "report": {"document_id": "abc", "source_file": "test.pdf"},
            "chunks": [],  # Empty chunks trigger fallback
            "classifier": {},
            "figures": [],
            "figure_manifest": None,
        }
        mock_ingest.return_value = "ok"

        from apps.api.services.r2r_client import ingest_file_with_pipeline

        result = ingest_file_with_pipeline("/tmp/tmpXXXX.pdf")

        mock_save_source.assert_called_once_with(
            "/tmp/tmpXXXX.pdf", document_id="abc", source_file="test.pdf"
        )
        assert result["source_url"] == "/documents/abc/source"
        assert result["ingestion_mode"] == "raw_file_fallback"

    @mock.patch("apps.api.services.r2r_client.save_source_pdf")
    @mock.patch("apps.api.services.r2r_client.ingest_file")
    @mock.patch("apps.api.services.r2r_client.run_pipeline")
    def test_fallback_path_skips_save_source_pdf_when_pipeline_raises(
        self, mock_pipeline, mock_ingest, mock_save_source
    ):
        """When pipeline itself raises, save_source_pdf is NOT called (arfix.AC6.2)."""
        mock_pipeline.side_effect = ValueError("parse failed")
        mock_ingest.return_value = "ok"

        from apps.api.services.r2r_client import ingest_file_with_pipeline

        result = ingest_file_with_pipeline("/tmp/tmpXXXX.pdf")

        mock_save_source.assert_not_called()
        assert result["ingestion_mode"] == "raw_file_fallback"

    @mock.patch("apps.api.services.r2r_client.save_source_pdf")
    @mock.patch("apps.api.services.r2r_client.write_document_manifest")
    @mock.patch("apps.api.services.r2r_client.ingest_prechunked_document")
    @mock.patch("apps.api.services.r2r_client.run_pipeline")
    def test_chunk_validation_filters_invalid_chunks(
        self, mock_pipeline, mock_ingest_chunks, mock_manifest, mock_save_source
    ):
        """Chunks missing required fields are filtered out (arfix.AC7.1)."""
        valid_chunk = {"text": "Valid content", "document_id": "doc", "source_file": "test.pdf"}
        invalid_chunk = {"text": "", "document_id": "doc", "source_file": "test.pdf"}  # empty text
        mock_pipeline.return_value = {
            "report": {"document_id": "doc", "source_file": "test.pdf"},
            "chunks": [valid_chunk, invalid_chunk],
            "classifier": {},
            "figures": [],
            "figure_manifest": None,
        }
        mock_ingest_chunks.return_value = "ok"

        from apps.api.services.r2r_client import ingest_file_with_pipeline

        ingest_file_with_pipeline("/tmp/tmpXXXX.pdf")

        # Should be called with only the valid chunk, not the invalid one
        mock_ingest_chunks.assert_called_once()
        called_chunks = mock_ingest_chunks.call_args[0][0]
        assert len(called_chunks) == 1
        assert called_chunks[0]["text"] == "Valid content"

    @mock.patch("apps.api.services.r2r_client.save_source_pdf")
    @mock.patch("apps.api.services.r2r_client.ingest_file")
    @mock.patch("apps.api.services.r2r_client.run_pipeline")
    def test_all_invalid_chunks_falls_back_to_raw_pdf(
        self, mock_pipeline, mock_ingest, mock_save_source
    ):
        """When all chunks are invalid, fallback to raw ingest (arfix.AC7.2)."""
        invalid_chunk = {"text": "", "document_id": "doc", "source_file": "test.pdf"}
        mock_pipeline.return_value = {
            "report": {"document_id": "doc", "source_file": "test.pdf"},
            "chunks": [invalid_chunk],
            "classifier": {},
            "figures": [],
            "figure_manifest": None,
        }
        mock_ingest.return_value = "ok"

        from apps.api.services.r2r_client import ingest_file_with_pipeline

        result = ingest_file_with_pipeline("/tmp/tmpXXXX.pdf")

        mock_ingest.assert_called_once_with("/tmp/tmpXXXX.pdf")
        mock_save_source.assert_called_once_with(
            "/tmp/tmpXXXX.pdf", document_id="doc", source_file="test.pdf"
        )
        assert result["ingestion_mode"] == "raw_file_fallback"

    @mock.patch("apps.api.services.r2r_client.save_source_pdf")
    @mock.patch("apps.api.services.r2r_client.write_document_manifest")
    @mock.patch("apps.api.services.r2r_client.ingest_prechunked_document")
    @mock.patch("apps.api.services.r2r_client.run_pipeline")
    def test_valid_chunks_pass_through_unchanged(
        self, mock_pipeline, mock_ingest_chunks, mock_manifest, mock_save_source
    ):
        """Valid chunks with all required fields pass through unchanged (arfix.AC7.3)."""
        valid_chunks = [
            {"text": "Content 1", "document_id": "doc", "source_file": "test.pdf"},
            {"text": "Content 2", "document_id": "doc", "source_file": "test.pdf"},
        ]
        mock_pipeline.return_value = {
            "report": {"document_id": "doc", "source_file": "test.pdf"},
            "chunks": valid_chunks,
            "classifier": {},
            "figures": [],
            "figure_manifest": None,
        }
        mock_ingest_chunks.return_value = "ok"

        from apps.api.services.r2r_client import ingest_file_with_pipeline

        ingest_file_with_pipeline("/tmp/tmpXXXX.pdf")

        # Should be called with all valid chunks unchanged
        mock_ingest_chunks.assert_called_once()
        called_chunks = mock_ingest_chunks.call_args[0][0]
        assert len(called_chunks) == 2
        assert called_chunks == valid_chunks

    @mock.patch("apps.api.services.r2r_client.write_document_manifest")
    @mock.patch("apps.api.services.r2r_client.ingest_file")
    @mock.patch("apps.api.services.r2r_client.ingest_prechunked_document")
    @mock.patch("apps.api.services.r2r_client.save_source_pdf")
    @mock.patch("apps.api.services.r2r_client.run_pipeline")
    def test_manifest_records_r2r_document_ids(
        self, mock_pipeline, mock_save_source, mock_ingest_chunks, mock_ingest, mock_manifest
    ):
        """Ingest stores R2R IDs so delete can clean vectors later."""
        chunks = [{"text": "Refunds are available.", "document_id": "doc", "source_file": "report.pdf"}]
        report = {"document_id": "doc", "source_file": "report.pdf", "tables_detected": 0}
        primary = mock.Mock()
        primary.results.document_id = "r2r-primary"
        figures = mock.Mock()
        figures.results.id = "r2r-figures"
        mock_pipeline.return_value = {
            "report": report,
            "chunks": chunks,
            "classifier": {},
            "figures": [{"figure_id": "fig1"}],
            "figure_manifest": "/data/figures/doc/figures.md",
        }
        mock_ingest_chunks.return_value = primary
        mock_ingest.return_value = figures

        from apps.api.services.r2r_client import ingest_file_with_pipeline

        result = ingest_file_with_pipeline("/tmp/tmpXXXX.pdf", original_filename="report.pdf")

        mock_manifest.assert_called_once_with(
            "doc",
            source_file="report.pdf",
            r2r_document_ids=["r2r-primary", "r2r-figures"],
        )
        assert result["r2r_document_ids"] == ["r2r-primary", "r2r-figures"]

    @mock.patch("apps.api.services.r2r_client.write_chunks_manifest")
    @mock.patch("apps.api.services.r2r_client.write_document_manifest")
    @mock.patch("apps.api.services.r2r_client.save_source_pdf")
    @mock.patch("apps.api.services.r2r_client.ingest_prechunked_document")
    @mock.patch("apps.api.services.r2r_client.run_pipeline")
    def test_ingest_file_with_pipeline_writes_chunks_manifest_on_pre_chunked_path(
        self, mock_pipeline, mock_ingest_chunks, mock_save_source, mock_doc_manifest, mock_chunks_manifest
    ):
        """Task 2: write_chunks_manifest is called on pre-chunked path with correct document_id."""
        chunks = [{"text": "Content", "page_start": 1, "bbox": [0, 0, 100, 100], "document_id": "doc1", "source_file": "test.pdf"}]
        report = {"document_id": "doc1", "source_file": "test.pdf"}
        mock_pipeline.return_value = {
            "report": report,
            "chunks": chunks,
            "classifier": {},
            "figures": [],
            "figure_manifest": None,
        }
        mock_ingest_chunks.return_value = mock.Mock()

        from apps.api.services.r2r_client import ingest_file_with_pipeline

        ingest_file_with_pipeline("/tmp/tmpXXXX.pdf")

        mock_chunks_manifest.assert_called_once_with("doc1", chunks)

    @mock.patch("apps.api.services.r2r_client.write_chunks_manifest")
    @mock.patch("apps.api.services.r2r_client.write_document_manifest")
    @mock.patch("apps.api.services.r2r_client.save_source_pdf")
    @mock.patch("apps.api.services.r2r_client.ingest_file")
    @mock.patch("apps.api.services.r2r_client.run_pipeline")
    def test_ingest_file_with_pipeline_does_not_write_chunks_manifest_on_fallback_path(
        self, mock_pipeline, mock_ingest, mock_save_source, mock_doc_manifest, mock_chunks_manifest
    ):
        """Task 2: write_chunks_manifest is NOT called on fallback path (no chunks)."""
        mock_pipeline.return_value = {
            "report": {"document_id": "doc1", "source_file": "test.pdf"},
            "chunks": [],  # Empty chunks trigger fallback
            "classifier": {},
            "figures": [],
            "figure_manifest": None,
        }
        mock_ingest.return_value = "ok"

        from apps.api.services.r2r_client import ingest_file_with_pipeline

        ingest_file_with_pipeline("/tmp/tmpXXXX.pdf")

        mock_chunks_manifest.assert_not_called()


class TestIngestPrechunkedDocument:
    """Test ingest_prechunked_document() metadata handling."""

    @mock.patch("apps.api.services.r2r_client.get_client")
    def test_none_valued_metadata_fields_are_included(self, mock_client_fn):
        """When document_id and source_file are None, metadata includes None values (arfix.AC8.1)."""
        mock_client = mock.MagicMock()
        mock_client_fn.return_value = mock_client

        from apps.api.services.r2r_client import ingest_prechunked_document

        chunks = [{"text": "body", "document_id": "doc", "source_file": "test.pdf"}]
        report = {}  # No document_id or source_file, so both will be None

        ingest_prechunked_document(chunks, report)

        # Verify that documents.create was called with metadata containing None values
        mock_client.documents.create.assert_called_once()
        call_args = mock_client.documents.create.call_args
        metadata = call_args.kwargs["metadata"]

        # Metadata should include the keys even though values are None
        assert "docquery_document_id" in metadata
        assert "source_file" in metadata
        assert metadata["docquery_document_id"] is None
        assert metadata["source_file"] is None
        assert metadata["ingestion_mode"] == "docquery_pre_chunked"

    @mock.patch("apps.api.services.r2r_client.get_client")
    def test_passes_chunks_as_strings_with_citation_headers(self, mock_client_fn):
        """chunks_for_r2r output is passed verbatim to client.documents.create (arfix.AC15.1)."""
        mock_client = mock_client_fn.return_value
        mock_client.documents.create.return_value = {"results": {"id": "r2r-abc123"}}

        from apps.api.services.r2r_client import ingest_prechunked_document

        chunks = [
            {
                "document_id": "doc1",
                "source_file": "test.pdf",
                "page_start": 1,
                "page_end": 2,
                "section_path": "Intro",
                "text": "Some policy text here.",
            }
        ]
        report = {"document_id": "doc1", "source_file": "test.pdf"}

        ingest_prechunked_document(chunks, report)

        mock_client.documents.create.assert_called_once()
        call_kwargs = mock_client.documents.create.call_args.kwargs
        assert "chunks" in call_kwargs, "chunks kwarg must be passed"
        assert isinstance(call_kwargs["chunks"], list), "chunks must be a list"
        assert len(call_kwargs["chunks"]) == 1
        assert call_kwargs["chunks"][0].startswith("DocQuery Citation:"), (
            "each chunk string must begin with the citation header prefix"
        )

    @mock.patch("apps.api.services.r2r_client.get_client")
    def test_metadata_contains_required_fields(self, mock_client_fn):
        """metadata dict passed to R2R contains ingestion_mode, docquery_document_id, source_file (arfix.AC15.2)."""
        mock_client = mock_client_fn.return_value
        mock_client.documents.create.return_value = {}

        from apps.api.services.r2r_client import ingest_prechunked_document

        chunks = [{"document_id": "doc1", "source_file": "test.pdf", "text": "body"}]
        report = {"document_id": "doc1", "source_file": "test.pdf"}

        ingest_prechunked_document(chunks, report)

        call_kwargs = mock_client.documents.create.call_args.kwargs
        metadata = call_kwargs.get("metadata", {})
        assert metadata.get("ingestion_mode") == "docquery_pre_chunked"
        assert "docquery_document_id" in metadata
        assert metadata["docquery_document_id"] == "doc1"
        assert "source_file" in metadata
        assert metadata["source_file"] == "test.pdf"

    @mock.patch("apps.api.services.r2r_client.get_client")
    def test_raises_runtime_error_when_client_construction_fails(self, mock_client_fn):
        """RuntimeError is raised when R2R client cannot be constructed (arfix.AC15.3)."""
        import httpx

        mock_client_fn.side_effect = httpx.HTTPError("connection refused")

        from apps.api.services.r2r_client import ingest_prechunked_document

        chunks = [{"document_id": "d", "source_file": "f.pdf", "text": "t"}]
        with pytest.raises(RuntimeError, match="R2R unavailable"):
            ingest_prechunked_document(chunks, {})


class TestDeleteR2RDocuments:
    @mock.patch("apps.api.services.r2r_client.get_client")
    def test_delete_r2r_documents_calls_sdk_delete_for_each_id(self, mock_client_fn):
        """delete_r2r_documents delegates every known R2R ID to the SDK."""
        from apps.api.services.r2r_client import delete_r2r_documents

        result = delete_r2r_documents(["r2r-primary", "r2r-figures"])

        assert result == {"deleted": ["r2r-primary", "r2r-figures"], "failed": []}
        assert mock_client_fn.return_value.documents.delete.call_args_list == [
            mock.call("r2r-primary"),
            mock.call("r2r-figures"),
        ]

    @mock.patch("apps.api.services.r2r_client.get_client")
    def test_delete_r2r_documents_returns_failed_when_client_construction_fails(self, mock_client_fn):
        """AC11.1: Client construction failure returns all IDs in failed[], no raise."""
        import httpx

        mock_client_fn.side_effect = httpx.ConnectError("R2R server down")

        from apps.api.services.r2r_client import delete_r2r_documents

        result = delete_r2r_documents(["r2r-primary", "r2r-figures"])

        assert result == {"deleted": [], "failed": ["r2r-primary", "r2r-figures"]}

    @mock.patch("apps.api.services.r2r_client.get_client")
    def test_delete_r2r_documents_handles_partial_per_doc_failure(self, mock_client_fn):
        """AC11.2: Per-document deletion failure is caught; successful deletions proceed."""
        import httpx

        mock_client = mock.MagicMock()
        mock_client_fn.return_value = mock_client

        # First call raises, second succeeds
        mock_client.documents.delete.side_effect = [
            httpx.HTTPError("Delete failed"),
            None,  # succeeds
        ]

        from apps.api.services.r2r_client import delete_r2r_documents

        result = delete_r2r_documents(["r2r-primary", "r2r-figures"])

        assert result == {"deleted": ["r2r-figures"], "failed": ["r2r-primary"]}


class TestRagQueryFigures:
    """Test rag_query() response enrichment."""

    @mock.patch("apps.api.services.r2r_client.figures_for_response")
    @mock.patch("apps.api.services.r2r_client.get_client")
    def test_rag_query_includes_figures_key(self, mock_client_fn, mock_figures):
        """rag_query() return dict must contain 'figures' key."""
        mock_figures.return_value = []

        mock_response = mock.MagicMock()
        mock_inner = mock.MagicMock()
        mock_inner.generated_answer = "The answer."
        mock_inner.search_results = mock.MagicMock()
        mock_inner.search_results.chunk_search_results = []
        mock_response.results = mock_inner
        mock_client_fn.return_value.retrieval.rag.return_value = mock_response

        from apps.api.services.r2r_client import rag_query

        result = rag_query("test question")

        assert "figures" in result
        assert isinstance(result["figures"], list)

    @mock.patch("apps.api.services.r2r_client.figures_for_response")
    @mock.patch("apps.api.services.r2r_client.get_client")
    def test_rag_query_uses_docquery_citation_header(self, mock_client_fn, mock_figures):
        """rag_query recovers document/page metadata embedded in retrieved text."""
        mock_figures.return_value = []

        hit = mock.MagicMock()
        hit.id = "r2r-hit"
        hit.score = 0.91
        hit.metadata = {}
        hit.text = (
            "DocQuery Citation: document_id=doc; source_file=policy.pdf; "
            "page_start=4; page_end=4; section_path=Refunds; chunk_index=2\n\n"
            "Refund policy body."
        )
        mock_inner = mock.MagicMock()
        mock_inner.generated_answer = "The answer."
        mock_inner.search_results = mock.MagicMock()
        mock_inner.search_results.chunk_search_results = [hit]
        mock_response = mock.MagicMock()
        mock_response.results = mock_inner
        mock_client_fn.return_value.retrieval.rag.return_value = mock_response

        from apps.api.services.r2r_client import rag_query

        result = rag_query("refund?")

        assert result["citations"][0]["document"] == "policy.pdf"
        assert result["citations"][0]["page"] == 4
        assert result["citations"][0]["section"] == "Refunds"
        assert result["retrieved_contexts"][0]["text"] == "Refund policy body."

    @mock.patch("apps.api.services.r2r_client.figures_for_response")
    @mock.patch("apps.api.services.r2r_client.get_client")
    def test_rag_query_suppresses_legacy_unknown_citations_when_known_exists(
        self, mock_client_fn, mock_figures
    ):
        """Legacy raw-ingested hits do not pollute citations when DocQuery hits exist."""
        mock_figures.return_value = []

        known = mock.MagicMock()
        known.id = "known-hit"
        known.score = 0.91
        known.metadata = {}
        known.text = (
            "DocQuery Citation: document_id=doc; source_file=policy.pdf; "
            "page_start=4; page_end=4; section_path=Refunds; chunk_index=2\n\n"
            "Refund policy body."
        )
        legacy = mock.MagicMock()
        legacy.id = "legacy-hit"
        legacy.score = 0.9
        legacy.metadata = {}
        legacy.text = "Legacy raw-ingested duplicate text."

        mock_inner = mock.MagicMock()
        mock_inner.generated_answer = "The answer."
        mock_inner.search_results = mock.MagicMock()
        mock_inner.search_results.chunk_search_results = [known, legacy]
        mock_response = mock.MagicMock()
        mock_response.results = mock_inner
        mock_client_fn.return_value.retrieval.rag.return_value = mock_response

        from apps.api.services.r2r_client import rag_query

        result = rag_query("refund?")

        assert len(result["citations"]) == 1
        assert result["citations"][0]["document"] == "policy.pdf"

    @mock.patch("apps.api.services.r2r_client.figures_for_response")
    @mock.patch("apps.api.services.r2r_client.get_client")
    def test_rag_query_header_document_takes_precedence_over_meta(
        self, mock_client_fn, mock_figures
    ):
        """arfix.AC1.1: Header document wins over meta.source_file."""
        mock_figures.return_value = []

        hit = mock.MagicMock()
        hit.id = "r2r-hit"
        hit.score = 0.91
        hit.metadata = {"source_file": "meta_doc.pdf"}  # wrong source from R2R meta
        hit.text = (
            "DocQuery Citation: document_id=doc; source_file=header_doc.pdf; "
            "page_start=4; page_end=4; section_path=Refunds; chunk_index=2\n\n"
            "Body text."
        )
        mock_inner = mock.MagicMock()
        mock_inner.generated_answer = "The answer."
        mock_inner.search_results = mock.MagicMock()
        mock_inner.search_results.chunk_search_results = [hit]
        mock_response = mock.MagicMock()
        mock_response.results = mock_inner
        mock_client_fn.return_value.retrieval.rag.return_value = mock_response

        from apps.api.services.r2r_client import rag_query

        result = rag_query("question?")

        # Header should win: document should be header_doc.pdf, not meta_doc.pdf
        assert result["citations"][0]["document"] == "header_doc.pdf"

    @mock.patch("apps.api.services.r2r_client.figures_for_response")
    @mock.patch("apps.api.services.r2r_client.get_client")
    def test_rag_query_meta_fallback_when_no_header(
        self, mock_client_fn, mock_figures
    ):
        """arfix.AC1.2: Falls back to meta.source_file when no DocQuery header."""
        mock_figures.return_value = []

        hit = mock.MagicMock()
        hit.id = "r2r-hit"
        hit.score = 0.91
        hit.metadata = {"source_file": "fallback_doc.pdf"}
        hit.text = "Plain text with no DocQuery header."

        mock_inner = mock.MagicMock()
        mock_inner.generated_answer = "The answer."
        mock_inner.search_results = mock.MagicMock()
        mock_inner.search_results.chunk_search_results = [hit]
        mock_response = mock.MagicMock()
        mock_response.results = mock_inner
        mock_client_fn.return_value.retrieval.rag.return_value = mock_response

        from apps.api.services.r2r_client import rag_query

        result = rag_query("question?")

        assert result["citations"][0]["document"] == "fallback_doc.pdf"

    @mock.patch("apps.api.services.r2r_client.figures_for_response")
    @mock.patch("apps.api.services.r2r_client.get_client")
    def test_rag_query_header_fields_take_precedence_over_meta(
        self, mock_client_fn, mock_figures
    ):
        """arfix.AC1.3: Header page and section win over meta fields."""
        mock_figures.return_value = []

        hit = mock.MagicMock()
        hit.id = "r2r-hit"
        hit.score = 0.91
        hit.metadata = {"page_start": 10, "page_end": 11, "section_path": "Meta Section"}
        hit.text = (
            "DocQuery Citation: document_id=doc; source_file=doc.pdf; "
            "page_start=4; page_end=5; section_path=Intro; chunk_index=0\n\n"
            "Body text."
        )
        mock_inner = mock.MagicMock()
        mock_inner.generated_answer = "The answer."
        mock_inner.search_results = mock.MagicMock()
        mock_inner.search_results.chunk_search_results = [hit]
        mock_response = mock.MagicMock()
        mock_response.results = mock_inner
        mock_client_fn.return_value.retrieval.rag.return_value = mock_response

        from apps.api.services.r2r_client import rag_query

        result = rag_query("question?")

        # Header should win for all fields: page, page_end, section
        assert result["citations"][0]["page"] == 4
        assert result["citations"][0]["page_end"] == 5
        assert result["citations"][0]["section"] == "Intro"

    @mock.patch("apps.api.services.r2r_client.figures_for_response")
    @mock.patch("apps.api.services.r2r_client.get_client")
    def test_rag_query_includes_chunk_index_from_header(
        self, mock_client_fn, mock_figures
    ):
        """Task 1: chunk_index from DocQuery citation header is included in citations."""
        mock_figures.return_value = []

        hit = mock.MagicMock()
        hit.id = "r2r-hit"
        hit.score = 0.85
        hit.metadata = {"source_file": "policy.pdf", "page_start": 1}
        hit.text = (
            "DocQuery Citation: document_id=doc1; source_file=policy.pdf; "
            "page_start=1; page_end=1; section_path=Refunds; chunk_index=7\n\n"
            "Refund policy details."
        )
        mock_inner = mock.MagicMock()
        mock_inner.generated_answer = "The refund policy is 30 days."
        mock_inner.search_results = mock.MagicMock()
        mock_inner.search_results.chunk_search_results = [hit]
        mock_response = mock.MagicMock()
        mock_response.results = mock_inner
        mock_client_fn.return_value.retrieval.rag.return_value = mock_response

        from apps.api.services.r2r_client import rag_query

        result = rag_query("refund policy?")

        assert len(result["citations"]) == 1
        assert result["citations"][0]["chunk_index"] == 7

    @mock.patch("apps.api.services.r2r_client.figures_for_response")
    @mock.patch("apps.api.services.r2r_client.get_client")
    def test_rag_query_chunk_index_is_none_when_header_missing(
        self, mock_client_fn, mock_figures
    ):
        """Task 1: chunk_index is None when no DocQuery header."""
        mock_figures.return_value = []

        hit = mock.MagicMock()
        hit.id = "r2r-hit"
        hit.score = 0.85
        hit.metadata = {"source_file": "policy.pdf", "page_start": 1}
        hit.text = "Plain text with no DocQuery header."

        mock_inner = mock.MagicMock()
        mock_inner.generated_answer = "The answer."
        mock_inner.search_results = mock.MagicMock()
        mock_inner.search_results.chunk_search_results = [hit]
        mock_response = mock.MagicMock()
        mock_response.results = mock_inner
        mock_client_fn.return_value.retrieval.rag.return_value = mock_response

        from apps.api.services.r2r_client import rag_query

        result = rag_query("question?")

        assert len(result["citations"]) == 1
        assert result["citations"][0]["chunk_index"] is None


class TestRagQueryBracketRewrite:
    @mock.patch("apps.api.services.r2r_client.figures_for_response", return_value=[])
    @mock.patch("apps.api.services.r2r_client.get_client")
    def test_hex_markers_rewritten_to_ordinal(self, mock_client_fn, mock_figures):
        chunk_id = "a1b2c3d-0000-0000-0000-000000000000"

        mock_chunk = mock.MagicMock()
        mock_chunk.score = 0.9
        mock_chunk.text = "The policy content."
        mock_chunk.metadata = {
            "chunk_id": chunk_id,
            "source_file": "policy.pdf",
            "page_start": 1,
            "page_end": 1,
        }
        mock_chunk.id = chunk_id

        mock_agg = mock.MagicMock()
        mock_agg.chunk_search_results = [mock_chunk]
        mock_result = mock.MagicMock()
        mock_result.generated_answer = "The policy covers [a1b2c3d] events."
        mock_result.search_results = mock_agg

        mock_response = mock.MagicMock()
        mock_response.results = mock_result
        mock_client_fn.return_value.retrieval.rag.return_value = mock_response

        from apps.api.services.r2r_client import rag_query

        result = rag_query("What is the policy?")

        assert result["answer"] == "The policy covers [1] events."
        assert result["citations"][0]["chunk_id"] == chunk_id

    @mock.patch("apps.api.services.r2r_client.figures_for_response", return_value=[])
    @mock.patch("apps.api.services.r2r_client.get_client")
    def test_no_hex_markers_answer_unchanged(self, mock_client_fn, mock_figures):
        mock_chunk = mock.MagicMock()
        mock_chunk.score = 0.7
        mock_chunk.text = "Some content."
        mock_chunk.metadata = {"source_file": "doc.pdf"}
        mock_chunk.id = "bbbbbbbb-0000-0000-0000-000000000000"

        mock_agg = mock.MagicMock()
        mock_agg.chunk_search_results = [mock_chunk]
        mock_result = mock.MagicMock()
        mock_result.generated_answer = "The answer has no inline markers."
        mock_result.search_results = mock_agg

        mock_response = mock.MagicMock()
        mock_response.results = mock_result
        mock_client_fn.return_value.retrieval.rag.return_value = mock_response

        from apps.api.services.r2r_client import rag_query

        result = rag_query("What is it?")

        assert result["answer"] == "The answer has no inline markers."
        assert len(result["citations"]) == 1
        assert result["citations"][0]["chunk_id"] == "bbbbbbbb-0000-0000-0000-000000000000"

    @mock.patch("apps.api.services.r2r_client.figures_for_response", return_value=[])
    @mock.patch("apps.api.services.r2r_client.get_client")
    def test_empty_citations_answer_unchanged(self, mock_client_fn, mock_figures):
        mock_agg = mock.MagicMock()
        mock_agg.chunk_search_results = []
        mock_result = mock.MagicMock()
        mock_result.generated_answer = "No citations available [cccccccc]."
        mock_result.search_results = mock_agg

        mock_response = mock.MagicMock()
        mock_response.results = mock_result
        mock_client_fn.return_value.retrieval.rag.return_value = mock_response

        from apps.api.services.r2r_client import rag_query

        result = rag_query("Anything?")

        assert result["answer"] == "No citations available [cccccccc]."
        assert result["citations"] == []
