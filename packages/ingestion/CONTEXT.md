# Ingestion Pipeline

Last verified: 2026-05-13

@status: active
@issues: none
@todo: DOCX/PPTX source display (SourcePanel shows "Could not load PDF" — convert to PDF via Docling or libreoffice for display)

## Purpose

The primary portfolio differentiator. Transforms raw business documents into citation-rich chunks for quality reporting and citation metadata extraction. Every stage is deterministic or rule-based except the final 10% LLM calls for genuine semantic ambiguity. The API now sends these DocQuery-authored chunks to R2R's `documents.create(chunks=[...])` path, with citation metadata embedded in a `DocQuery Citation:` header at the start of each chunk.

## Contracts

- **Exposes**:
  - `pipeline.run_pipeline(pdf_path, document_id=None, source_file=None) -> {"report", "chunks", "classifier", "figures", "figure_manifest"}` — orchestrates all six stages for PDFs only. `source_file` is the original uploaded filename; defaults to `pdf_path.name` so callers that don't pass it get the temp filename — pass it explicitly to avoid temp paths leaking into figure records and quality reports.
  - `pipeline.run_pipeline_for_source(path_or_url, source_file=None, collection_id=None) -> {"report", "chunks", "classifier", "figures", "figure_manifest"}` — entry point for DOCX, PPTX (via Docling), and web URLs (via crawl4ai). Returns the same shape as `run_pipeline`; `figures` and `figure_manifest` are always empty for non-PDF sources.
  - chunked documents with full citation metadata, quality reports written to `reports/ingestion/<doc_id>.json` + `.md`
  - figure assets and sidecar JSON written to `data/figures/<doc_id>/` (PNGs + `figures.json`); `figures.md` Markdown manifest written for R2R re-ingestion when figures are found (PDF only)
  - `extract_figures.extract_figures(pdf_path, document_id, source_file, ...) -> list[figure_record]` and `extract_figures.write_figure_manifest(document_id, figures) -> Path | None`
- **Guarantees**: every chunk carries the full citation metadata schema — `document_id`, `source_file`, `page_start`, `page_end`, `section_path`, `bbox`, `parser`, `chunk_template`, `confidence`. Chunks missing any field are invalid output. `run_pipeline` does NOT call R2R directly; the caller is responsible for sending returned chunks through `apps/api/services/r2r_client.ingest_prechunked_document()`. Figure records carry `figure_id`, `document_id`, `source_file`, `page_number`, `bbox`, `asset_path`, `image_url`, `caption`, `ocr_text`.
- **Expects**: raw PDFs or documents in `data/`; `.env` with `GOOGLE_API_KEY` for the 10% LLM calls; `tesseract` on PATH for figure OCR (silently degrades to empty `ocr_text` on failure)

## Dependencies

- **Uses**: R2R SDK (ingest endpoint), pdfplumber / pytesseract / camelot (parsers), PyMuPDF (`fitz`) + Pillow (figure extraction + clipping), Google Gemini via `langchain-google-genai` (LLM-only steps), docling>=2.0 (DOCX/PPTX conversion), crawl4ai>=0.6 (web scraping)
- **Used by**: `apps/api/` ingest route, `scripts/ingest_sample_docs.py`
- **Boundary**: never import from `apps/` or `packages/evals/`; this is the upstream producer

## Key Decisions

- **60/30/10 orchestration ratio**: ~60% deterministic (table normalization rules, regex classification, citation extraction), ~30% rule-based orchestration (parser routing, confidence thresholds, flow control), ~10% LLM (semantic ambiguity only — resolving ambiguous table relationships, intent classification where rules fail). Never use an LLM where a library or rule works.
- **Dual storage for tables**: raw markdown AND normalized sentence form both stored in chunk metadata — consumers pick what they need
- **RAGFlow patterns only**: layout-aware parsing, template chunking, visual citation inspection are borrowed from RAGFlow's approach; RAGFlow itself is not self-hosted

## Pipeline Stages

### PDF path
`classify_document.py` → `parse_pdf.py` → `normalize_tables.py` → `chunk_templates.py` → `extract_figures.py` → `quality_report.py`

1. **classify** — detects type (`general`, `paper`, `legal_contract`, `table_heavy`, `slide_deck`, `manual`), selects parser + chunking template
2. **parse** — routes to fast-text / OCR / table-aware / vision parser based on classifier output
3. **normalize** — converts raw table markdown to LLM-readable sentences
4. **chunk** — applies heading-aware / clause-aware / slide-page / table-aware chunking per type
5. **extract_figures** — extracts embedded raster images via PyMuPDF, clips at 2x scale, deduplicates by rounded bbox, OCRs each PNG, attaches nearest `Figure N` caption (≤160 px). FCIS split: `extract_figures_helpers.py` (Functional Core: `figure_id_from`, `nearest_caption`, `_CAPTION_RE`); `extract_figures.py` (Imperative Shell: file I/O, fitz calls, OCR). Writes `figures.json` + `figures.md` only when figures are found.
6. **quality_report** — per-document report: parser used, chunk count, tables detected, **figures detected**, low-confidence pages, citation coverage estimate

### Multi-format path
**Supported input types**: `run_pipeline(pdf_path)` — PDF only (existing path). `run_pipeline_for_source(path_or_url)` — DOCX, PPTX (via Docling), and web URLs (via crawl4ai). Non-PDF sources skip figure extraction and receive synthetic page bboxes (letter-size: `[0, 0, 612, 792]`).

## Invariants

- Citation metadata is complete on every chunk — no partial schemas
- LLM calls are isolated to the classify and normalize stages only — figure extraction is 100% deterministic (no LLM)
- Quality reports are always produced, even for low-confidence documents
- `figure_id_from(doc_id, page, image_number, rect_index)` is deterministic — re-ingesting the same PDF must overwrite assets, never duplicate them. Any change to the ID scheme breaks idempotency and orphans existing assets.

## Gotchas

- camelot v1.0.9 uses the **pdfium backend by default** — Ghostscript is NOT required for standard lattice/stream table extraction. Only add Ghostscript if you explicitly need the `backend='ghostscript'` path.
- OCR path is slow (~10s/page); test with small docs first
- `confidence` scores are heuristic, not calibrated — do not surface as exact probabilities
- **OCR_CHAR_THRESHOLD = 10** (`classify_document.py`): A page with fewer than 10 characters of extractable text is classified as scanned and routed to the OCR parser. This threshold catches genuinely scanned pages but risks misclassifying sparse-text cover pages or title-only pages as scanned. Bump to 50 if you observe false-positive OCR routing on real documents.
- **`bbox` precision**: Text chunks (heading-aware, clause-aware) compute a tight paragraph bbox using `_tight_bbox()` in `chunk_templates.py`, which matches extracted line bboxes from `parse_pdf.py::text_lines` against the chunk text. Table chunks get real region bboxes from camelot. OCR-path chunks fall back to the full-page bbox (no pdfplumber line data). If `_tight_bbox` finds no matching lines (e.g., all lines < 10 chars), it falls back to the full-page bbox — a known limitation for very sparse chunks.
