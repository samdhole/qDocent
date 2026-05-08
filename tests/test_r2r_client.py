"""Tests for R2R client and confidence heuristic."""
from apps.api.services.r2r_client_helpers import _label_from_score


def test_high_confidence():
    """top_score=0.80 → confidence_label='high', needs_human_review=False"""
    confidence_label, needs_review = _label_from_score(0.80)
    assert confidence_label == "high"
    assert needs_review is False


def test_medium_boundary():
    """top_score=0.79 → confidence_label='medium', needs_human_review=False"""
    confidence_label, needs_review = _label_from_score(0.79)
    assert confidence_label == "medium"
    assert needs_review is False


def test_medium_lower():
    """top_score=0.50 → confidence_label='medium', needs_human_review=False"""
    confidence_label, needs_review = _label_from_score(0.50)
    assert confidence_label == "medium"
    assert needs_review is False


def test_low_boundary():
    """top_score=0.49 → confidence_label='low', needs_human_review=True"""
    confidence_label, needs_review = _label_from_score(0.49)
    assert confidence_label == "low"
    assert needs_review is True


def test_no_results():
    """top_score=0.0 → confidence_label='low', needs_human_review=True"""
    confidence_label, needs_review = _label_from_score(0.0)
    assert confidence_label == "low"
    assert needs_review is True


from unittest import mock


class TestIngestFileWithPipeline:
    """Test ingest_file_with_pipeline() figure manifest wiring."""

    @mock.patch("apps.api.services.r2r_client.ingest_file")
    @mock.patch("apps.api.services.r2r_client.run_pipeline")
    def test_original_filename_passed_to_pipeline(self, mock_pipeline, mock_ingest):
        """original_filename is forwarded to run_pipeline as source_file."""
        mock_pipeline.return_value = {
            "report": {"document_id": "doc", "tables_detected": 0},
            "chunks": [],
            "classifier": {},
            "figures": [],
            "figure_manifest": None,
        }
        mock_ingest.return_value = "ok"

        from apps.api.services.r2r_client import ingest_file_with_pipeline
        ingest_file_with_pipeline("/tmp/tmpXXXX.pdf", original_filename="report.pdf")

        mock_pipeline.assert_called_once_with("/tmp/tmpXXXX.pdf", source_file="report.pdf")

    @mock.patch("apps.api.services.r2r_client.ingest_file")
    @mock.patch("apps.api.services.r2r_client.run_pipeline")
    def test_figure_manifest_ingested_after_pdf(self, mock_pipeline, mock_ingest):
        """Figure manifest is ingested as a second ingest_file call after PDF."""
        mock_pipeline.return_value = {
            "report": {"document_id": "doc", "tables_detected": 0},
            "chunks": [],
            "classifier": {},
            "figures": [{"figure_id": "fig1"}],
            "figure_manifest": "/data/figures/doc/figures.md",
        }
        mock_ingest.return_value = "ok"

        from apps.api.services.r2r_client import ingest_file_with_pipeline
        result = ingest_file_with_pipeline("/tmp/tmpXXXX.pdf")

        assert mock_ingest.call_count == 2
        calls = [c.args[0] for c in mock_ingest.call_args_list]
        assert "/tmp/tmpXXXX.pdf" in calls
        assert "/data/figures/doc/figures.md" in calls
        assert result["figures_r2r"] is not None

    @mock.patch("apps.api.services.r2r_client.ingest_file")
    @mock.patch("apps.api.services.r2r_client.run_pipeline")
    def test_figure_manifest_ingest_failure_is_nonfatal(self, mock_pipeline, mock_ingest):
        """Manifest ingest failure does not raise — returns figures_r2r=None."""
        mock_pipeline.return_value = {
            "report": {"document_id": "doc", "tables_detected": 0},
            "chunks": [],
            "classifier": {},
            "figures": [{"figure_id": "fig1"}],
            "figure_manifest": "/data/figures/doc/figures.md",
        }

        def ingest_side_effect(path):
            if "figures.md" in path:
                raise RuntimeError("R2R unavailable")
            return "ok"

        mock_ingest.side_effect = ingest_side_effect

        from apps.api.services.r2r_client import ingest_file_with_pipeline
        result = ingest_file_with_pipeline("/tmp/tmpXXXX.pdf")

        assert result["figures_r2r"] is None
        assert "figures" in result

    @mock.patch("apps.api.services.r2r_client.ingest_file")
    @mock.patch("apps.api.services.r2r_client.run_pipeline")
    def test_no_manifest_ingest_when_empty_figures(self, mock_pipeline, mock_ingest):
        """When figure_manifest is None (empty figures list), only one ingest_file call."""
        mock_pipeline.return_value = {
            "report": {"document_id": "doc", "tables_detected": 0},
            "chunks": [],
            "classifier": {},
            "figures": [],
            "figure_manifest": None,
        }
        mock_ingest.return_value = "ok"

        from apps.api.services.r2r_client import ingest_file_with_pipeline
        result = ingest_file_with_pipeline("/tmp/tmpXXXX.pdf")

        mock_ingest.assert_called_once_with("/tmp/tmpXXXX.pdf")
        assert result["figures_r2r"] is None


class TestRagQueryFigures:
    """Test that rag_query() returns 'figures' key."""

    @mock.patch("apps.api.services.r2r_client.figures_for_response")
    @mock.patch("apps.api.services.r2r_client._client")
    def test_rag_query_includes_figures_key(self, mock_client_fn, mock_figures):
        """rag_query() return dict must contain 'figures' key."""
        mock_figures.return_value = []

        # Set up mock R2R response
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
