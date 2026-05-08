"""Generate per-document ingestion quality reports (JSON + Markdown).

Reports always produced — even for low-confidence documents.
Low-confidence pages (OCR conf < 70.0) are listed as warnings.
# pattern: Imperative Shell
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPORTS_DIR = Path("reports/ingestion")
OCR_LOW_CONF_THRESHOLD = 70.0
CITATION_COVERAGE_CONFIDENCE_MIN = 0.80


def generate_report(
    document_id: str,
    source_file: str,
    pages: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    classifier_result: dict[str, Any],
    figures: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Generate and write quality report. Returns the report dict."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    tables_detected = sum(len(p.get("tables", [])) for p in pages)
    figures_detected = len(figures or [])
    low_confidence_pages = [
        p["page_number"]
        for p in pages
        if p.get("confidence", 100.0) < OCR_LOW_CONF_THRESHOLD
    ]
    high_confidence_chunks = sum(
        1 for c in chunks if c.get("confidence", 0) >= CITATION_COVERAGE_CONFIDENCE_MIN
    )
    citation_coverage = round(high_confidence_chunks / max(len(chunks), 1), 4)

    report = {
        "document_id": document_id,
        "document_type": classifier_result.get("document_type", "unknown"),
        "parser_used": classifier_result.get("recommended_parser", "unknown"),
        "pages": len(pages),
        "chunks": len(chunks),
        "tables_detected": tables_detected,
        "figures_detected": figures_detected,
        "low_confidence_pages": low_confidence_pages,
        "citation_coverage_estimate": citation_coverage,
    }

    _write_json(document_id, report)
    _write_markdown(document_id, source_file, report, pages, classifier_result)

    return report


def _write_json(document_id: str, report: dict) -> None:
    path = REPORTS_DIR / f"{document_id}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")


def _write_markdown(
    document_id: str,
    source_file: str,
    report: dict,
    pages: list[dict],
    classifier_result: dict,
) -> None:
    low_pages = report["low_confidence_pages"]
    warnings = [f"Page {p} had low OCR confidence." for p in low_pages]

    lines = [
        f"# Ingestion Quality Report: {source_file}",
        "",
        "## Summary",
        "",
        "| Field | Value |",
        "|---|---:|",
        f"| Pages | {report['pages']} |",
        f"| Parser Used | {report['parser_used']} |",
        f"| Chunks Created | {report['chunks']} |",
        f"| Tables Detected | {report['tables_detected']} |",
        f"| Figures Detected | {report['figures_detected']} |",
        f"| Low-Confidence Pages | {', '.join(map(str, low_pages)) or 'None'} |",
        f"| Citation Coverage Estimate | {int(report['citation_coverage_estimate'] * 100)}% |",
        "",
        "## Parser Decision",
        "",
        f"The document was classified as `{report['document_type']}`. "
        f"The pipeline used `{report['parser_used']}` with "
        f"`{classifier_result.get('recommended_template', 'default')}` chunking template.",
        "",
    ]

    if warnings:
        lines += ["## Warnings", ""]
        lines += [f"- {w}" for w in warnings]
        lines += ["", "## Recommended Human Review", ""]
        lines += [f"Review pages {', '.join(map(str, low_pages))} before using this document for client-facing answers."]
    else:
        lines += ["## Warnings", "", "None — all pages parsed with high confidence."]

    path = REPORTS_DIR / f"{document_id}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
