from pathlib import Path

import pytest

from scripts import demo_readiness


def test_run_checks_marks_demo_ready_when_core_surfaces_respond(tmp_path: Path) -> None:
    eval_path = tmp_path / "ragas_results_20260508_120000.csv"
    eval_path.write_text(
        "question_id,answer_relevancy,context_precision,faithfulness\n"
        + "\n".join(f"q{i},0.9,0.8,0.7" for i in range(1, 11)),
        encoding="utf-8",
    )
    (tmp_path / "ragas_summary_20260508_120000.md").write_text(
        "# RAGAS Evaluation Summary\n",
        encoding="utf-8",
    )

    def fake_request(method: str, path: str, payload: dict | None = None) -> dict:
        responses = {
            ("GET", "/health"): {"status": "ok"},
            ("GET", "/documents"): {
                "documents": [
                    {
                        "document_id": "company_policy",
                        "source_url": "/documents/company_policy/source",
                    }
                ]
            },
            ("POST", "/ask"): {
                "answer": "Refunds are allowed within 30 days.",
                "citations": [
                    {
                        "source": "company_policy.pdf",
                        "document_id": "company_policy",
                        "page": 2,
                    }
                ],
            },
        }
        return responses[(method, path)]

    report = demo_readiness.run_checks(
        api_base_url="http://api.test",
        evals_dir=tmp_path,
        request_json=fake_request,
    )

    assert report.ready is True
    assert [check.name for check in report.checks] == [
        "api_health",
        "stored_documents",
        "ask_with_citations",
        "latest_ragas_eval",
    ]
    assert all(check.passed for check in report.checks)


def test_run_checks_fails_when_latest_eval_has_too_few_questions(tmp_path: Path) -> None:
    (tmp_path / "ragas_results_20260508_120000.csv").write_text(
        "question_id,answer_relevancy\nq1,0.9\nq2,0.8\n",
        encoding="utf-8",
    )
    (tmp_path / "ragas_summary_20260508_120000.md").write_text(
        "# RAGAS Evaluation Summary\n",
        encoding="utf-8",
    )

    def fake_request(method: str, path: str, payload: dict | None = None) -> dict:
        if method == "GET" and path == "/health":
            return {"status": "ok"}
        if method == "GET" and path == "/documents":
            return {"documents": []}
        if method == "POST" and path == "/ask":
            return {"answer": "Answer", "citations": [{"source": "policy.pdf"}]}
        raise AssertionError((method, path, payload))

    report = demo_readiness.run_checks(
        api_base_url="http://api.test",
        evals_dir=tmp_path,
        request_json=fake_request,
    )

    eval_check = next(check for check in report.checks if check.name == "latest_ragas_eval")
    assert report.ready is False
    assert eval_check.passed is False
    assert "2 question rows" in eval_check.detail


def test_default_request_json_raises_clear_error_on_unreachable_api() -> None:
    with pytest.raises(RuntimeError, match="GET /health failed"):
        demo_readiness.default_request_json(
            "http://127.0.0.1:1",
            "GET",
            "/health",
            timeout_seconds=0.01,
        )
