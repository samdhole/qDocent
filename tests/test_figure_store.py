"""Tests for figure_store Functional Core module."""
import json
from pathlib import Path

import pytest

import apps.api.services.figure_store as figure_store_mod
from apps.api.services.figure_store import figures_for_response, load_figures


def _write_fixture_figures(figures_dir: Path, document_id: str, records: list[dict]) -> None:
    """Write synthetic figures.json for a document."""
    doc_dir = figures_dir / document_id
    doc_dir.mkdir(parents=True, exist_ok=True)
    (doc_dir / "figures.json").write_text(
        json.dumps(records, ensure_ascii=False), encoding="utf-8"
    )


def _figure(
    figure_id: str,
    source_file: str = "report.pdf",
    page_number: int = 1,
) -> dict:
    return {
        "content_type": "figure",
        "figure_id": figure_id,
        "document_id": "doc",
        "source_file": source_file,
        "page_number": page_number,
        "bbox": [0.0, 0.0, 100.0, 100.0],
        "asset_path": f"data/figures/doc/{figure_id}.png",
        "image_url": f"/figures/doc/{figure_id}.png",
        "caption": "",
        "ocr_text": "",
    }


class TestLoadFigures:
    """Test load_figures() with monkeypatched FIGURES_DIR."""

    def test_returns_empty_when_dir_missing(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Non-existent FIGURES_DIR returns [] without error."""
        monkeypatch.setattr(figure_store_mod, "FIGURES_DIR", tmp_path / "nonexistent")
        result = load_figures()
        assert result == []

    def test_loads_all_documents(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """load_figures() globs all */figures.json files."""
        figures_dir = tmp_path / "figures"
        monkeypatch.setattr(figure_store_mod, "FIGURES_DIR", figures_dir)

        _write_fixture_figures(figures_dir, "doc1", [_figure("doc1_p001_fig001_01", source_file="a.pdf")])
        _write_fixture_figures(figures_dir, "doc2", [_figure("doc2_p001_fig001_01", source_file="b.pdf")])

        result = load_figures()
        assert len(result) == 2

    def test_loads_specific_document(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """load_figures(document_id) loads only that document's figures."""
        figures_dir = tmp_path / "figures"
        monkeypatch.setattr(figure_store_mod, "FIGURES_DIR", figures_dir)

        _write_fixture_figures(figures_dir, "doc1", [_figure("doc1_p001_fig001_01")])
        _write_fixture_figures(figures_dir, "doc2", [_figure("doc2_p001_fig001_01")])

        result = load_figures("doc1")
        assert len(result) == 1
        assert result[0]["figure_id"] == "doc1_p001_fig001_01"

    def test_returns_empty_for_unknown_document(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """load_figures(unknown_id) returns []."""
        figures_dir = tmp_path / "figures"
        figures_dir.mkdir()
        monkeypatch.setattr(figure_store_mod, "FIGURES_DIR", figures_dir)
        result = load_figures("no_such_doc")
        assert result == []


class TestFiguresForResponse:
    """Test figures_for_response() matching and capping logic."""

    def test_empty_when_no_figures_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Missing FIGURES_DIR returns [] without error."""
        monkeypatch.setattr(figure_store_mod, "FIGURES_DIR", tmp_path / "missing")
        result = figures_for_response(
            citations=[{"document": "report.pdf", "page": 1}],
            retrieved_contexts=[],
        )
        assert result == []

    def test_stage2_page_match(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Figure on same (source_file, page_number) as a citation is returned."""
        figures_dir = tmp_path / "figures"
        monkeypatch.setattr(figure_store_mod, "FIGURES_DIR", figures_dir)
        fig = _figure("doc_p003_fig001_01", source_file="annual_report.pdf", page_number=3)
        _write_fixture_figures(figures_dir, "doc", [fig])

        result = figures_for_response(
            citations=[{"document": "annual_report.pdf", "page": 3}],
            retrieved_contexts=[],
        )

        assert len(result) == 1
        assert result[0]["figure_id"] == "doc_p003_fig001_01"

    def test_stage2_no_match_different_page(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Figure on different page than citation is not returned."""
        figures_dir = tmp_path / "figures"
        monkeypatch.setattr(figure_store_mod, "FIGURES_DIR", figures_dir)
        fig = _figure("doc_p003_fig001_01", source_file="report.pdf", page_number=3)
        _write_fixture_figures(figures_dir, "doc", [fig])

        result = figures_for_response(
            citations=[{"document": "report.pdf", "page": 5}],
            retrieved_contexts=[],
        )

        assert result == []

    def test_stage1_regex_match(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Figure ID in retrieved context text is matched in Stage 1."""
        figures_dir = tmp_path / "figures"
        monkeypatch.setattr(figure_store_mod, "FIGURES_DIR", figures_dir)
        fig = _figure("doc_p001_fig001_01", source_file="report.pdf", page_number=1)
        _write_fixture_figures(figures_dir, "doc", [fig])

        result = figures_for_response(
            citations=[],
            retrieved_contexts=[
                {"text": "## Figure ID: doc_p001_fig001_01\nContent type: figure\nPage: 1", "score": 0.9}
            ],
        )

        assert len(result) == 1
        assert result[0]["figure_id"] == "doc_p001_fig001_01"

    def test_stage1_ignores_low_score_incidental_figure_context(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Low-score figure sidecar hits do not surface unrelated figures."""
        figures_dir = tmp_path / "figures"
        monkeypatch.setattr(figure_store_mod, "FIGURES_DIR", figures_dir)
        fig = _figure("doc_p001_fig001_01", source_file="report.pdf", page_number=1)
        _write_fixture_figures(figures_dir, "doc", [fig])

        result = figures_for_response(
            citations=[],
            retrieved_contexts=[
                {"text": "## Figure ID: doc_p001_fig001_01\nContent type: figure\nPage: 1", "score": 0.45}
            ],
        )

        assert result == []

    def test_stage1_multiple_ids_in_single_chunk(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Multiple Figure IDs in one retrieved context chunk are all matched."""
        figures_dir = tmp_path / "figures"
        monkeypatch.setattr(figure_store_mod, "FIGURES_DIR", figures_dir)
        fig1 = _figure("doc_p001_fig001_01", source_file="report.pdf", page_number=1)
        fig2 = _figure("doc_p001_fig002_01", source_file="report.pdf", page_number=1)
        _write_fixture_figures(figures_dir, "doc", [fig1, fig2])

        result = figures_for_response(
            citations=[],
            retrieved_contexts=[
                {"text": "Compare Figure ID: doc_p001_fig001_01 with Figure ID: doc_p001_fig002_01", "score": 0.9}
            ],
        )

        assert len(result) == 2
        figure_ids = {f["figure_id"] for f in result}
        assert figure_ids == {"doc_p001_fig001_01", "doc_p001_fig002_01"}

    def test_deduplication_across_stages(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Figure matched by both stages appears only once."""
        figures_dir = tmp_path / "figures"
        monkeypatch.setattr(figure_store_mod, "FIGURES_DIR", figures_dir)
        fig = _figure("doc_p001_fig001_01", source_file="report.pdf", page_number=1)
        _write_fixture_figures(figures_dir, "doc", [fig])

        result = figures_for_response(
            citations=[{"document": "report.pdf", "page": 1}],
            retrieved_contexts=[
                {"text": "## Figure ID: doc_p001_fig001_01\nPage: 1", "score": 0.9}
            ],
        )

        assert len(result) == 1

    def test_limit_cap(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Result is capped at the specified limit."""
        figures_dir = tmp_path / "figures"
        monkeypatch.setattr(figure_store_mod, "FIGURES_DIR", figures_dir)

        figs = [
            _figure(f"doc_p00{i}_fig001_01", source_file="report.pdf", page_number=i)
            for i in range(1, 9)  # 8 figures
        ]
        _write_fixture_figures(figures_dir, "doc", figs)

        citations = [{"document": "report.pdf", "page": i} for i in range(1, 9)]
        result = figures_for_response(citations=citations, retrieved_contexts=[], limit=3)

        assert len(result) == 3

    def test_empty_citations_and_contexts(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Both empty inputs returns []."""
        figures_dir = tmp_path / "figures"
        figures_dir.mkdir()
        monkeypatch.setattr(figure_store_mod, "FIGURES_DIR", figures_dir)

        result = figures_for_response(citations=[], retrieved_contexts=[])
        assert result == []
