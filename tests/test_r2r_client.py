"""Tests for R2R client behavior and confidence heuristic."""
from unittest import mock

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
    @mock.patch("apps.api.services.r2r_client.run_pipeline")
    def test_original_filename_passed_to_pipeline(
        self, mock_pipeline, mock_save_source, mock_ingest_chunks, mock_manifest
    ):
        """original_filename is forwarded to run_pipeline as source_file."""
        mock_pipeline.return_value = {
            "report": {"document_id": "doc", "tables_detected": 0},
            "chunks": [{"text": "body"}],
            "classifier": {},
            "figures": [],
            "figure_manifest": None,
        }
        mock_ingest_chunks.return_value = "ok"

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
        chunks = [{"text": "Refunds are available.", "source_file": "report.pdf"}]
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
        chunks = [{"text": "Refunds are available.", "source_file": "report.pdf"}]
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
            "chunks": [{"text": "body"}],
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
            "chunks": [{"text": "body"}],
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
            "chunks": [{"text": "body"}],
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

    @mock.patch("apps.api.services.r2r_client.write_document_manifest")
    @mock.patch("apps.api.services.r2r_client.ingest_file")
    @mock.patch("apps.api.services.r2r_client.ingest_prechunked_document")
    @mock.patch("apps.api.services.r2r_client.save_source_pdf")
    @mock.patch("apps.api.services.r2r_client.run_pipeline")
    def test_manifest_records_r2r_document_ids(
        self, mock_pipeline, mock_save_source, mock_ingest_chunks, mock_ingest, mock_manifest
    ):
        """Ingest stores R2R IDs so delete can clean vectors later."""
        chunks = [{"text": "Refunds are available.", "source_file": "report.pdf"}]
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


class TestDeleteR2RDocuments:
    @mock.patch("apps.api.services.r2r_client._client")
    def test_delete_r2r_documents_calls_sdk_delete_for_each_id(self, mock_client_fn):
        """delete_r2r_documents delegates every known R2R ID to the SDK."""
        from apps.api.services.r2r_client import delete_r2r_documents

        result = delete_r2r_documents(["r2r-primary", "r2r-figures"])

        assert result == {"deleted": ["r2r-primary", "r2r-figures"], "failed": []}
        assert mock_client_fn.return_value.documents.delete.call_args_list == [
            mock.call("r2r-primary"),
            mock.call("r2r-figures"),
        ]


class TestRagQueryFigures:
    """Test rag_query() response enrichment."""

    @mock.patch("apps.api.services.r2r_client.figures_for_response")
    @mock.patch("apps.api.services.r2r_client._client")
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
    @mock.patch("apps.api.services.r2r_client._client")
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
    @mock.patch("apps.api.services.r2r_client._client")
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
