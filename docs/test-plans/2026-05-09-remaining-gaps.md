# Human Test Plan: 2026-05-09 Remaining Gaps

**Plan:** `docs/implementation-plans/2026-05-09-remaining-gaps/`
**Coverage:** 15/15 automatable ACs covered (315 backend pytest + 63 frontend vitest pass).
**Manual scope:** end-to-end browser + terminal verification for items where a passing unit test is not sufficient.
**Last verified:** 2026-05-09

This plan covers only the steps a human must perform. Phase 1 (hex shortid suppression) and Phase 2 (citation deep-linking) are end-to-end UI behaviours; Phase 3 (RAGAS expansion) requires running the eval against live R2R + Gemini; Phase 4 (questions endpoint) is a docs/code-presence sanity check.

---

## Prerequisites

Run each in its own terminal:

| # | Command | Port | Purpose |
|---|---------|------|---------|
| 1 | `make r2r` | 7272 | R2R retrieval server (loads `r2r_gemini.toml`) |
| 2 | `make api` | 8000 | FastAPI wrapper |
| 3 | `make web` | 3000 | Next.js UI |

Baseline (must be green before starting):

```bash
.venv/Scripts/python.exe -m pytest tests/ -v          # 315 pass
cd apps/web && npx vitest run                         # 63 pass
```

If the documents corpus is empty: `make ingest` to load `data/sample_docs/` (3 PDFs including `sample_support_history.pdf`).

`.env` must have `GOOGLE_API_KEY` set (used by R2R completion + RAGAS evaluator).

Open `http://localhost:3000/ask` in Chrome with DevTools available.

---

## Phase 1: Hex shortid suppression in streaming view (AC1.1, AC1.2, AC1.3, AC2.1)

The vitest unit covers the regex; this confirms the regex actually runs against live SSE chunks before the `[N]` rewrite happens.

| Step | Action | Expected |
|------|--------|----------|
| 1 | On `/ask`, ask "What is the refund policy?" Watch the answer stream in token-by-token. | While streaming, no bare `[abc1234]` / `[A1B2C3D4]` hex tokens flash in the partial text — they are stripped on the fly. |
| 2 | Once streaming finishes, inspect the committed answer. | Inline blue `[1]`, `[2]` numeric chips appear (rewritten by `citation_marker_rewriter`). Numeric markers were not eaten by the strip regex. |
| 3 | DevTools → Network → open the `/conversations/{id}/messages/stream` request → Response tab. Search the SSE payload for one of the raw `[abc1234]` tokens (any 6–8 hex chars in brackets) emitted by R2R. | Raw token appears in the SSE payload but never in the rendered DOM (confirms suppression is client-side). |
| 4 | Open `apps/web/components/ConversationView.tsx` line ~142 in a viewer. Confirm the JSX reads `{stripHexShortIds(partialText)}` and the import on line 21 is `from "@/lib/stripHexShortIds"`. | No inline regex literal `\[0-9a-f\]` survives in this file. |

---

## Phase 2: Citation deep-linking — end-to-end (AC3.1, AC4.1, AC4.2, AC5.1, AC5.2)

The pytest mocks `rag_query`; this exercises the real DocQuery → R2R → API → UI flow.

### Phase 2a: `document_id` flows through the live API

| Step | Action | Expected |
|------|--------|----------|
| 1 | In a fresh terminal: `curl -s -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"question":"What is the refund policy?"}' | python -m json.tool` | Response JSON has `citations: [...]`. Each citation entry has non-null `document_id`, non-null `page`, and a `section` string. |
| 2 | Pick the first `document_id` from the response. Run: `curl -s http://localhost:8000/documents/<doc_id>/chunks | python -m json.tool` | Returns `{document_id, chunks: [...]}` with at least one chunk. Confirms the deep-link target is reachable. |
| 3 | If `document_id` is missing/null in step 1: re-ingest a sample doc (`make ingest`) — the raw-PDF fallback path produces no chunks.json and citations come back as `unknown`. Pre-chunked DocQuery ingest is the supported path. | After re-ingest, retry step 1 — `document_id` populated. |

### Phase 2b: CitationBadge clickability in the browser

| Step | Action | Expected |
|------|--------|----------|
| 1 | On `/ask`, ask the same question that returned a populated `document_id` in 2a. | Answer renders with inline blue `[1]` chip(s). Cursor over the chip shows pointer (clickable). |
| 2 | Click `[1]`. | The lazy-loaded SourcePanel sheet slides in from the right. PDF renders at the cited page; a yellow bbox highlight overlays the cited chunk. |
| 3 | Close the panel (X or Escape). | Sheet closes; chat view restored. |
| 4 | Hover (don't click) `[1]`. | After ~150 ms a HoverCard shows the chunk's verbatim text, source filename, and `p.<page>`. |
| 5 | If you have an answer where any citation is missing `document_id` or `page` (older raw-PDF ingest), hover that chip. | Chip is greyed/non-interactive — no hover pointer, click does nothing. Confirms `canOpenSource` predicate gates the click. |

### Phase 2c: Cross-check `canOpenSource` against the source

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open `apps/web/components/CitationBadge.tsx` line 23. | Reads `const isClickable = canOpenSource(citation, onSelectCitation)` — not an inline boolean expression. Line 7 imports `canOpenSource` from `@/lib/citationClickable`. |

---

## Phase 3: RAGAS eval expansion — live run (AC7.1, AC7.2, AC6.2)

The pytest covers dataset structure; this confirms the runner actually executes 16 questions against R2R + Gemini and writes a CSV that downstream tools can read.

### Phase 3a: Dataset spot-check (AC6.2 — manual review)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open `packages/evals/eval_dataset.yaml`, find the 4 entries: `support_ticket_1001`, `support_ticket_1002`, `support_data_export`, `support_billing_dispute`. | All 4 present, `category: support_history`, references describe only facts found in `sample_support_history.pdf`. |
| 2 | Open `data/sample_docs/sample_support_history.pdf` (or rebuild via `python scripts/create_sample_docs.py`). Spot-check that the 4 reference answers cite only ticket #1001 (refund 2024-01-15), #1002 (25% enterprise discount → VP Sales), #1003 (data export), #1004 (billing dispute → account exec). | No reference invents a date, approver, or escalation path absent from the PDF. No cross-doc fact leakage from `company_policy.pdf` or `pricing_overview.pdf`. |

### Phase 3b: Run the eval

| Step | Action | Expected |
|------|--------|----------|
| 1 | With R2R + API running, from the project root: `make eval` | Exits 0. Console shows progress through 16 questions. Final lines print summary + paths to written artifacts. |
| 2 | Confirm two new artifacts in `reports/evals/`: `ragas_results_YYYYMMDD_HHMMSS.csv` and `ragas_summary_YYYYMMDD_HHMMSS.md`. | Both present, timestamped within the last few minutes. |
| 3 | Run: `.venv/Scripts/python.exe -c "import csv, glob; f=sorted(glob.glob('reports/evals/ragas_results_*.csv'))[-1]; rows=list(csv.DictReader(open(f, encoding='utf-8'))); print(f, len(rows))"` | Prints latest CSV path and row count ≥ 16. |
| 4 | Run: `.venv/Scripts/python.exe -c "import csv, glob; f=sorted(glob.glob('reports/evals/ragas_results_*.csv'))[-1]; ids={r['question_id'] for r in csv.DictReader(open(f, encoding='utf-8'))}; [print(q, '->', 'FOUND' if q in ids else 'MISSING') for q in ['support_ticket_1001','support_ticket_1002','support_data_export','support_billing_dispute']]"` | All 4 IDs print `FOUND`. If column name differs, inspect header: `python -c "import csv; print(next(csv.reader(open('<csv-path>'))))"` and adjust the lookup key. |
| 5 | Open the new `ragas_summary_*.md`. | Aggregate rows reference 16 questions; per-category breakdown includes `support_history` with non-empty scores. |
| 6 | Confirm `reports/evals/*.csv` and `*.md` are NOT staged (`git status`). | Both ignored — only `eval_dataset.yaml` and `tests/test_eval_dataset.py` should appear in any commit related to this phase. |

---

## Phase 4: Question-generation endpoint + docs (AC10.1)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Pick an ingested document with a `chunks.json` manifest: `ls data/documents/`. Choose a `<doc_id>` directory that contains `chunks.json`. | Directory present with both `manifest.json` and `chunks.json`. |
| 2 | Run: `curl -s http://localhost:8000/documents/<doc_id>/questions | python -m json.tool` | Status 200. JSON shape: `{"document_id": "<doc_id>", "questions": [...]}`. List has 0–6 strings, each ending in `?`. If `GOOGLE_API_KEY` is unset or the LLM call fails, the list is empty (not an error). |
| 3 | Run with a non-existent ID: `curl -i http://localhost:8000/documents/does-not-exist/questions` | HTTP 404 with `{"detail": "..."}`. |
| 4 | Open `apps/api/CONTEXT.md`. Confirm `/documents/{id}/questions` appears in the `**Exposes**` bullet (~line 15) AND in the Response shapes block (~line 56) with the documented response shape `{document_id, questions: [str, ...]}` and the caveats about 404 + empty list on missing key. | Both locations updated; markdown alignment in the code block is preserved. |

---

## End-to-End: Hex strip + citation deep-link in one flow

Purpose: validate that Phase 1 and Phase 2 changes coexist without regression in the streaming code path.

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open `/ask`, DevTools Network tab on. | Empty conversation. |
| 2 | Ask a question that produces multi-citation answers (e.g. "What is the refund policy and which support tickets relate to refunds?"). | Streaming starts. During stream: no hex tokens flash. After commit: numeric `[1]`, `[2]`, ... chips visible inline. |
| 3 | Click `[2]`. | SourcePanel opens at the page cited by chunk index 2. |
| 4 | Close the panel. Reload the page (Ctrl+F5). Submit the same question again. | Stream + chips behave identically; no console errors in DevTools. |
| 5 | Inspect Network → the streamed SSE payload. | Raw R2R `[hex]` markers are present in the payload but the rendered DOM only shows numeric `[N]` chips. |

---

## Human Verification Required (summary table)

| AC | Why manual | Steps |
|----|------------|-------|
| AC6.2 No cross-doc leakage in references | Requires reading the PDF + comparing each reference sentence to source facts; no programmatic assertion | Phase 3a step 2 |
| AC7.1 `make eval` exits 0 | Requires live R2R + Gemini; not run in CI | Phase 3b steps 1–2 |
| AC7.2 CSV ≥ 16 rows + 4 new IDs present | Output of a live run; not asserted by unit tests | Phase 3b steps 3–5 |
| AC10.1 CONTEXT.md lists endpoint in both sections | Documentation freshness, not behaviour | Phase 4 step 4 |
| AC1.x in real SSE | Unit covers regex; live stream confirms it runs against R2R-emitted hex tokens | Phase 1 steps 1–3 |
| AC3.1/AC5.x in real DOM | pytest mocks rag_query; vitest tests pure predicate. The browser hop confirms the live API populates `document_id` and the live React tree gates clicks correctly | Phase 2a–2b |

---

## Traceability

| Acceptance Criterion | Automated Test | Manual Step |
|----------------------|----------------|-------------|
| AC1.1 Uppercase hex stripped | `stripHexShortIds.test.ts` line 11 | Phase 1 step 1, E2E step 5 |
| AC1.2 Lowercase hex stripped | `stripHexShortIds.test.ts` line 5 | Phase 1 step 1, E2E step 5 |
| AC1.3 Numeric `[N]` not stripped | `stripHexShortIds.test.ts` lines 19, 25 | Phase 1 step 2 |
| AC2.1 Real import | `stripHexShortIds.test.ts` line 2 | Phase 1 step 4 |
| AC3.1 /ask forwards document_id | `test_routes_ask.py::test_ask_citation_carries_document_id` | Phase 2a step 1 |
| AC4.1 Header fields parsed | `test_r2r_chunk_adapter.py::test_citation_from_retrieved_text_parses_header_and_strips_body` | Phase 2a steps 1–2 (live verification) |
| AC4.2 No-prefix fallback | `test_r2r_chunk_adapter.py::test_citation_from_retrieved_text_falls_back_for_plain_text` | — (covered by automated) |
| AC5.1 All-met → clickable | `citationClickable.test.ts` line 7 | Phase 2b steps 1–2, 2c |
| AC5.2 Missing → non-clickable | `citationClickable.test.ts` lines 11–34 | Phase 2b step 5 |
| AC6.1 ≥4 support_history questions | `test_eval_dataset.py` line 33 | Phase 3a step 1 |
| AC6.2 References derivable from doc | — | Phase 3a step 2 |
| AC7.1 `make eval` exits 0 | — | Phase 3b steps 1–2 |
| AC7.2 CSV has ≥16 rows + 4 IDs | — | Phase 3b steps 3–5 |
| AC8.1 Category required | `test_eval_dataset.py` line 31 | — |
| AC8.2 Count ≥4 | `test_eval_dataset.py` line 33 | — |
| AC9.1 200 + correct shape | `test_route_documents.py::test_get_document_questions_success` | Phase 4 step 2 |
| AC9.2 404 when no chunks.json | `test_route_documents.py::test_get_document_questions_not_found` | Phase 4 step 3 |
| AC9.3 Questions end in `?` | `test_question_generator.py` (structural) | Phase 4 step 2 |
| AC10.1 Endpoint documented | — | Phase 4 step 4 |
