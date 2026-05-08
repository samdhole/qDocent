"""Tests for extract_figures_helpers pure functions."""
import types

import pytest

from packages.ingestion.extract_figures_helpers import (
    _CAPTION_RE,
    figure_id_from,
    nearest_caption,
)


def _rect(y0: float, y1: float) -> types.SimpleNamespace:
    """Minimal duck-typed rect with y0/y1 — no fitz required."""
    return types.SimpleNamespace(y0=y0, y1=y1)


class TestCaptionRe:
    """Test _CAPTION_RE compiled regex."""

    def test_matches_figure_colon(self):
        """'Figure 1:' should match."""
        assert _CAPTION_RE.match("Figure 1: Architecture overview")

    def test_matches_fig_dot(self):
        """'Fig. 2.' should match."""
        assert _CAPTION_RE.match("Fig. 2. Data flow diagram")

    def test_matches_fig_no_dot(self):
        """'fig 3' (lowercase, no dot) should match."""
        assert _CAPTION_RE.match("fig 3 - system diagram")

    def test_matches_figure_uppercase(self):
        """'FIGURE 4:' should match (case-insensitive)."""
        assert _CAPTION_RE.match("FIGURE 4: Pipeline overview")

    def test_no_match_body_text(self):
        """Normal body text should not match."""
        assert not _CAPTION_RE.match("The following diagram illustrates the flow.")

    def test_no_match_table_label(self):
        """'Table 1:' should not match — only figures."""
        assert not _CAPTION_RE.match("Table 1: Summary statistics")

    def test_no_match_empty(self):
        """Empty string should not match."""
        assert not _CAPTION_RE.match("")


class TestFigureIdFrom:
    """Test figure_id_from() determinism and formatting."""

    def test_output_format(self):
        """ID should follow {doc}_p{page:03d}_fig{n:03d}_{r:02d} pattern."""
        result = figure_id_from("my_doc", 1, 1, 1)
        assert result == "my_doc_p001_fig001_01"

    def test_zero_padded_page(self):
        """Page 12 should be zero-padded to 3 digits."""
        result = figure_id_from("doc", 12, 1, 1)
        assert result == "doc_p012_fig001_01"

    def test_zero_padded_image(self):
        """Image 5, rect 3 should be zero-padded."""
        result = figure_id_from("doc", 1, 5, 3)
        assert result == "doc_p001_fig005_03"

    def test_deterministic(self):
        """Calling twice with same inputs returns identical ID."""
        a = figure_id_from("report", 3, 2, 1)
        b = figure_id_from("report", 3, 2, 1)
        assert a == b

    def test_different_inputs_different_ids(self):
        """Different page numbers produce different IDs."""
        a = figure_id_from("doc", 1, 1, 1)
        b = figure_id_from("doc", 2, 1, 1)
        assert a != b


class TestNearestCaption:
    """Test nearest_caption() distance logic and filtering."""

    def _make_block(self, y0: float, y1: float, text: str) -> tuple:
        """Return a minimal fitz text block tuple: (x0, y0, x1, y1, text)."""
        return (0.0, y0, 100.0, y1, text)

    def test_returns_caption_within_threshold(self):
        """Caption 100 px below rect should be returned."""
        rect = _rect(y0=200, y1=300)
        blocks = [self._make_block(305, 320, "Figure 1: My chart")]
        assert nearest_caption(blocks, rect) == "Figure 1: My chart"

    def test_ignores_caption_beyond_threshold(self):
        """Caption > 160 px away should be ignored."""
        rect = _rect(y0=200, y1=300)
        blocks = [self._make_block(470, 490, "Figure 1: Far away")]
        assert nearest_caption(blocks, rect) == ""

    def test_picks_closer_of_two_captions(self):
        """When two captions are within threshold, the closer one wins."""
        rect = _rect(y0=200, y1=300)
        blocks = [
            self._make_block(310, 325, "Figure 1: Closer"),
            self._make_block(350, 365, "Figure 2: Farther"),
        ]
        assert nearest_caption(blocks, rect) == "Figure 1: Closer"

    def test_ignores_non_caption_blocks(self):
        """Body text blocks should not be returned as captions."""
        rect = _rect(y0=200, y1=300)
        blocks = [self._make_block(305, 320, "This is body text, not a caption.")]
        assert nearest_caption(blocks, rect) == ""

    def test_empty_blocks(self):
        """No blocks should return empty string without error."""
        rect = _rect(y0=200, y1=300)
        assert nearest_caption([], rect) == ""

    def test_normalises_whitespace(self):
        """Extra whitespace in caption text should be normalised."""
        rect = _rect(y0=200, y1=300)
        blocks = [self._make_block(305, 320, "  Figure  1:   My  chart  ")]
        result = nearest_caption(blocks, rect)
        assert result == "Figure 1: My chart"
