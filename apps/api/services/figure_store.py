# pattern: Imperative Shell
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

FIGURES_DIR = Path("data/figures")
# Regex charset [A-Za-z0-9_\-] matches UUID/hash format of current document IDs.
# A format change (e.g. IDs containing '.') would require updating this pattern.
_FIGURE_ID_RE = re.compile(r"Figure ID:\s*([A-Za-z0-9_\-]+)")


def load_figures(document_id: str | None = None) -> list[dict[str, Any]]:
    """Load figure records from disk.

    When document_id is given, loads only that document's figures.json.
    When None, globs all data/figures/*/figures.json.
    Returns [] if FIGURES_DIR does not exist or no files are found.
    """
    if not FIGURES_DIR.exists():
        return []

    if document_id is not None:
        target = FIGURES_DIR / document_id / "figures.json"
        if not target.exists():
            return []
        return json.loads(target.read_text(encoding="utf-8"))

    results: list[dict[str, Any]] = []
    for path in FIGURES_DIR.glob("*/figures.json"):
        results.extend(json.loads(path.read_text(encoding="utf-8")))
    return results


def figures_for_response(
    citations: list[dict[str, Any]],
    retrieved_contexts: list[dict[str, Any]],
    limit: int = 6,
) -> list[dict[str, Any]]:
    """Return figures relevant to a RAG response, capped at limit.

    Two-stage matching (deduplicated):
      Stage 1 — regex-scan retrieved_contexts text for 'Figure ID: <id>' markers.
                 Catches figure-specific queries where the sidecar was retrieved.
      Stage 2 — page-match figures whose (source_file, page_number) overlaps with
                 a citation's (document, page). Load-bearing path for general queries.
    """
    all_figures = load_figures()  # TODO: cache when figure corpus grows
    by_id = {f["figure_id"]: f for f in all_figures}
    selected: dict[str, dict[str, Any]] = {}

    # Stage 1: figure IDs mentioned in retrieved context text
    # NOTE: retrieved_contexts text is truncated to 400 chars by r2r_client.py (Phase 5 concern).
    # Figure IDs past position 400 will be silently missed. Stage 2 (page-match) is the
    # load-bearing primary path for general queries; Stage 1 is best-effort for explicit refs.
    for ctx in retrieved_contexts:
        text = ctx.get("text", "")
        for fig_id in _FIGURE_ID_RE.findall(text):
            if fig_id in by_id:
                selected[fig_id] = by_id[fig_id]

    # Stage 2: page-match against citation (document, page) pairs
    citation_keys = {
        (c.get("document"), c.get("page"))
        for c in citations
        if c.get("document") and c.get("page") is not None
    }
    for f in all_figures:
        key = (f.get("source_file"), f.get("page_number"))
        if key in citation_keys:
            selected[f["figure_id"]] = f

    return list(selected.values())[:limit]
