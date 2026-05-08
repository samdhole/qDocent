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
