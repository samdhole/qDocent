"""Check whether the local DocQuery commercial demo is ready to show."""
# pattern: Imperative Shell
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib import error, request


DEFAULT_API_BASE_URL = os.getenv("DOCQUERY_API_BASE_URL", "http://localhost:8000")
DEFAULT_EVALS_DIR = Path("reports/evals")
DEFAULT_TIMEOUT_SECONDS = 10.0
MIN_EVAL_ROWS = 10

RequestJson = Callable[[str, str, dict | None], dict]


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ReadinessReport:
    ready: bool
    checks: list[ReadinessCheck]


def default_request_json(
    api_base_url: str,
    method: str,
    path: str,
    payload: dict | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> dict:
    """Call a JSON API endpoint and return the decoded response body."""
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    http_request = request.Request(
        f"{api_base_url.rstrip('/')}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
    except (OSError, error.HTTPError, error.URLError) as exc:
        raise RuntimeError(f"{method} {path} failed: {exc}") from exc

    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{method} {path} returned non-JSON response") from exc
    if not isinstance(decoded, dict):
        raise RuntimeError(f"{method} {path} returned JSON {type(decoded).__name__}, expected object")
    return decoded


def run_checks(
    api_base_url: str = DEFAULT_API_BASE_URL,
    evals_dir: Path = DEFAULT_EVALS_DIR,
    request_json: RequestJson | None = None,
) -> ReadinessReport:
    """Run the commercial-demo smoke checks without mutating application state."""
    requester = request_json or (
        lambda method, path, payload=None: default_request_json(api_base_url, method, path, payload)
    )
    checks = [
        _check_api_health(requester),
        _check_stored_documents(requester),
        _check_ask_with_citations(requester),
        _check_workflow_email_draft(requester),
        _check_latest_ragas_eval(evals_dir),
    ]
    return ReadinessReport(
        ready=all(check.passed for check in checks),
        checks=checks,
    )


def _check_api_health(request_json: RequestJson) -> ReadinessCheck:
    try:
        response = request_json("GET", "/health", None)
    except RuntimeError as exc:
        return ReadinessCheck("api_health", False, str(exc))
    status = response.get("status")
    if status == "ok":
        return ReadinessCheck("api_health", True, "API health returned ok.")
    return ReadinessCheck("api_health", False, f"Expected status ok, got {status!r}.")


def _check_stored_documents(request_json: RequestJson) -> ReadinessCheck:
    try:
        response = request_json("GET", "/documents", None)
    except RuntimeError as exc:
        return ReadinessCheck("stored_documents", False, str(exc))
    documents = response.get("documents")
    if not isinstance(documents, list):
        return ReadinessCheck("stored_documents", False, "Documents response did not include a list.")
    with_source = [
        doc
        for doc in documents
        if isinstance(doc, dict) and doc.get("document_id") and doc.get("source_url")
    ]
    if with_source:
        return ReadinessCheck(
            "stored_documents",
            True,
            f"{len(with_source)} stored document(s) expose source PDFs.",
        )
    if documents:
        return ReadinessCheck(
            "stored_documents",
            False,
            f"{len(documents)} document(s) found, but none expose source URLs.",
        )
    return ReadinessCheck(
        "stored_documents",
        False,
        "No stored documents. Run make ingest or upload a sample PDF before the demo.",
    )


def _check_ask_with_citations(request_json: RequestJson) -> ReadinessCheck:
    payload = {"question": "What is the refund policy? Cite the source."}
    try:
        response = request_json("POST", "/ask", payload)
    except RuntimeError as exc:
        return ReadinessCheck("ask_with_citations", False, str(exc))
    answer = str(response.get("answer", "")).strip()
    citations = response.get("citations")
    if not answer:
        return ReadinessCheck("ask_with_citations", False, "Ask response did not include an answer.")
    if not isinstance(citations, list) or not citations:
        return ReadinessCheck("ask_with_citations", False, "Ask response did not include citations.")
    usable = [
        citation
        for citation in citations
        if isinstance(citation, dict) and (citation.get("source") or citation.get("document_id"))
    ]
    if not usable:
        return ReadinessCheck("ask_with_citations", False, "Citations were present but lacked source metadata.")
    return ReadinessCheck(
        "ask_with_citations",
        True,
        f"Ask returned an answer with {len(usable)} usable citation(s).",
    )


def _check_workflow_email_draft(request_json: RequestJson) -> ReadinessCheck:
    payload = {
        "message": (
            "Customer asks for a refund because their onboarding documents "
            "were processed late. Draft a support reply."
        )
    }
    try:
        response = request_json("POST", "/workflows/support/email-draft", payload)
    except RuntimeError as exc:
        return ReadinessCheck("workflow_email_draft", False, str(exc))
    draft = str(response.get("draft_response") or response.get("draft") or "").strip()
    if not draft:
        return ReadinessCheck("workflow_email_draft", False, "Workflow response did not include a draft.")
    if "requires_human_approval" not in response and "needs_approval" not in response:
        return ReadinessCheck("workflow_email_draft", False, "Workflow response did not include approval state.")
    return ReadinessCheck("workflow_email_draft", True, "Workflow generated an approval-aware draft.")


def _check_latest_ragas_eval(evals_dir: Path) -> ReadinessCheck:
    latest_csv = _latest_file(evals_dir, "ragas_results_*.csv")
    latest_summary = _latest_file(evals_dir, "ragas_summary_*.md")
    if latest_csv is None:
        return ReadinessCheck("latest_ragas_eval", False, f"No RAGAS CSV found in {evals_dir}.")
    if latest_summary is None:
        return ReadinessCheck("latest_ragas_eval", False, f"No RAGAS summary Markdown found in {evals_dir}.")

    row_count = _count_csv_rows(latest_csv)
    if row_count < MIN_EVAL_ROWS:
        return ReadinessCheck(
            "latest_ragas_eval",
            False,
            f"Latest eval has {row_count} question rows; expected at least {MIN_EVAL_ROWS}.",
        )
    return ReadinessCheck(
        "latest_ragas_eval",
        True,
        f"Latest eval has {row_count} question rows: {latest_csv.name}.",
    )


def _latest_file(directory: Path, pattern: str) -> Path | None:
    if not directory.exists():
        return None
    matches = [path for path in directory.glob(pattern) if path.is_file()]
    if not matches:
        return None
    return max(matches, key=lambda path: path.stat().st_mtime)


def _count_csv_rows(path: Path) -> int:
    with path.open(newline="", encoding="utf-8") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def format_report(report: ReadinessReport) -> str:
    status = "READY" if report.ready else "NOT READY"
    lines = [f"DocQuery demo readiness: {status}", ""]
    for check in report.checks:
        marker = "PASS" if check.passed else "FAIL"
        lines.append(f"[{marker}] {check.name}: {check.detail}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base-url", default=DEFAULT_API_BASE_URL)
    parser.add_argument("--evals-dir", type=Path, default=DEFAULT_EVALS_DIR)
    args = parser.parse_args()

    report = run_checks(api_base_url=args.api_base_url, evals_dir=args.evals_dir)
    print(format_report(report))
    if not report.ready:
        sys.exit(1)


if __name__ == "__main__":
    main()
