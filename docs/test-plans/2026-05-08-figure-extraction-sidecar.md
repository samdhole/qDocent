# Human Test Plan: Figure Extraction Sidecar

Generated: 2026-05-08  
Implementation plan: `docs/implementation-plans/2026-05-08-figure-extraction-sidecar/`  
Automated coverage: 28/28 acceptance criteria covered  
Suite runtime: 13s (AC7.1 budget: 60s)

---

## Prerequisites

- Python 3.11 venv at `.venv/` populated via `make setup`
- Node 20 LTS toolchain available
- `GOOGLE_API_KEY` populated in `.env`
- R2R server running (`make r2r`) on port 7272 with `r2r_gemini.toml` loaded
- API server running (`make api`) on port 8000
- Web server running (`make web`) on port 3000
- Sample PDFs generated: `python scripts/create_sample_docs.py`
- At least one PDF that contains embedded raster images has been ingested through the web UI or `make ingest`
- `.venv\Scripts\python.exe -m pytest tests/ -q` passing (152 tests, ~13s)

---

## Phase 1: Pre-flight build and test gates

| Step | Action | Expected |
|------|--------|----------|
| 1.1 | From repo root, run `cd apps/web && npx tsc --noEmit` | Zero TypeScript errors, command exits 0 |
| 1.2 | From repo root, run `.venv\Scripts\python.exe -m pytest tests/ -q` | "152 passed" (or current count), 0 failures, runtime < 60s |
| 1.3 | Confirm both `make r2r` and `make api` are running with no error stack traces in their consoles | Both consoles show `Uvicorn running` / R2R startup banner without tracebacks |

---

## Phase 2: AC4.1 — Static figure file is served

| Step | Action | Expected |
|------|--------|----------|
| 2.1 | In a fresh browser, open DevTools (F12) and navigate to `http://localhost:3000` | Web UI loads, no console errors |
| 2.2 | In the Network tab, ask a question whose ingested PDF contains images (e.g., "What does the architecture diagram show?") | A POST to `/ask` returns 200 with JSON containing a non-empty `figures` array |
| 2.3 | Copy `document_id` and a `figure_id` from the JSON response, plus the `image_url` field of the first figure (e.g., `/figures/abc123/abc123_p001_fig001_01.png`) | Values are present and well-formed |
| 2.4 | Open `http://localhost:8000{image_url}` in a new tab (substitute the actual URL) | HTTP 200; rendered PNG is visible; correct Content-Type header (`image/png`) |
| 2.5 | Open `http://localhost:8000/figures/{document_id}/does_not_exist.png` | HTTP 404; FastAPI default 404 body, no 500 stack trace |

---

## Phase 3: AC4.2 — Figures section renders in the UI

| Step | Action | Expected |
|------|--------|----------|
| 3.1 | At `http://localhost:3000`, ask a question that hits a page with at least one extracted figure | Answer card renders with: answer text, `Citations` section, then a `Figures` section beneath Citations |
| 3.2 | Visually inspect the Figures section | Each figure shows the rendered image, the figure_id, the page number, and a caption (caption may be empty if none was detected) |
| 3.3 | Click into the image (or right-click → "Open image in new tab") | The image URL points to `http://localhost:8000/figures/...png` and loads cleanly |
| 3.4 | Refresh the page and re-ask the same question | Figures section reappears identically; figure_ids match (deterministic) |

---

## Phase 4: AC4.3 — Empty Figures section is hidden

| Step | Action | Expected |
|------|--------|----------|
| 4.1 | Ask a question that returns no figure matches (e.g., a metadata-only question on a PDF that has no images, or a question whose retrieval hits pages with no images) | Answer card renders the answer and Citations only |
| 4.2 | Visually verify | No "Figures" header is present, no empty bordered box, no "No figures" placeholder |
| 4.3 | Inspect the `/ask` JSON response in DevTools | `figures` is `[]` (empty list), confirming the UI is suppressing on empty data |

---

## End-to-End: Fresh ingest → ask → render figures

Purpose: validates the entire AC1 → AC2 → AC3 → AC4 → AC5 chain end to end.

1. Run `python scripts/reset_local_data.py` to clear `data/figures/` and reports.
2. Pick a real PDF with embedded images (or generate one with `scripts/create_sample_docs.py` and add an image).
3. Upload it via the web UI ingest flow, using a filename that is distinct from the temp upload path (e.g., `my_real_report.pdf`).
4. While ingesting, watch the API console: confirm two R2R `ingest_file` calls (one for the PDF, one for `figures.md`) appear in the logs.
5. Open `data/figures/{doc_id}/` on disk. Verify:
   - At least one `*.png` file exists.
   - `figures.json` exists and parses as a list whose `source_file` field equals `my_real_report.pdf` (not a temp path).
   - `figures.md` exists with `## Figure ID: ...` headings.
6. Open `reports/ingestion/{doc_id}.json`. Verify `figures_detected` equals the count of PNGs in step 5 and `source_file == "my_real_report.pdf"`.
7. Ask a question whose answer is on a page that contains a figure.
8. In the UI, confirm the Figures section appears with the same figure_ids you saw on disk.
9. Re-upload the same file. Confirm `data/figures/{doc_id}/` is overwritten (not appended): same figure_ids, no duplicate suffixes.

---

## End-to-End: Manifest ingest failure does not break ingest

Purpose: validates AC2.4 in a real (not mocked) scenario.

1. With API running, temporarily stop R2R (`Ctrl-C` the `make r2r` terminal).
2. Through the web UI, attempt to ingest a PDF with images.
3. Confirm the request fails as expected (R2R is down, so the primary ingest will error — this is fine; the goal is to confirm we do not get a different/worse error from the figure manifest path). Restart R2R.
4. With R2R running, ingest a PDF, then while watching the API logs verify that even if the R2R `figures.md` ingest call were to fail (e.g., transient 500), the API response still returns `200 ok` with `quality_report` populated and `figures_r2r: null`. (If the system is healthy, you will see two successful ingest calls and `figures_r2r` populated — that is also acceptable behavior. The negative path is covered by `test_figure_manifest_ingest_failure_is_nonfatal`.)

---

## Human Verification Required

| Criterion | Why Manual | Steps |
|-----------|------------|-------|
| AC4.1 | Verifies a real HTTP route + on-disk PNG that the test suite mocks | Phase 2 |
| AC4.2 | Visual verification of React rendering, image loading, layout | Phase 3 |
| AC4.3 | Visual confirmation of conditional rendering (no empty container) | Phase 4 |

---

## Traceability

| Acceptance Criterion | Automated Test | Manual Step |
|----------------------|----------------|-------------|
| AC1.1 PNGs in `data/figures/{doc_id}/` | `test_png_files_created` | E2E step 5 |
| AC1.2 Required keys present | `test_record_schema` | — |
| AC1.3 Deterministic figure_id, overwrite | `test_figure_id_deterministic` | E2E step 9 |
| AC1.4 Small images excluded | `test_small_images_excluded` | — |
| AC1.5 OCR failure → empty string | `test_ocr_failure_returns_empty_string` | — |
| AC1.6 Empty PDF → empty list | `test_empty_pdf_returns_empty_list` | — |
| AC2.1 figures.md written | `test_writes_markdown_file` | E2E step 5 |
| AC2.2 Each figure has `##` heading | `test_each_figure_has_heading` | E2E step 5 |
| AC2.3 Manifest ingested after PDF | `test_figure_manifest_ingested_after_pdf` | E2E step 4 |
| AC2.4 Manifest failure non-fatal | `test_figure_manifest_ingest_failure_is_nonfatal` | E2E manifest failure scenario |
| AC2.5 No manifest on empty figures | `test_returns_none_for_empty_figures` + `test_no_manifest_ingest_when_empty_figures` | — |
| AC3.1 `figures` key in rag_query | `test_rag_query_includes_figures_key` | Phase 2, step 2.2 |
| AC3.2 Page match | `test_stage2_page_match` | Phase 3, step 3.1 |
| AC3.3 Regex match in retrieved text | `test_stage1_regex_match` | Phase 3, step 3.1 |
| AC3.4 Limit cap | `test_limit_cap` | — |
| AC3.5 Dedup across stages | `test_deduplication_across_stages` | — |
| AC3.6 Missing dir → empty | `test_empty_when_no_figures_dir` | — |
| AC4.1 GET figure PNG returns 200 | — | Phase 2 |
| AC4.2 Figures render in UI | — | Phase 3 |
| AC4.3 No Figures section when empty | — | Phase 4 |
| AC5.1 figures_detected matches list | `test_figures_detected_matches_figures_list` + `test_figures_detected_with_figures` | E2E step 6 |
| AC5.2 figures_detected = 0 when empty | `test_figures_detected_zero_when_empty` + `test_figures_detected_backwards_compatible` | — |
| AC6.1 original_filename forwarded | `test_post_ingest_passes_original_filename` | — |
| AC6.2 source_file = original | `test_figures_json_written` + `test_source_file_in_records` | E2E step 5 |
| AC6.3 Quality report source_file | `test_pipeline_source_file_param` | E2E step 6 |
| AC7.1 Suite under 60s | `pytest tests/ -q` (13.18s observed) | Phase 1, step 1.2 |
| AC7.2 Helper tests have no I/O | `test_extract_figures_helpers.py` — `types.SimpleNamespace` rects | — |
| AC7.3 Pipeline keys covered | `test_pipeline_returns_figures_key` + `test_pipeline_returns_figure_manifest_key` | — |
| AC7.4 Figure store empty/page/cap | `test_returns_empty_when_dir_missing` + `test_stage2_page_match` + `test_limit_cap` | — |
