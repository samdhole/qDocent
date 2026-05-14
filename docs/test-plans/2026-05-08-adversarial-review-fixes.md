# Human Test Plan — Adversarial Review Fixes

Implementation plan: `docs/implementation-plans/2026-05-08-adversarial-review-fixes/`
Automated coverage: PASS (92/92 tests, all ACs covered)
Manual criteria: AC12.1–AC12.4, AC13.1–AC13.2, AC14.1–AC14.2

---

## Prerequisites

- `make setup` completed; `.venv` exists
- `make r2r` running on http://localhost:7272
- `make api` running on http://localhost:8000
- `make web` running on http://localhost:3000
- A small valid PDF on disk (≥2 pages). Use `python scripts/create_sample_docs.py` to generate sample PDFs in `data/sample_docs/`
- Browser DevTools open with Console + Network tabs visible
- `.venv/Scripts/python.exe -m pytest tests/ -v` passing (239 automated tests green)

---

## Phase 5a — DELETE confirmation guard (arfix.AC12)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Navigate to http://localhost:3000/documents | Documents list renders with at least 2 rows; each row has a "Delete" button |
| 2 | Click "Delete" on Row A | Row A's button switches to "Confirm?" (red) and "Cancel". No DELETE request fires (verify Network tab is silent for `/documents/...`). Row A is **not** removed. |
| 3 | Without leaving Row A, click "Cancel" | Row A returns to a single "Delete" button. No DELETE request fires. Row A still present. |
| 4 | Click "Delete" on Row A again | Row A again shows "Confirm?"/"Cancel" |
| 5 | Click "Delete" on Row B (while Row A is in confirm state) | Row A reverts to single "Delete" (confirmation cleared). Row B now shows "Confirm?"/"Cancel". Only one row in confirm state at a time. |
| 6 | Click "Confirm?" on Row B | A `DELETE /documents/<id>` fires with 200. Row B disappears from the list within ~1 s. |

Maps to: AC12.1 (steps 1–2), AC12.2 (step 6), AC12.3 (steps 2–3), AC12.4 (step 5).

---

## Phase 5b — pollJob cancellation on unmount (arfix.AC13)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Open DevTools → Network → filter for `ingest/jobs` | Filter active, no requests yet |
| 2 | On `/`, upload a PDF | `POST /ingest/jobs` → 202 with `job_id`. `GET /ingest/jobs/<id>` requests start firing every ~2 s. |
| 3 | While polling is active, navigate to a different page (e.g., `/reports`) | Within ≤2 s, `GET /ingest/jobs/<id>` requests **stop** appearing in the Network tab. No further poll requests for that job ID after navigation. |

Maps to: AC13.1 (step 3).

> **AC13.2 — not manually testable via the UI.** `upload()` is the sole call site (bound to `<form onSubmit={upload}>`), and its submit button is `disabled={uploading}` for the entire duration of an active poll. There is no UI path that allows a second upload to begin while a first poll is running. The `pollAbortRef.current?.abort()` call at the top of `upload()` is therefore unreachable in normal use for this scenario. AC13.1 (unmount cleanup via `useEffect` return) covers the only realistic stale-poll trigger. AC13.2 is superseded by the design choice to prevent concurrent uploads.

---

## Phase 5c — Unique React keys for citations (arfix.AC14)

| Step | Action | Expected |
|------|--------|----------|
| 1 | Ingest two distinct PDFs that share content on a single topic. Use `python scripts/create_sample_docs.py` then `make ingest`, or upload two PDFs through the UI. | Both documents appear in `/documents` |
| 2 | Navigate to `/` (Ask page). Open DevTools Console; clear it. | Console empty |
| 3 | Submit a question likely to retrieve chunks from both documents (e.g., "What is the refund policy?") | Response renders with multiple citation cards. Console shows **no** "Encountered two children with the same key" or "Each child in a list should have a unique 'key' prop" warning. |
| 4 | In DevTools → Elements or React DevTools, inspect each rendered citation `<li>`. | Each item has a distinct `key` attribute. |
| 5 | Repeat step 3 several times with different questions | Console remains free of duplicate-key warnings across multiple queries. |

Maps to: AC14.1 (steps 2–3, 5), AC14.2 (step 4).

---

## End-to-End: Citation header round-trip (full stack)

Validates the production ingest → retrieve → cite path delivers non-"unknown" citations.

1. From a clean state (`make clean`, then `make r2r`, `make api`, `make web`), upload `data/sample_docs/company_policy.pdf` via the `/` page upload control.
2. Wait until the upload-progress UI reports completion (job status = `completed`).
3. Navigate to `/documents`. Confirm the new document appears with a working `source_url` link.
4. Open `data/documents/<doc_id>/manifest.json` on disk. Confirm it contains `r2r_document_ids: [...]` with at least 1 ID and no `null` values.
5. Return to `/` and ask a question whose answer is in the uploaded PDF (e.g., "How long is the refund window?").
6. In the response panel, confirm:
   - At least one citation card has `document` ≠ `"unknown"` and matches the uploaded PDF's filename
   - Citation `page` is an integer ≥ 1
   - Citation `section` is a non-empty string when the source has section headings
7. In the API server logs, confirm no warnings about "Corrupt manifest" or "missing valid r2r_document_ids".

---

## End-to-End: Delete cleans up R2R + local store

**R2R healthy path:**
1. With a document present, navigate to `/documents`.
2. Click "Delete" → "Confirm?" on that row.
3. Observe the request in DevTools Network: `DELETE /documents/<doc_id>` returns 200 with body `{"status": "deleted", "document_id": "...", "r2r_delete": {"deleted": [...], "failed": []}}`. The `deleted` list contains the IDs from `manifest.json`.
4. Confirm `data/documents/<doc_id>/` no longer exists on disk.
5. Re-ask the same question on `/`. Previously-cited content should no longer return citations from this document.

**R2R unhealthy path (optional but recommended before sign-off):**
1. Re-ingest one document, then stop R2R (`Ctrl+C` in the `make r2r` terminal).
2. Click "Delete" → "Confirm?" on that row.
3. The request returns 200 (not 503) with `r2r_delete.failed` populated by all R2R IDs and `deleted` empty.
4. Confirm `data/documents/<doc_id>/` is removed locally despite R2R being down.
5. Restart R2R with `make r2r`.

---

## Smoke script (arfix.AC16.2)

Run from project root with venv active and R2R running:

```bash
.venv/Scripts/python.exe scripts/smoke_r2r.py
```

Expected output includes:
```
Citation header round-trip: OK — document='smoke_test.pdf', page=1
```

If you see `WARNING: Citation header round-trip FAILED`, treat as a regression — investigate `apps/api/services/r2r_chunk_adapter.py` and `apps/api/services/r2r_client.py`.

---

## Traceability

| Acceptance Criterion | Automated Test | Manual Step |
|----------------------|----------------|-------------|
| arfix.AC1.1 | tests/test_r2r_client.py::test_rag_query_header_document_takes_precedence_over_meta | E2E "Citation round-trip" step 6 |
| arfix.AC1.2 | tests/test_r2r_client.py::test_rag_query_meta_fallback_when_no_header | — |
| arfix.AC1.3 | tests/test_r2r_client.py::test_rag_query_header_fields_take_precedence_over_meta | E2E "Citation round-trip" step 6 |
| arfix.AC2.1 | tests/test_r2r_chunk_adapter.py::test_chunk_text_for_r2r_section_path_with_equals_roundtrips | — |
| arfix.AC2.2 | tests/test_r2r_chunk_adapter.py::test_chunk_text_for_r2r_source_file_with_semicolon_encodes_to_comma | — |
| arfix.AC2.3 | tests/test_r2r_chunk_adapter.py::test_chunk_text_for_r2r_none_fields_produce_empty_string | — |
| arfix.AC3.1 | tests/test_document_store.py::test_safe_segment_raises_on_* (5 tests) | — |
| arfix.AC3.2 | tests/test_document_store.py::test_safe_segment_accepts_* (3 tests) | — |
| arfix.AC4.1 | tests/test_document_store.py::test_load_document_manifest_returns_none_on_corrupt_json | E2E step 7 |
| arfix.AC4.2 | tests/test_document_store.py::test_load_document_manifest_returns_none_when_r2r_ids_is_{null,string,missing} | — |
| arfix.AC4.3 | tests/test_document_store.py::test_document_manifest_round_trips_r2r_ids | E2E step 4 |
| arfix.AC5.1 | tests/test_route_ingest.py::test_create_ingest_job_cleans_up_tmpfile_on_exception | — |
| arfix.AC6.1 | tests/test_r2r_client.py::test_fallback_path_saves_source_pdf_when_pipeline_provides_document_id | — |
| arfix.AC6.2 | tests/test_r2r_client.py::test_fallback_path_skips_save_source_pdf_when_pipeline_raises | — |
| arfix.AC7.1 | tests/test_r2r_client.py::test_chunk_validation_filters_invalid_chunks | — |
| arfix.AC7.2 | tests/test_r2r_client.py::test_all_invalid_chunks_falls_back_to_raw_pdf | — |
| arfix.AC7.3 | tests/test_r2r_client.py::test_valid_chunks_pass_through_unchanged | — |
| arfix.AC8.1 | tests/test_r2r_client.py::test_none_valued_metadata_fields_are_included | — |
| arfix.AC9.1 | tests/test_ingest_jobs.py::test_expired_{completed,failed}_job_is_pruned | — |
| arfix.AC9.2 | tests/test_ingest_jobs.py::test_non_terminal_job_is_never_pruned | — |
| arfix.AC9.3 | tests/test_ingest_jobs.py::test_recent_completed_job_is_not_pruned | — |
| arfix.AC10.1 | tests/test_route_documents.py::test_delete_document_removes_stored_source_pdf | E2E "Delete" step 3 |
| arfix.AC10.2 | tests/test_route_documents.py::test_delete_document_removes_r2r_documents_when_manifest_has_ids | E2E "Delete" step 3 |
| arfix.AC11.1 | tests/test_r2r_client.py::test_delete_r2r_documents_returns_failed_when_client_construction_fails | E2E "Delete (unhealthy)" |
| arfix.AC11.2 | tests/test_route_documents.py::test_delete_document_succeeds_even_when_r2r_delete_fails | E2E "Delete (unhealthy)" steps 3–4 |
| arfix.AC11.3 | tests/test_route_documents.py::test_delete_document_succeeds_even_when_r2r_delete_fails | E2E "Delete (unhealthy)" steps 3–4 |
| arfix.AC12.1 | — | Phase 5a steps 1–2 |
| arfix.AC12.2 | — | Phase 5a step 6 |
| arfix.AC12.3 | — | Phase 5a step 3 |
| arfix.AC12.4 | — | Phase 5a step 5 |
| arfix.AC13.1 | — | Phase 5b step 3 |
| arfix.AC13.2 | — | N/A — scenario unreachable via UI (upload button disabled while polling active; see Phase 5b note) |
| arfix.AC14.1 | — | Phase 5c steps 2–3, 5 |
| arfix.AC14.2 | — | Phase 5c step 4 |
| arfix.AC15.1 | tests/test_r2r_client.py::test_passes_chunks_as_strings_with_citation_headers | — |
| arfix.AC15.2 | tests/test_r2r_client.py::test_metadata_contains_required_fields | — |
| arfix.AC15.3 | tests/test_r2r_client.py::test_raises_runtime_error_when_client_construction_fails | — |
| arfix.AC16.1 | tests/test_integration_r2r_citation.py::test_prechunked_ingest_citation_round_trip | E2E "Citation round-trip" |
| arfix.AC16.2 | scripts/smoke_r2r.py (script) | "Smoke script" section |
