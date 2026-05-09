# API Layer

Last verified: 2026-05-09

@status: active
@issues: none
@todo: none

## Purpose

FastAPI wrapper between the frontend and R2R. Translates HTTP requests into service calls, enforces the 503 contract for R2R unavailability, and ensures the R2R SDK is never exposed directly to the frontend. Uploads can use either synchronous `/ingest` or local-process async jobs via `/ingest/jobs` and `/ingest/jobs/{id}`. Document cleanup deletes known R2R document IDs when a local manifest exists; sources without a manifest report empty `deleted`/`failed` lists. Multi-turn Q&A goes through `/conversations/*` (R2R agent path); single-shot `/ask` keeps the simpler RAG path for RAGAS eval and CLI scripts.

## Contracts

- **Exposes**: REST endpoints at `:8000` — `/health`, `/ask`, `/ingest`, `/ingest/jobs`, `/ingest/jobs/{id}`, `/documents`, `/documents/{id}/source`, `/documents/{id}/chunks`, `/documents/{id}/questions`, `/documents/{id}`, `/conversations`, `/conversations/{id}/messages`, `/conversations/{id}/messages/stream` (SSE), `/eval/results`, `/eval/run`, `/reports/ingestion/{id}`, `/workflows/support/triage`, `/workflows/support/email-draft`. Static files served at `/figures/<doc_id>/<fig_id>.png` — `main.py` mkdirs `data/figures/` at startup then mounts `StaticFiles` unconditionally, so the mount always exists (even on a fresh repo with no figures yet — requests just 404 until something is ingested).
- **Guarantees**: R2R failures on `/ask`, `/ingest`, `/ingest/jobs`, `/conversations`, `/conversations/{id}/messages` surface as HTTP 503 with `{"detail": "R2R unavailable: ..."}` — never 500. The streaming route `/conversations/{id}/messages/stream` cannot return a mid-stream 503 (headers already sent), so R2R failures emit a final `{"type": "error", "detail": "..."}` SSE frame instead. **DELETE `/documents/{id}` is the carve-out**: `r2r_client.delete_r2r_documents` never raises — R2R failures land in `r2r_delete.failed[]` so the local source PDF still gets cleaned up even when R2R is down. Non-PDF ingest returns 400. Missing eval results / source PDFs return 404. `/documents/{id}/chunks` always returns 200 with `{chunks: []}` when no manifest exists.
- **Expects**: running R2R at `R2R_BASE_URL`; `python-multipart` installed (required for `UploadFile` to work)

## Dependencies

- **Uses**: `apps/api/services/` (`r2r_client`, `r2r_agent`, `r2r_client_helpers`, `r2r_chunk_adapter`, `figure_store`, `document_store`, `ragas_runner`, `report_writer`); `packages/workflows/` (triage + email-draft graphs); `packages/ingestion/` (run_pipeline)
- **Used by**: `apps/web/` frontend only — never called directly from ingestion or eval packages
- **Boundary**: routes import from `services/` only; services import from packages; routes never import `r2r` SDK or package internals directly

## Key Decisions

- **`r2r_client.py` and `r2r_agent.py` are the only files that import `r2r`**: all SDK interaction is concentrated in these two modules. `r2r_client.py` owns the single-shot `retrieval.rag` path (used by `/ask`, RAGAS eval, scripts); `r2r_agent.py` owns the multi-turn `retrieval.agent` path (used by `/conversations/*`). Routes import `from apps.api.services import r2r_client` / `r2r_agent` — never `from r2r import ...`. The one exception is the workflow graphs in `packages/workflows/`, which embed their own `R2RClient` for retrieval — they predate the API service layer.
- **Conversation/agent path kept separate from RAG path**: `r2r_agent.agent_query()` and `agent_stream()` produce the same response dict shape as `r2r_client.rag_query()` plus a `conversation_id` field, so the frontend renderer is unchanged. Both accept two new optional params: `doc_only: bool = False` and `document_id: str | None = None`. When `document_id` is provided, `_build_search_settings` loads the document's manifest and injects `filters: {"document_id": {"$in": r2r_ids}}` into search settings (scoping retrieval to that document's R2R chunks); if the manifest has no R2R IDs a warning is logged and retrieval proceeds unscoped. When `doc_only=True`, `_apply_doc_only_check` is called post-hoc: if `retrieved_contexts` is empty or `confidence_label == "low"`, the answer is replaced with the canonical not-found string (`"I couldn't find this in your documents."`), `confidence_label` is forced to `"low"`, `needs_human_review` to `True`, and `doc_only_not_found: True` is added to the response dict. Adapter logic lives in `_adapt_agent_response` and is re-used by both query and stream paths (DRY). `_adapt_agent_response` also calls `rewrite_brackets` from `citation_marker_rewriter.py` to rewrite R2R `[shortid]` inline markers to ordered `[N]` and reorder `citations` / `retrieved_contexts` in lockstep (prose order first, uncited appended). The simpler `rag_query` is preserved so RAGAS eval and smoke scripts don't pay agent overhead and don't need conversation state.
- **SSE streaming response headers**: `/conversations/{id}/messages/stream` sets `Cache-Control: no-cache, no-transform`, `X-Accel-Buffering: no`, `Connection: keep-alive` — load-bearing to defeat nginx and Next.js dev-proxy buffering. Event types emitted: `status` (`searching` / `found_results` / `generating` phase beats), `token` (text deltas), `final` (full adapter dict), `error` (R2R mid-stream failure). The route always emits a terminal `final` event, even if the SDK loop exits without `FinalAnswerEvent` (defensive).
- **FCIS split in services**: pure helpers live in dedicated `# pattern: Functional Core` modules — `r2r_client_helpers.py` (`_label_from_score`, `_valid_chunks`), `r2r_chunk_adapter.py` (`chunks_for_r2r`, `citation_from_retrieved_text`), `figure_store.py` (`load_figures`, `figures_for_response`), and `citation_marker_rewriter.py` (`rewrite_brackets`). `r2r_client.py`, `r2r_agent.py`, and `document_store.py` (`# pattern: Imperative Shell`) hold all I/O. Add future pure helpers to the matching helpers file or create a new FC module.
- **Document store persists two manifests per document**: `data/documents/<doc_id>/manifest.json` (R2R document IDs, written by `write_document_manifest`, used for cleanup) and `data/documents/<doc_id>/chunks.json` (per-chunk `{chunk_index, page_start, page_end, bbox, section_path, text_preview}`, written by `write_chunks_manifest`, served by `GET /documents/{id}/chunks` and consumed by the web SourcePanel for bbox highlighting). Both are written at ingest time on the pre-chunked path; the raw-file fallback path writes neither (no chunk metadata available). Corrupt or missing manifests return `None` and the route returns an empty list — never 500.
- **Figure matching strategy in `figure_store.figures_for_response`**: two-stage deduplicated match. **Stage 1** regex-scans `retrieved_contexts[].text` for `Figure ID: <id>` markers from the ingested `figures.md` sidecar. **Stage 2** page-matches figures whose `(source_file, page_number)` overlaps with a citation's `(document, page)`. Stage 2 is now viable for DocQuery-ingested documents because pre-chunked R2R ingest preserves citation headers and `rag_query()` parses them back into real `document`/`page` citation values. The `_FIGURE_ID_RE` charset `[A-Za-z0-9_\-]` assumes alphanumeric figure IDs from `extract_figures_helpers.figure_id_from` — changing the ID scheme to include `.` or other characters requires updating the regex too.
- **R2R SDK response peeling (r2r>=3.6.6 with `core`)**: `client.retrieval.rag(...)` now returns a wrapper whose payload lives under `.results`, and `search_results` is an `AggregateSearchResult` whose chunk hits live under `.chunk_search_results`. The peeling pattern is:
  ```python
  inner = getattr(response, "results", response)
  agg = getattr(inner, "search_results", None)
  chunks = getattr(agg, "chunk_search_results", None) or [] if agg else []
  answer = getattr(inner, "generated_answer", None) or str(inner)
  ```
  Repeated in `r2r_client.rag_query`, `support_triage_graph.retrieve_context`, and `email_draft_graph.retrieve_policy`. If the SDK shape changes again, update all three.
- **`/eval/run` is synchronous** (plan specified `BackgroundTasks`): synchronous execution ensures errors propagate as 503; background tasks silently swallow eval failures. Response: `{"status": "ok", "message": "Evaluation completed successfully."}`.
- **`/ingest` uses a temp file**: `UploadFile` bytes are written to `tempfile.NamedTemporaryFile` before being passed to the pipeline. The temp file is deleted in `finally` regardless of success or failure. The route passes `file.filename` as `original_filename` so figure records and quality reports show the real uploaded name, not the temp path.
- **Pipeline-backed `/ingest` is the primary path**: `ingest_file_with_pipeline` sends DocQuery-produced chunks to R2R via `documents.create(chunks=[...])`. Each chunk starts with a `DocQuery Citation:` header containing `document_id`, `source_file`, `page_start`, `page_end`, `section_path`, and `chunk_index`; `rag_query` parses this header back out so citations are not `unknown`. **Citation field precedence is header-first**: when both the parsed header and R2R chunk `metadata` carry the same field (`document`, `page`, `page_end`, `section`), the header value wins — DocQuery is the authoritative source for citation metadata. Chunks missing any of `text`, `document_id`, or `source_file` are dropped by `_valid_chunks` before the pre-chunked call (warning logged with drop count). If the pipeline raises, returns no chunks, **or all chunks are dropped as invalid**, the service falls back to plain raw-file `ingest_file` and still saves the source PDF when `report.document_id` is present. The `figures.md` manifest is also re-ingested into R2R after the primary document — manifest-ingest failure is logged as a warning, not raised.
- **CORS locked to `localhost:3000`**: `main.py` allows `http://localhost:3000` only. Expand this list before any production deployment.

## Response shapes

```
POST /ask       → {question, answer, citations[], retrieved_contexts[], figures[], confidence_label, needs_human_review}
POST /ingest    → {status: "ok", result: {r2r, quality_report, document_id, figures[], figures_r2r}}
POST /ingest/jobs → {job_id, status}
GET  /ingest/jobs/{id} → {job_id, status, result?, error?}
GET  /documents → {documents: [{document_id, source_file, source_url, size_bytes, updated_at}]}
GET  /documents/{id}/source → source PDF file
GET  /documents/{id}/chunks → {document_id, chunks: [{chunk_index, page_start, page_end, bbox, section_path, text_preview}]}
GET  /documents/{id}/questions → {document_id, questions: [str, ...]} (0-6 LLM-generated; 404 if no chunks.json; empty list if GOOGLE_API_KEY unset or LLM fails)
DELETE /documents/{id} → {status, document_id, r2r_delete: {deleted: [r2r_id...], failed: [r2r_id...]}}
POST /conversations → {conversation_id}
POST /conversations/{id}/messages → body: {message, doc_only?: bool, document_id?: str} → same shape as /ask + {conversation_id, doc_only_not_found?: bool}
POST /conversations/{id}/messages/stream → body: {message, doc_only?: bool, document_id?: str} → text/event-stream of {type: status|token|final|error, ...}; final.result has same shape as above
GET  /eval/results → [{question_id, answer_relevancy, context_precision, faithfulness, ...}]
POST /eval/run  → {status: "ok", message: "..."}
GET  /reports/ingestion/{id} → quality report JSON
GET  /figures/{doc_id}/{fig_id}.png → static PNG asset (mount is always created at startup; 404 until figures exist)
POST /workflows/support/triage      → SupportState dict (8 fields)
POST /workflows/support/email-draft → SupportState dict (requires_human_approval always true)
```

Citations now carry `document_id`, `chunk_id`, and `chunk_index` (from the parsed `DocQuery Citation:` header) so the web SourcePanel can resolve clicks back to the source PDF + bbox. `figures[]` items in `/ask` carry `figure_id`, `source_file`, `page_number`, `image_url`, `caption`, capped at 6 per response. `image_url` is server-relative (`/figures/<doc_id>/<fig_id>.png`) — the frontend prepends the API origin.

## Invariants

- `confidence_label` ∈ `{high, medium, low, needs_review}` — derived from top R2R search score via `_label_from_score`; thresholds: high ≥ 0.80, medium ≥ 0.50, low < 0.50
- When `doc_only=True` and retrieval is empty or low-confidence, the response answer is replaced with `"I couldn't find this in your documents."`, `confidence_label` is forced to `"low"`, `needs_human_review` to `True`, and `doc_only_not_found: True` is added. This check is applied post-hoc after the R2R round-trip, so partial retrieval still lands in `retrieved_contexts`.
- Routes catch `RuntimeError` (raised by services on R2R failure) and re-raise as `HTTPException(503)`. Exception: the DELETE route swallows R2R failures into `r2r_delete.failed[]` and never returns 503 for R2R errors — only for missing local source PDFs (404).
- `r2r_client.py` catches `(httpx.HTTPError, R2RException)` and re-raises as `RuntimeError("R2R unavailable: ...")`. `R2RException` is imported from `shared.abstractions.exception` (vendored by `r2r[core]`) — without it, R2R-side validation errors would bubble up as 500s instead of the contracted 503.
- **Async ingest job TTL**: `ingest_jobs._JOB_TTL = 60 minutes`. Terminal jobs (`completed` / `failed`) are lazily evicted from the in-memory `_JOBS` dict on the next `get_ingest_job(id)` call once their `updated_at` is older than the TTL — `GET /ingest/jobs/{id}` returns `404` for evicted jobs. Active (`queued` / `running`) jobs are never expired. There is no background sweeper; eviction only happens on read.

## Gotchas

- `python-multipart` must be in `requirements.txt` — without it FastAPI silently rejects `UploadFile` requests with a 422
- `UploadFile.filename` can be `None` — the ingest route guards this before the `.endswith(".pdf")` check
- Workflow routes pass the full request body as `{"message": "..."}` — the LangGraph graphs accept a plain string, not the raw dict
