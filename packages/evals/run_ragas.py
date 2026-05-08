"""Library wrapper: run RAGAS eval and return EvaluationResult.

Called by scripts/eval_ragas.py and apps/api/services/ragas_runner.py.
Never imports from apps/ or packages/ingestion/.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from langchain_openai import ChatOpenAI
from r2r import R2RClient
from ragas import evaluate
from ragas.integrations.r2r import transform_to_ragas_dataset
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import AnswerRelevancy, ContextPrecision, Faithfulness


def load_dataset(path: Path) -> tuple[list[str], list[str], list[str]]:
    """Return (questions, references, ids) from eval_dataset.yaml."""
    with path.open(encoding="utf-8") as f:
        config = yaml.safe_load(f)
    items = config["questions"]
    return (
        [i["user_input"] for i in items],
        [i["reference"] for i in items],
        [i["id"] for i in items],
    )


def run_eval(
    *,
    r2r_base_url: str,
    eval_model: str,
    dataset_path: Path,
    search_settings: dict[str, Any] | None = None,
) -> Any:  # ragas.EvaluationResult
    """Run RAGAS evaluation and return result object (call .to_pandas() on it)."""
    if search_settings is None:
        search_settings = {"limit": 5, "graph_settings": {"enabled": False}}

    questions, references, _ = load_dataset(dataset_path)
    client = R2RClient(base_url=r2r_base_url)

    r2r_responses = [
        client.retrieval.rag(query=q, search_settings=search_settings)
        for q in questions
    ]

    dataset = transform_to_ragas_dataset(
        user_inputs=questions,
        r2r_responses=r2r_responses,
        references=references,
    )

    evaluator_llm = LangchainLLMWrapper(ChatOpenAI(model=eval_model))
    metrics = [
        AnswerRelevancy(llm=evaluator_llm),
        ContextPrecision(llm=evaluator_llm),
        Faithfulness(llm=evaluator_llm),
    ]

    return evaluate(dataset=dataset, metrics=metrics)
