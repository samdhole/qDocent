"""Read eval and ingestion reports from disk for API routes."""
# pattern: Imperative Shell
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

EVAL_DIR = Path("reports/evals")
INGESTION_DIR = Path("reports/ingestion")


def latest_eval_results() -> list[dict]:
    """Return rows from the most recent ragas_results_*.csv as dicts."""
    csvs = sorted(EVAL_DIR.glob("ragas_results_*.csv"))
    if not csvs:
        return []
    df = pd.read_csv(csvs[-1])
    return df.to_dict(orient="records")


def ingestion_report(document_id: str) -> dict | None:
    """Return parsed ingestion report JSON for a document, or None."""
    path = INGESTION_DIR / f"{document_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
