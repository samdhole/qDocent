# Human Test Plan — Wiki Doc-ID Validation

Generated: 2026-05-15

## Prerequisites
- Local stack running: `make r2r` (port 7272), `make api` (port 8000), `make web` (port 3000)
- `GOOGLE_API_KEY` set in `.env`
- At least one notebook with one ingested PDF (`make ingest` or upload via UI)
- Tail API logs in a terminal: `docker compose logs -f api`
- `.venv/Scripts/python.exe -m pytest tests/test_wiki_generator.py -v` passes (9 tests)

---

## Phase 1: Wiki generation with real notebook

| Step | Action | Expected |
|------|--------|----------|
| 1.1 | Open `http://localhost:3000`, select a notebook containing ≥1 ingested document | Notebook view loads with document list |
| 1.2 | Click "Generate Wiki" | Job kicks off; UI shows progress; `pages_done` increments to `pages_total` |
| 1.3 | When complete, open each generated page | Pages render with markdown content; no "error" stubs |
| 1.4 | Inspect API logs during generation | No warnings about dropped IDs if Gemini chose only real manifest IDs (expected common case) |

---

## Phase 2: Verify AC2.2 — log warning when invented IDs appear

Purpose: AC2.2 is the only criterion without an automated assertion; must be visually confirmed in logs.

| Step | Action | Expected |
|------|--------|----------|
| 2.1 | Generate a wiki on a notebook with exactly 1 document (raises odds Gemini hallucinates extra IDs) | Job completes |
| 2.2 | Grep API logs for the warning: `dropped * invented doc ID(s)` | If any IDs were invented, a `logger.warning` line names the dropped IDs and the page slug. If none invented, no warning — both acceptable. |
| 2.3 | Repeat across 2–3 notebooks to increase odds of seeing at least one warning | At least one run logs the warning OR all runs skip it cleanly (both valid; the failure mode is a crash or silent invalid upsert) |

---

## End-to-End: Invented-ID resilience

Purpose: Validates AC3 in a live run — the previous failure was wiki generation serving hallucinated content when R2R returned empty results for invented `document_ids`. This run must NOT produce hallucinated content.

1. Pick a notebook with a single doc whose ID is known (check `GET /notebooks/{id}/documents`)
2. Generate the wiki end-to-end
3. Confirm: job status reaches `completed` (not `failed`), every page has non-empty content, and no R2R 4xx errors appear in logs referencing nonexistent `document_ids`
4. Open a page that may have had invented IDs filtered out — content should still be coherent (collection-scoped fallback served retrieval)

---

## Human Verification Required

| Criterion | Why Manual | Steps |
|-----------|------------|-------|
| AC2.2 log warning | Depends on nondeterministic Gemini output; observability check, not behavioral | Phase 2 above |
| Overall content quality | Generated wiki quality is subjective | Phase 1.3 — read a page and judge coherence vs. source documents |

---

## Traceability

| Acceptance Criterion | Automated Test | Manual Step |
|----------------------|----------------|-------------|
| AC1.1 | `TestValidDocIds::test_mixed` | — |
| AC1.2 | `TestValidDocIds::test_all_invalid` | — |
| AC1.3 | `TestValidDocIds::test_all_valid` | — |
| AC1.4 | `TestValidDocIds::test_empty_input` | — |
| AC2.1 | `TestGenerateWiki::test_invented_doc_ids_are_dropped` | — |
| AC2.2 | — | Phase 2.2 |
| AC2.3 | `TestGenerateWiki::test_generates_structure_and_pages` | Phase 1.2–1.3 |
| AC3.1 | `TestGenerateWiki::test_invented_doc_ids_are_dropped` | E2E step 3 |
| AC3.2 | `test_invented_doc_ids_are_dropped` (empty list → collection fallback) | E2E step 4 |
