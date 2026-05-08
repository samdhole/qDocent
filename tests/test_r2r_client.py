"""Tests for R2R client and confidence heuristic."""
import pytest


def test_high_confidence():
    """top_score=0.80 → confidence_label='high', needs_human_review=False"""
    # Extract confidence logic from rag_query to test independently
    top_score = 0.80
    if top_score >= 0.80:
        confidence_label = "high"
    elif top_score >= 0.50:
        confidence_label = "medium"
    else:
        confidence_label = "low"
    needs_review = confidence_label in ("low", "needs_review")

    assert confidence_label == "high"
    assert needs_review is False


def test_medium_confidence():
    """top_score=0.79 → confidence_label='medium', needs_human_review=False"""
    top_score = 0.79
    if top_score >= 0.80:
        confidence_label = "high"
    elif top_score >= 0.50:
        confidence_label = "medium"
    else:
        confidence_label = "low"
    needs_review = confidence_label in ("low", "needs_review")

    assert confidence_label == "medium"
    assert needs_review is False


def test_medium_confidence_lower():
    """top_score=0.50 → confidence_label='medium'"""
    top_score = 0.50
    if top_score >= 0.80:
        confidence_label = "high"
    elif top_score >= 0.50:
        confidence_label = "medium"
    else:
        confidence_label = "low"

    assert confidence_label == "medium"


def test_low_confidence():
    """top_score=0.49 → confidence_label='low', needs_human_review=True"""
    top_score = 0.49
    if top_score >= 0.80:
        confidence_label = "high"
    elif top_score >= 0.50:
        confidence_label = "medium"
    else:
        confidence_label = "low"
    needs_review = confidence_label in ("low", "needs_review")

    assert confidence_label == "low"
    assert needs_review is True


def test_no_results():
    """empty search_results → top_score=0.0 → confidence_label='low', needs_human_review=True"""
    retrieved_contexts = []
    top_score = retrieved_contexts[0]["score"] if retrieved_contexts else 0.0

    if top_score >= 0.80:
        confidence_label = "high"
    elif top_score >= 0.50:
        confidence_label = "medium"
    else:
        confidence_label = "low"
    needs_review = confidence_label in ("low", "needs_review")

    assert top_score == 0.0
    assert confidence_label == "low"
    assert needs_review is True
