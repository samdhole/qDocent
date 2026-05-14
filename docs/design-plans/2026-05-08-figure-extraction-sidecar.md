# Figure Extraction Sidecar Pipeline Design

## Summary

Figure extraction is added to the existing ingestion pipeline as a **sidecar step** — a discrete stage that runs inside `run_pipeline()` after table normalization and before the quality report, with no separate service or process required. When a PDF is ingested, `extract_figures()` uses PyMuPDF to locate embedded raster images on each page, applies a minimum-size filter (80×80 px), saves each image as a PNG asset under `data/figures/{document_id}/`, runs OCR to capture text within the image, and heuristically finds the nearest caption block in the page layout. The resulting figure records — containing the figure ID, source filename, page number, bounding box, image URL, caption, and OCR text — are written to a per-document `figures.json` and also formatted into a Markdown sidecar file (`figures.md`). The sidecar is then ingested into R2R as a separate retrievable document, making individual figures searchable by semantic similarity alongside the parent PDF. Figure IDs are deterministic, so re-ingesting the same PDF overwrites rather than appends, and the sidecar is only ingested after the parent PDF succeeds to keep R2R state consistent.

At query time, `rag_query()` calls a pure-function figure store service that matches figures to the retrieved answer using two stages: first, a regex scan of R2R's retrieved context chunks for `Figure ID:` identifiers (useful when the answer was drawn directly from the sidecar), and second, a page-match against citation metadata — figures whose `(source_file, page_number)` aligns with a cited page are included regardless of whether the sidecar was retrieved. The resulting figure list (capped at six entries, deduplicated) is attached to the `/ask` response and rendered in the frontend `AnswerCard` as a two-column image grid. Figure PNG assets are served as static files via FastAPI's `StaticFiles` mount, mounted conditionally so an absent `data/figures/` directory does not crash the server.

## Definition of Done

- PDFs ingested via `/ingest` have embedded raster figures extracted as PNG assets
- Each figure's caption text and OCR content are indexed in R2R via a Markdown sidecar document
- `/ask` responses include a `figures` list with `image_url`, `caption`, `source_file`, and `page_number` for figures relevant to the answer
- Figure images are served at `/figures/{document_id}/{figure_id}.png` via the FastAPI static file mount
- `figures_detected` in the quality report reflects the real count
- Original uploaded filename (not temp path) appears in all figure records, manifests, and quality reports
- All existing 98 tests continue to pass; new tests cover figure helpers, pipeline integration, and figure store matching

## Acceptance Criteria

### figure-extraction-sidecar.AC1: Raster figures are extracted during ingestion
- **figure-extraction-sidecar.AC1.1 Success:** PDF with embedded raster images produces PNG files in `data/figures/{document_id}/`
- **figure-extraction-sidecar.AC1.2 Success:** Each figure record contains `figure_id`, `source_file`, `page_number`, `bbox`, `image_url`, `caption`, `ocr_text`
- **figure-extraction-sidecar.AC1.3 Success:** `figure_id` is deterministic — re-ingesting the same PDF produces identical IDs and overwrites (not appends) existing assets
- **figure-extraction-sidecar.AC1.4 Success:** Images smaller than 80×80px are excluded
- **figure-extraction-sidecar.AC1.5 Failure:** OCR failure (e.g. corrupt image) returns `ocr_text=""` without raising
- **figure-extraction-sidecar.AC1.6 Edge:** PDF with no embedded raster images returns empty figures list

### figure-extraction-sidecar.AC2: Figure content is indexed in R2R via Markdown sidecar
- **figure-extraction-sidecar.AC2.1 Success:** `figures.md` is written to `data/figures/{document_id}/` after extraction
- **figure-extraction-sidecar.AC2.2 Success:** Each figure appears as a `##` heading in `figures.md` with Figure ID, source file, page, image URL, caption, and OCR text
- **figure-extraction-sidecar.AC2.3 Success:** `figures.md` is ingested into R2R only after the raw PDF ingest succeeds
- **figure-extraction-sidecar.AC2.4 Failure:** Figure manifest ingest failure logs a warning but does not raise or fail the ingest response
- **figure-extraction-sidecar.AC2.5 Edge:** Empty figures list produces no `figures.md` and no manifest ingest attempt

### figure-extraction-sidecar.AC3: `/ask` responses include relevant figures
- **figure-extraction-sidecar.AC3.1 Success:** `rag_query()` return dict contains `"figures"` key (list, may be empty)
- **figure-extraction-sidecar.AC3.2 Success:** Figures whose `(source_file, page_number)` matches a citation's `(document, page)` are included
- **figure-extraction-sidecar.AC3.3 Success:** Figures whose `Figure ID:` appears in retrieved context text are included
- **figure-extraction-sidecar.AC3.4 Success:** Result is capped at `limit=6` figures
- **figure-extraction-sidecar.AC3.5 Success:** Duplicate figures from both matching stages appear only once
- **figure-extraction-sidecar.AC3.6 Edge:** Missing `data/figures/` directory returns empty list without error

### figure-extraction-sidecar.AC4: Figure images are served as static assets
- **figure-extraction-sidecar.AC4.1 Success:** `GET /figures/{document_id}/{figure_id}.png` returns the PNG with 200
- **figure-extraction-sidecar.AC4.2 Success:** `StaticFiles` mount is present in `main.py` when `data/figures/` exists
- **figure-extraction-sidecar.AC4.3 Edge:** Missing `data/figures/` at API startup does not crash the server

### figure-extraction-sidecar.AC5: Quality report reflects real figure count
- **figure-extraction-sidecar.AC5.1 Success:** `figures_detected` in quality report equals `len(figures)` returned by `extract_figures()`
- **figure-extraction-sidecar.AC5.2 Edge:** `figures_detected` is `0` when PDF has no embedded raster images

### figure-extraction-sidecar.AC6: Original filename used throughout
- **figure-extraction-sidecar.AC6.1 Success:** Figure records show `source_file` = original uploaded filename, not temp path
- **figure-extraction-sidecar.AC6.2 Success:** `figures.md` and `figures.json` contain original filename
- **figure-extraction-sidecar.AC6.3 Success:** Quality report `source_file` field shows original filename

### figure-extraction-sidecar.AC7: Test suite integrity
- **figure-extraction-sidecar.AC7.1** All 98 existing tests pass after all phases are complete
- **figure-extraction-sidecar.AC7.2** New tests cover: caption regex matching, nearest-caption distance, figure ID determinism
- **figure-extraction-sidecar.AC7.3** New tests cover: pipeline `"figures"` and `"figure_manifest"` keys, `figures_detected` count
- **figure-extraction-sidecar.AC7.4** New tests cover: figure store empty-dir graceful return, page-match logic, limit cap

## Glossary

- **R2R**: The retrieval engine at the core of this system (port 7272). Stores documents as vector embeddings, answers natural-language queries via RAG, and returns citations alongside its response.
- **RAG (Retrieval-Augmented Generation)**: A technique where a language model's answer is grounded in passages retrieved from a document store rather than generated purely from training data.
- **Sidecar** (two senses): (1) The figure-extraction pipeline step that runs alongside the main PDF parse without being a separate service. (2) The Markdown companion file (`figures.md`) that represents figure content as retrievable text chunks in R2R.
- **PyMuPDF**: A Python library (`fitz`) for parsing PDF structure. Used to iterate pages, locate embedded raster images, extract pixel data, and read surrounding text blocks for caption detection.
- **Pillow**: A Python image-processing library (`PIL`). Used to convert raw pixmap bytes from PyMuPDF into PNG files saved to disk.
- **OCR (Optical Character Recognition)**: Reading text contained within a raster image. Applied to each extracted figure to capture labels, axis values, or annotations not present in the PDF text layer.
- **Pixmap / `Matrix(2, 2)`**: A PyMuPDF `Pixmap` is a raster representation of a PDF page or image region. `Matrix(2, 2)` renders it at 2× scale, quadrupling pixel count relative to 1×.
- **Raster figure**: An image embedded in a PDF as a grid of pixels (e.g., a photograph, a scanned chart). Distinct from a vector figure, which is geometric drawing commands and cannot be extracted the same way.
- **bbox (bounding box)**: The rectangular region on a PDF page containing a figure, expressed as `(x0, y0, x1, y1)` coordinates. Used for size filtering and finding nearby caption text.
- **Markdown sidecar (`figures.md`)**: A Markdown file where each extracted figure is a `##`-headed section containing metadata and OCR text. Ingested into R2R so individual figures are retrievable by semantic search.
- **Figure manifest**: Collectively, the `figures.json` record file (used by the figure store at query time) and the `figures.md` sidecar (ingested into R2R). Both written to `data/figures/{document_id}/`.
- **FC/IS split (Functional Core / Imperative Shell)**: Architectural pattern enforced in this codebase. FC modules contain pure functions (tested directly). IS modules orchestrate I/O, file writes, and network calls (tested via mocks). Every production module is annotated with a `# pattern:` comment.
- **`StaticFiles` mount**: A FastAPI feature that serves a local directory as a URL path. Exposes `data/figures/` at `/figures/*` so the frontend can load figure PNGs from the API server.
- **Citation**: In the RAG context, a reference returned by R2R alongside its answer — typically `{document, page}` metadata identifying which document chunk the answer came from.
- **`retrieved_contexts`**: The raw text chunks R2R retrieved from its vector store to construct the answer. Stage 1 figure matching regex-scans these for `Figure ID:` markers from the sidecar.
- **Quality report**: A structured summary produced at the end of `run_pipeline()` for each ingested document. Records chunk count, table count, and `figures_detected`.
- **Deterministic / idempotent re-ingest**: `figure_id` values are computed from fixed inputs (`document_id`, `page_number`, `image_number`, `rect_index`) so re-ingesting the same PDF overwrites existing files rather than creating duplicates.
- **AnswerCard**: The React component in the frontend (`apps/web/components/AnswerCard.tsx`) that renders the RAG response, citations, and (after this feature) a two-column figure image grid.
- **`_CAPTION_RE`**: A compiled Python regex pattern that recognises caption-like text near a figure (e.g. lines beginning with "Figure", "Fig."). Defined in the Functional Core helpers module for reuse and testability.
- **`NEXT_PUBLIC_API_URL`**: A Next.js environment variable the frontend uses to prefix API calls and image `src` attributes. Makes the API origin configurable between environments.

---

## Architecture

Figure extraction runs as a sidecar step inside the existing ingestion pipeline. After table normalization and before the quality report, `pipeline.py` calls `extract_figures()`, which uses PyMuPDF to locate embedded raster images in each PDF page, saves them as PNG assets, performs OCR, and finds the nearest caption text. The extracted figure records are written to `data/figures/{document_id}/figures.json` (per-document, overwritten on re-ingest for idempotency). A Markdown sidecar (`data/figures/{document_id}/figures.md`) formats each figure as a heading-delimited chunk so R2R can retrieve individual figures by semantic similarity.

`r2r_client.ingest_file_with_pipeline()` ingests the main PDF first; only if that succeeds does it ingest the Markdown sidecar. This keeps R2R state consistent — half-ingested state (figures without a parent document) never occurs.

At query time, `rag_query()` calls `figure_store.figures_for_response()`, which uses two stages: (1) regex-scan retrieved context chunks for `Figure ID:` identifiers from the sidecar, and (2) page-match figures whose `(source_file, page_number)` overlaps with cited pages. Stage 2 is the load-bearing path; stage 1 is a bonus for figure-specific queries.

Figure PNG assets are served via a `StaticFiles` mount at `/figures` in `main.py`, mounted conditionally on `data/figures/` existing. The frontend `AnswerCard` renders a two-column image grid when `result.figures` is non-empty.

```
PDF upload (ingest route)
  └─ r2r_client.ingest_file_with_pipeline(file_path, original_filename)
       ├─ run_pipeline(pdf_path, source_file=original_filename)
       │    ├─ [existing] classify → parse_pdf → normalize_tables → chunk
       │    ├─ [new] extract_figures() → figures list + PNG assets + figures.json
       │    ├─ [new] write_figure_manifest() → figures.md
       │    └─ generate_report(..., figures=figures) → figures_detected count
       ├─ R2R ingest: raw PDF
       └─ R2R ingest: figures.md (only if PDF ingest succeeded)

GET /ask?q=...
  └─ rag_query(query)
       ├─ [existing] R2R retrieval → answer + citations + retrieved_contexts
       └─ [new] figures_for_response(citations, retrieved_contexts) → figures list

Static assets
  └─ FastAPI /figures/* → data/figures/{document_id}/{figure_id}.png
```

## Existing Patterns

Investigation confirmed these existing patterns this design follows:

**FC/IS module split** — `r2r_client.py` (Imperative Shell) delegates pure helpers to `r2r_client_helpers.py` (Functional Core). This design mirrors that exactly: `extract_figures.py` (IS, does file I/O + OCR) alongside `extract_figures_helpers.py` (FC, pure functions: `nearest_caption`, `figure_id_from`, `_CAPTION_RE`). `figure_store.py` is Functional Core (pure reads from disk, no side effects).

**FCIS comment requirement** — every production module starts with `# pattern: Functional Core` or `# pattern: Imperative Shell`. All new modules follow this.

**Module naming** — project prohibits generic names (`utils.py`, `helpers.py`). Names used here (`extract_figures_helpers.py`, `figure_store.py`) are descriptive and specific.

**Graceful pipeline fallback** — `ingest_file_with_pipeline` already wraps `run_pipeline` in try/except to fall back to direct R2R ingest. Figure manifest ingest follows the same pattern: failure logs a warning but does not break the main ingest response.

**Test structure** — existing tests in `tests/` mock R2R at the boundary and test pure functions directly. New tests follow this: pure helpers tested directly, R2R-touching paths mocked.

**No existing figure extraction pattern** — `figures_detected = 0` is an explicit stub with a comment naming "Phase 3+ extensions". This design is that extension.

## Implementation Phases

<!-- START_PHASE_1 -->
### Phase 1: Pure Helpers and Dependencies

**Goal:** Lay the deterministic foundation — pure helper functions, the `_CAPTION_RE` regex, deterministic ID generation — and add the missing `Pillow` dependency. Nothing touches the pipeline or API yet.

**Components:**
- `packages/ingestion/extract_figures_helpers.py` (Functional Core) — `nearest_caption(blocks, rect) -> str`, `figure_id_from(document_id, page_number, image_number, rect_index) -> str`, `_CAPTION_RE` compiled regex
- `requirements.txt` — add `Pillow>=10.0.0`
- `tests/test_extract_figures_helpers.py` — tests for all three exports: caption regex matching, nearest-caption distance logic, figure ID determinism

**Dependencies:** None (first phase)

**Done when:** `pytest tests/test_extract_figures_helpers.py` passes; `pip install -r requirements.txt` installs Pillow cleanly; all 98 existing tests still pass

<!-- END_PHASE_1 -->

<!-- START_PHASE_2 -->
### Phase 2: Figure Extractor Module

**Goal:** Implement `extract_figures()` and `write_figure_manifest()` — the Imperative Shell that uses PyMuPDF to extract raster images, run OCR, save PNGs, write `figures.json`, and produce the Markdown sidecar.

**Components:**
- `packages/ingestion/extract_figures.py` (Imperative Shell) — `extract_figures(pdf_path, document_id, source_file, min_width=80, min_height=80) -> list[dict]`, `write_figure_manifest(document_id, figures) -> Path | None`
- `data/figures/` directory convention — `data/figures/{document_id}/{figure_id}.png`, `data/figures/{document_id}/figures.json`, `data/figures/{document_id}/figures.md`
- Figure record schema: `{content_type, figure_id, document_id, source_file, page_number, bbox, asset_path, image_url, caption, ocr_text}`
- `tests/test_extract_figures.py` — integration tests using a synthetic in-memory PDF (one embedded PNG) or one of the existing `data/sample_docs/` PDFs; verifies record schema, file creation, OCR fallback on failure

**Dependencies:** Phase 1 (helpers + Pillow)

**Done when:** `extract_figures()` produces valid records and saved PNGs on at least one sample doc; `write_figure_manifest()` produces a valid `.md` file; tests pass; OCR failure is silently caught and returns `""`

<!-- END_PHASE_2 -->

<!-- START_PHASE_3 -->
### Phase 3: Pipeline and Quality Report Integration

**Goal:** Wire figure extraction into `run_pipeline()` and fix the `figures_detected` stub in `quality_report.py`. Also thread `source_file` and `original_filename` to their correct depths so temp filenames never appear in records.

**Components:**
- `packages/ingestion/pipeline.py` — `run_pipeline(pdf_path, document_id=None, source_file=None)` gains `source_file` param (defaults to `path.name`); calls `extract_figures()` and `write_figure_manifest()` after table normalization; return dict gains `"figures"` and `"figure_manifest"` keys; passes `figures=figures` to `generate_report()`
- `packages/ingestion/quality_report.py` — `generate_report()` gains `figures: list | None = None` param; sets `figures_detected = len(figures or [])`
- `tests/test_pipeline.py` — extend existing tests: verify `"figures"` key in return dict, `"figure_manifest"` key present, `quality_report["figures_detected"]` equals `len(figures)`

**Dependencies:** Phase 2 (extractor module)

**Done when:** `run_pipeline()` on a sample doc returns `figures` list and `figure_manifest` path; `figures_detected` in quality report is non-zero when figures are found; all existing pipeline tests still pass

<!-- END_PHASE_3 -->

<!-- START_PHASE_4 -->
### Phase 4: Figure Store Service

**Goal:** Implement the read-only service that loads per-document `figures.json` files and matches figures to RAG query results.

**Components:**
- `apps/api/services/figure_store.py` (Functional Core) — `load_figures(document_id=None) -> list[dict]` (globs `data/figures/*/figures.json`; returns `[]` if none exist), `figures_for_response(citations, retrieved_contexts, limit=6) -> list[dict]` (two-stage: regex scan for `Figure ID:` + page-match on `(source_file, page_number)` vs `(document, page)` from citations)
- `tests/test_figure_store.py` — tests: empty return when no `data/figures/` exists; stage 2 page-match with synthetic fixture; `limit` cap respected; deduplication between stages

**Dependencies:** Phase 3 (figures.json files exist after pipeline runs)

**Done when:** `figures_for_response()` returns correct figures given synthetic citation fixtures; returns `[]` gracefully on missing data directory; all tests pass

<!-- END_PHASE_4 -->

<!-- START_PHASE_5 -->
### Phase 5: API Layer Wiring

**Goal:** Connect figure extraction through the API — thread `original_filename` into the pipeline, ingest the Markdown sidecar into R2R, attach figures to `rag_query()` responses, and mount static file serving.

**Components:**
- `apps/api/routes/ingest.py` — pass `original_filename=file.filename` to `ingest_file_with_pipeline()`
- `apps/api/services/r2r_client.py` — `ingest_file_with_pipeline(file_path, original_filename=None)`: passes `source_file` to `run_pipeline()`; after successful PDF ingest, ingests figure manifest in try/except (warning logged on failure); return dict gains `"figures_r2r"` and `"figures"` keys. `rag_query()`: calls `figures_for_response()` before return; response gains `"figures"` key
- `apps/api/main.py` — conditional `StaticFiles` mount: `app.mount("/figures", StaticFiles(directory="data/figures"), name="figures")` only if `Path("data/figures").exists()`
- `tests/test_r2r_client.py` — extend: mock ingest returns correctly when figure manifest present; figure manifest ingest failure does not raise; `rag_query` return includes `"figures"` key

**Dependencies:** Phase 4 (figure store), Phase 3 (pipeline returns figure_manifest)

**Done when:** `/ingest` response includes `"figures"` list; `/ask` response includes `"figures"` list; figure manifest ingest failure is non-fatal; static files mount present in `main.py`; all tests pass

<!-- END_PHASE_5 -->

<!-- START_PHASE_6 -->
### Phase 6: Frontend Types and Rendering

**Goal:** Extend TypeScript types and render figure images in `AnswerCard`.

**Components:**
- `apps/web/lib/types.ts` — add `FigureAsset = {figure_id, source_file, page_number, image_url, caption?}`; extend `AskResponse` with `figures: FigureAsset[]`
- `apps/web/components/AnswerCard.tsx` — figure grid below citations: two-column responsive `<figure>/<img>/<figcaption>` grid, rendered only when `result.figures.length > 0`; `src` uses `NEXT_PUBLIC_API_URL ?? "http://localhost:8000"` prefix (follows existing pattern)

**Dependencies:** Phase 5 (API returns figures)

**Done when:** Frontend compiles without type errors; figure images render in the browser when `/ask` returns figures; no figures section shown when `figures` is empty; `NEXT_PUBLIC_API_URL` respected for image src

<!-- END_PHASE_6 -->

## Additional Considerations

**Idempotent re-ingest:** `figure_id` is deterministic from `(document_id, page_number, image_number, rect_index)`. Re-ingesting the same PDF overwrites `figures.json`, `figures.md`, and PNG files rather than appending duplicates. `extract_figures()` must write to the doc dir with overwrite semantics (not append).

**Conditional manifest ingest order:** Figure manifest is ingested only after the raw PDF ingest succeeds. A failed PDF ingest leaves no figure state in R2R.

**StaticFiles security:** `data/figures/` becomes web-accessible at `/figures/*`. Acceptable pre-security-review per `CLAUDE.md` (real client data lands in `data/do_not_commit/`). Flag for review before production use.

**Pixmap resolution:** `Matrix(2, 2)` (2× scale) is used for PNG extraction. This quadruples pixel count vs. 1×. Appropriate for demo-scale PDFs; revisit with `Matrix(1.5, 1.5)` if large multi-figure documents cause memory issues.

**Caption-anchored vector crops deferred:** The 320px-above-caption heuristic for vector charts/diagrams was evaluated and cut. Raster extraction covers the meaningful subset for demo docs. Revisit after seeing real document failure modes.
