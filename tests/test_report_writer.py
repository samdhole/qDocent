"""Tests for report writer service."""
from pathlib import Path
from unittest.mock import patch
import tempfile
from apps.api.services.report_writer import latest_eval_results


def test_latest_eval_results_empty(tmp_path, monkeypatch):
    """Returns [] when reports/evals/ is empty"""
    # Create a temp evals dir
    evals_dir = tmp_path / "evals"
    evals_dir.mkdir()

    # Monkeypatch the EVAL_DIR to use our temp dir
    import apps.api.services.report_writer as rw
    monkeypatch.setattr(rw, "EVAL_DIR", evals_dir)

    result = latest_eval_results()
    assert result == []


def test_latest_eval_results_single_csv(tmp_path, monkeypatch):
    """Returns rows from CSV when one exists"""
    evals_dir = tmp_path / "evals"
    evals_dir.mkdir()

    # Create a test CSV
    csv_path = evals_dir / "ragas_results_20260507_120000.csv"
    csv_path.write_text(
        "question_id,answer_relevancy,context_precision,faithfulness\n"
        "q1,0.85,0.90,0.88\n"
        "q2,0.79,0.75,0.82\n"
    )

    import apps.api.services.report_writer as rw
    monkeypatch.setattr(rw, "EVAL_DIR", evals_dir)

    result = latest_eval_results()
    assert len(result) == 2
    assert result[0]["question_id"] == "q1"
    assert result[1]["question_id"] == "q2"


def test_latest_eval_results_multiple_csvs(tmp_path, monkeypatch):
    """Returns rows from the LATEST CSV when multiple exist"""
    evals_dir = tmp_path / "evals"
    evals_dir.mkdir()

    # Create two CSVs with different timestamps
    csv1_path = evals_dir / "ragas_results_20260507_110000.csv"
    csv1_path.write_text(
        "question_id,answer_relevancy,context_precision,faithfulness\n"
        "q_old,0.70,0.65,0.68\n"
    )

    csv2_path = evals_dir / "ragas_results_20260507_120000.csv"
    csv2_path.write_text(
        "question_id,answer_relevancy,context_precision,faithfulness\n"
        "q_new,0.85,0.90,0.88\n"
    )

    import apps.api.services.report_writer as rw
    monkeypatch.setattr(rw, "EVAL_DIR", evals_dir)

    result = latest_eval_results()
    # Should return rows from the LATEST csv (sorted alphabetically, so csv2 is newest)
    assert len(result) == 1
    assert result[0]["question_id"] == "q_new"
