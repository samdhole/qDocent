"""Summarize the latest RAGAS results CSV and print a markdown table."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

REPORTS_DIR = Path("reports/evals")
TARGETS = {
    "faithfulness": 0.85,
    "context_precision": 0.75,
    "answer_relevancy": 0.80,
}


def latest_csv(reports_dir: Path = REPORTS_DIR) -> Path:
    csvs = sorted(reports_dir.glob("ragas_results_*.csv"))
    if not csvs:
        raise FileNotFoundError(f"No results found in {reports_dir}. Run: make eval")
    return csvs[-1]


def summarize(path: Path | None = None) -> None:
    path = path or latest_csv()
    df = pd.read_csv(path)

    metric_cols = ["answer_relevancy", "context_precision", "faithfulness"]
    present = [c for c in metric_cols if c in df.columns]

    print(f"\nResults from: {path.name}\n")
    print("Per-question scores:")
    print(df[["question_id"] + present].to_string(index=False))

    print("\nAverages vs targets:")
    for col in present:
        avg = df[col].mean()
        target = TARGETS.get(col, 0)
        status = "PASS" if avg >= target else "FAIL"
        print(f"  {col:<22} avg={avg:.3f}  target>={target}  [{status}]")


if __name__ == "__main__":
    summarize()
