from ragas.metrics import LLMContextPrecisionWithReference

from packages.evals.run_ragas import build_metrics


class DummyLLM:
    pass


class DummyEmbeddings:
    pass


def test_build_metrics_uses_langchain_compatible_context_precision() -> None:
    metrics = build_metrics(llm=DummyLLM(), embeddings=DummyEmbeddings())

    context_metric = next(metric for metric in metrics if metric.name == "context_precision")

    assert isinstance(context_metric, LLMContextPrecisionWithReference)
