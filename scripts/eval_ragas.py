"""Run RAGAS evaluation against R2R and save timestamped results."""
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from r2r import R2RClient
from ragas import evaluate
from ragas.integrations.r2r import transform_to_ragas_dataset
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import AnswerRelevancy, ContextPrecision, Faithfulness

load_dotenv()

R2R_BASE_URL = os.getenv("R2R_BASE_URL", "http://localhost:7272")
EVAL_MODEL = os.getenv("RAGAS_EVAL_MODEL", "gpt-4o-mini")
DATASET_PATH = Path("packages/evals/eval_dataset.yaml")
REPORTS_DIR = Path("reports/evals")


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    with DATASET_PATH.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)

    questions = [item["user_input"] for item in config["questions"]]
    references = [item["reference"] for item in config["questions"]]
    ids = [item["id"] for item in config["questions"]]

    client = R2RClient(base_url=R2R_BASE_URL)

    search_settings = {
        "limit": 5,
        "graph_settings": {"enabled": False},
    }

    print(f"Running {len(questions)} RAG queries against {R2R_BASE_URL} ...")
    r2r_responses = []
    for i, question in enumerate(questions):
        print(f"  [{i+1}/{len(questions)}] {question[:60]}")
        try:
            response = client.retrieval.rag(
                query=question,
                search_settings=search_settings,
            )
            r2r_responses.append(response)
        except Exception as exc:
            sys.exit(f"RAG query failed: {exc}\nIs R2R running? make r2r")

    print("Transforming to RAGAS dataset ...")
    dataset = transform_to_ragas_dataset(
        user_inputs=questions,
        r2r_responses=r2r_responses,
        references=references,
    )

    llm = ChatOpenAI(model=EVAL_MODEL)
    evaluator_llm = LangchainLLMWrapper(llm)
    metrics = [
        AnswerRelevancy(llm=evaluator_llm),
        ContextPrecision(llm=evaluator_llm),
        Faithfulness(llm=evaluator_llm),
    ]

    print(f"Evaluating with {EVAL_MODEL} ...")
    results = evaluate(dataset=dataset, metrics=metrics)

    df = results.to_pandas()
    df.insert(0, "question_id", ids)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = REPORTS_DIR / f"ragas_results_{timestamp}.csv"
    df.to_csv(out_path, index=False)

    # Markdown summary (satisfies HANDOFF.md §23.1)
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
    print(df[["question_id", "answer_relevancy", "context_precision", "faithfulness"]].to_string())
    print("\nAverages:")
    print(df[["answer_relevancy", "context_precision", "faithfulness"]].mean())


if __name__ == "__main__":
    main()
