"""Tests for the portfolio RAGAS dataset."""
from pathlib import Path

import yaml

from packages.evals.run_ragas import load_dataset


DATASET_PATH = Path("packages/evals/eval_dataset.yaml")


def _question_items():
    return yaml.safe_load(DATASET_PATH.read_text(encoding="utf-8"))["questions"]


def test_eval_dataset_has_commercial_demo_breadth():
    """Dataset has enough scenarios to make a demo eval meaningful."""
    questions, references, ids = load_dataset(DATASET_PATH)

    assert len(questions) >= 10
    assert len(references) == len(questions)
    assert len(ids) == len(questions)
    assert len(set(ids)) == len(ids)


def test_eval_dataset_covers_answerable_and_refusal_cases():
    """Eval dataset includes policy, pricing, architecture, and refusal cases."""
    items = _question_items()
    categories = {item["category"] for item in items}

    assert {"policy", "pricing", "architecture", "refusal"} <= categories
    assert sum(1 for item in items if item["category"] == "refusal") >= 2
