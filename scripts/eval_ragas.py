"""Run RAGAS evaluation against R2R and save timestamped results."""
# pattern: Imperative Shell
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

from packages.evals.run_ragas import load_dataset, run_eval

load_dotenv()

R2R_BASE_URL = os.getenv("R2R_BASE_URL", "http://localhost:7272")
EVAL_MODEL = os.getenv("RAGAS_EVAL_MODEL", "gemini-3-flash-preview")
DATASET_PATH = Path("packages/evals/eval_dataset.yaml")
REPORTS_DIR = Path("reports/evals")


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Load dataset to get IDs separately
    questions, references, ids = load_dataset(DATASET_PATH)

    try:
        print(f"Running RAGAS evaluation ({len(questions)} questions) ...")
        results = run_eval(
            r2r_base_url=R2R_BASE_URL,
            eval_model=EVAL_MODEL,
            dataset_path=DATASET_PATH,
        )
    except Exception as exc:
        sys.exit(f"RAG query failed: {exc}\nIs R2R running? make r2r")

    df = results.to_pandas()
    df.insert(0, "question_id", ids)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = REPORTS_DIR / f"ragas_results_{timestamp}.csv"
    df.to_csv(out_path, index=False)

    md_path = REPORTS_DIR / f"ragas_summary_{timestamp}.md"
    metric_cols = ["answer_relevancy", "context_precision", "faithfulness"]
    present = ["question_id"] + [c for c in metric_cols if c in df.columns]
    header = " | ".join(present)
    sep = " | ".join(["---"] * len(present))
    rows_md = []
    for _, row in df.iterrows():
        vals = [f"{row[c]:.3f}" if isinstance(row[c], float) else str(row[c]) for c in present]
        rows_md.append(f"| {' | '.join(vals)} |")
    avgs_md = [f"- **{c}:** {df[c].mean():.3f}" for c in metric_cols if c in df.columns]
    md_lines = [
        "# RAGAS Evaluation Summary",
        "",
        f"**Run:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Model:** {EVAL_MODEL}",
        f"**R2R:** {R2R_BASE_URL}",
        "",
        "## Per-Question Results",
        "",
        f"| {header} |",
        f"| {sep} |",
        *rows_md,
        "",
        "## Averages",
        "",
        *avgs_md,
    ]
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"\nSaved CSV:      {out_path}")
    print(f"Saved Markdown: {md_path}")
    print("\nPer-question results:")
    print(df[present].to_string())
    print("\nAverages:")
    metric_cols_present = [c for c in metric_cols if c in df.columns]
    print(df[metric_cols_present].mean())


if __name__ == "__main__":
    main()
