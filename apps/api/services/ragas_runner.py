"""Thin orchestration wrapper around packages/evals/run_ragas.py."""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from packages.evals.run_ragas import load_dataset, run_eval

load_dotenv()

DATASET_PATH = Path("packages/evals/eval_dataset.yaml")
REPORTS_DIR = Path("reports/evals")
R2R_BASE_URL = os.getenv("R2R_BASE_URL", "http://localhost:7272")
EVAL_MODEL = os.getenv("RAGAS_EVAL_MODEL", "gpt-4o-mini")


def run_and_save() -> Path:
    """Run RAGAS eval, save CSV, return the output path."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    results = run_eval(
        r2r_base_url=R2R_BASE_URL,
        eval_model=EVAL_MODEL,
        dataset_path=DATASET_PATH,
    )
    df = results.to_pandas()
    _, _, ids = load_dataset(DATASET_PATH)
    df.insert(0, "question_id", ids)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = REPORTS_DIR / f"ragas_results_{timestamp}.csv"
    df.to_csv(out_path, index=False)
    return out_path
