# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Last verified: 2026-05-16

**Evaluated AI Knowledge & Workflow Assistant** — a local-first RAG portfolio project and reusable client starter kit. The system ingests business documents (PDF, DOCX, PPTX, and web URLs), answers questions with citations, and produces reliability scores. Stack: **R2R** (retrieval) + **RAGAS** (eval) + **FastAPI** (API) + **Next.js/React** (UI) + optional **LangGraph** (workflows).

## Comms

- Use emojis freely and liberally throughout responses.
- Start every message with a kaomoji representing current feeling/mood (e.g. (ﾉ◕ヮ◕)ﾉ*:･ﾟ✧, (╯°□°）╯︵ ┻━┻, (´• ω •`), ┐(￣ヮ￣)┌, etc.c).
- Notice when you are confused or uncertain, use research agents to search the web or codebase to add context to the problem whenever things become uncertain or thorny. Then ask advisor.
- Take a haiku break anytime you feel like it would help you so you can work good and hard.

## Routing Table

Navigate by task — read only the relevant workspace.

| Task                           | Directory               | Also read                         |
| ------------------------------ | ----------------------- | --------------------------------- |
| Ingestion / parsing / chunking | `packages/ingestion/` | `packages/ingestion/CONTEXT.md` |
| RAGAS evaluation               | `packages/evals/`     | `packages/evals/CONTEXT.md`     |
| LangGraph workflows            | `packages/workflows/` | `packages/workflows/CONTEXT.md` |
| API routes and services        | `apps/api/`           | `apps/api/CONTEXT.md`           |
| Frontend UI                    | `apps/web/`           | `apps/web/CLAUDE.md`            |
| Scripts / smoke tests          | `scripts/`            | —                                |
| First-run install / launchers  | `install/`            | `install/README.md`             |

Each `CONTEXT.md` defines what "good output" means for that workspace — quality thresholds, success criteria, and domain-specific rules. `apps/web/` has a `CLAUDE.md` covering routes, components, and stream/query contracts. `scripts/` has no CONTEXT.md — conventions are standard enough to read from the code directly.

## Commands

Run each service in a separate terminal:

```bash
make setup      # Create venv + install deps
make r2r        # Start R2R server (port 7272)
make api        # Start FastAPI wrapper (port 8000)
make web        # Start web UI (port 3000)
make smoke      # Smoke test R2R connection + ingest
make ingest     # Ingest sample documents
make eval       # Run RAGAS evaluation, save to reports/evals/
make demo-check # Verify API, docs, citations, workflows, and latest eval artifact
make demo-setup # One-time corpus setup for /demo page (downloads Robinhood ARS, ingests, snapshots wiki/Q&A/figure)
make test       # Run full pytest + frontend vitest suites (mirrors CI)
make clean      # Remove pytest cache and eval reports
```

CI runs `make test` equivalents on every push/PR to `master` via `.github/workflows/ci.yml`; Dependabot watches pip + npm weekly via `.github/dependabot.yml`.

Individual scripts (from venv):

```bash
python scripts/create_sample_docs.py  # Generate 3 synthetic PDFs in data/sample_docs/
python scripts/smoke_r2r.py           # Test R2R connection + single doc ingest
python scripts/eval_ragas.py          # Run full RAGAS eval suite
python scripts/demo_readiness.py      # Check local commercial-demo readiness
python scripts/ingest_sample_docs.py
python scripts/reset_local_data.py
python scripts/ask.py "question"      # CLI RAG query
python scripts/setup_demo_corpus.py   # One-time /demo corpus ingest + snapshot capture (idempotent)
```

API dev server: `uvicorn apps.api.main:app --reload --port 8000`

## Architecture

### Service Topology

```
Business docs (PDF / DOCX / PPTX / URL)
     ↓
packages/ingestion/   (classify → parse → normalize → chunk → cite)
                      PDFs: full 6-stage pipeline via run_pipeline()
                      DOCX/PPTX/URL: python-docx/pptx + trafilatura → chunk via run_pipeline_for_source()
     ↓
R2R :7272             (retrieval, vector store, RAG responses)
     ↓
apps/api/ :8000       (FastAPI wrapper — never expose R2R SDK directly to frontend)
     ↓
apps/web/ :3000       (demo UI — ask, documents, reports, evals pages)
     ↓
packages/evals/       (RAGAS evaluation, offline, saves to reports/)
```

LangGraph (`packages/workflows/`) is additive — only used when multi-step business logic is required (triage, approval, escalation). R2R handles all basic Q&A without it.

Each package's `CONTEXT.md` defines the contracts, invariants, and quality thresholds for that layer — read it before editing that package.

## Environment

Copy `.env.example` → `.env` (never commit `.env`):

```bash
GOOGLE_API_KEY=
R2R_BASE_URL=http://localhost:7272
RAGAS_EVAL_MODEL=gemini-3-flash-preview
RAGAS_EMBEDDING_MODEL=models/text-embedding-004
APP_ENV=local
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000

# Frontend env vars (baked at Next.js build time; restart dev server after changing)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_DEMO_NOTEBOOK_ID=
```

`CORS_ORIGINS` is a comma-separated allowlist read by `apps/api/main.py`. Expand it before any non-local deployment.

`NEXT_PUBLIC_*` vars are baked into the Next.js bundle at build time — restart `make web` after changing them. `NEXT_PUBLIC_DEMO_NOTEBOOK_ID` is consumed by `apps/web/app/(app)/demo/DemoAskBox.tsx`: when set + `${NEXT_PUBLIC_API_URL}/health` returns 2xx within 2s, the panel renders a live `ConversationView` scoped to that notebook; otherwise it falls back to the cached snapshot in `apps/web/app/(app)/demo/data/example_qa.json`. Populate it after running `make demo-setup` (the script prints the `DEMO_NOTEBOOK_ID` on completion).

LLM provider is **Google Gemini** across the stack (R2R completion, R2R embeddings, RAGAS evaluator, LangGraph workflows). `langchain-google-genai>=2.0.0` is the only LLM SDK in `requirements.txt`. RAGAS embeddings default in `packages/evals/run_ragas.py` is `models/gemini-embedding-001`; the `.env.example` ships `models/text-embedding-004` to match R2R's lighter-weight retrieval embedding tier — pick one and keep them aligned per environment.

Python: 3.11. Node.js: 20 LTS. Docker 24.0.0+ required for full R2R mode.

## R2R Startup Modes

> **First-time setup:** Copy `r2r_gemini.toml.example` → `r2r_gemini.toml` and set a real
> `default_admin_password` before starting R2R. Never commit `r2r_gemini.toml` — it is gitignored.

R2R is configured via `r2r_gemini.toml` at the project root. `fast_llm`, `quality_llm`, and `chunk_enrichment.generation_config.model` point at `gemini/gemini-2.5-flash`; `vlm`, `reasoning_llm`, and `planning_llm` point at `gemini/gemini-2.0-flash`; embeddings at `gemini/gemini-embedding-2` (3072-dim). **Do not switch the agent-path LLMs back to `gemini-3-flash-preview`** — it has a `thought_signature` bug that breaks R2R's multi-tool agent loop (used by `/conversations/*/messages` and the streaming variant via `/retrieval/agent`). RAGAS eval, wiki generation, and suggested-question generation still use `gemini-3-flash-preview` directly (separate code paths, not via R2R). Do not start R2R without this config or it will fall back to OpenAI defaults and fail.

**Light mode** (fastest for local demo, recommended):

```bash
make r2r
# equivalent to:
R2R_CONFIG_PATH=r2r_gemini.toml uv run python -m r2r.serve
```

**Full Docker mode** (when needed):

```bash
git clone git@github.com:SciPhi-AI/R2R.git external/R2R
cd external/R2R
R2R_CONFIG_NAME=full GEMINI_API_KEY=<key> docker compose -f compose.full.yaml --profile postgres up -d
```

The Docker path has **not been re-validated against the Gemini config** since the migration — local light mode via `make r2r` is the supported workflow. If you need Docker, verify the upstream compose file actually mounts `r2r_gemini.toml` and forwards `GEMINI_API_KEY` to the litellm completion provider.

Keep upstream R2R under `external/` — never modify it directly. Wrap through the local API instead.

## Full-Stack Docker Deployment

The repo ships a project-owned `docker-compose.yml` at the root that runs all four services (`postgres`, `r2r`, `api`, `web`) for client handoff / VPS deployment. This is distinct from the upstream R2R compose file under `external/R2R/`.

```bash
cp .env.example .env          # or .env.example.client for handoff
docker compose up -d --build
```

- Service chain via healthchecks: `postgres` → `r2r` (depends_on healthy postgres) → `api` (depends_on healthy r2r) → `web`.
- `R2R_BASE_URL=http://r2r:7272` inside the compose network (the `.env.example` has both local and Docker values; uncomment the Docker line).
- R2R Postgres credentials are wired through `R2R_POSTGRES_{HOST,PORT,USER,PASSWORD,DBNAME}` and default to the in-compose `postgres` service. These are unused in local `make r2r` mode (R2R's built-in backend).
- `GOOGLE_API_KEY` is forwarded to R2R/litellm as `GEMINI_API_KEY` by `docker-compose.yml` — keep a single key in `.env`.
- `apps/web/next.config.ts` sets `output: "standalone"` so `docker/web/Dockerfile`'s three-stage build can copy the minimal Next.js server runtime. Do not remove `output: "standalone"` without updating the web Dockerfile.
- `.dockerignore` excludes `.venv/`, `data/`, `external/`, `.env*`, `node_modules/`, and `reports/` from build contexts. Add new local-state directories there if they appear at the repo root.
- Deployment guide: `docs/client-handoff/deployment.md` (gitignored per `docs/` rule; regenerated from `docs/design-plans/`).
- `.env.example.client` is the trimmed handoff env file — keep it in sync with `.env.example` when adding required vars.

## First-Run Install / Launcher Scripts

The `install/` directory ships first-run setup and daily-launch wrappers for client handoff on Windows and Linux. They are thin orchestrators over `docker compose` — no business logic lives here.

- `install/setup.ps1` / `install/setup.sh` — first-run wizard. Prompts for `GOOGLE_API_KEY` and (on setup.sh) admin password, writes `.env` from `.env.example.client`, runs `docker compose up -d --build`, waits for `api` health, opens the browser to `http://localhost:3000`.
- `install/start.ps1` / `install/start.sh` — daily launcher. Verifies Docker is running, runs `docker compose up -d` if any service is down, opens the browser. Does not rebuild.
- `install/README.md` — user-facing quickstart (Windows + Linux). The only doc in `install/` aimed at non-developers; keep it short.
- Tests in `tests/test_install_scripts.py` assert structural invariants only (script existence, required commands referenced, no hard-coded secrets) — they do not execute the scripts. Update them when adding/renaming scripts or required commands.
- Scripts target the project-owned root `docker-compose.yml` (see Full-Stack Docker Deployment), never the upstream R2R compose file.

## Tests

Pytest suite under `tests/` (currently ~48 test files, 537 test functions, including multi-format coverage: `test_format_router.py`, `test_docling_loader.py`, `test_web_loader.py`, plus URL-ingest cases in `test_route_notebooks.py`). Run with:

```bash
.venv/Scripts/python.exe -m pytest tests/ -v   # Windows
source .venv/bin/activate && pytest tests/ -v  # Unix
```

Human verification checklists in `docs/test-plans/` — latest: `2026-05-13-docker-handoff.md` (Docker handoff: AC1–AC6 across startup, persistence, env files, deployment doc, security, LF endings). Prior: `2026-05-13-demo-page.md` (16 ACs across /demo page phases).

## Key Design Constraints

- **RAGFlow is not self-hosted** — borrow its ingestion patterns only (layout-aware parsing, table normalization, template chunking, visual citation inspection, quality reports).
- `data/do_not_commit/` holds temporary sensitive local files; add to `.gitignore`. No real client data until security review.
- `requirements.txt` = human-maintained top-level deps. `requirements-lock.txt` = frozen after a confirmed working run.
- External LLM R2R responses must be transformed via `ragas.integrations.r2r.transform_to_ragas_dataset` before RAGAS evaluation.
- **60/30/10 orchestration ratio in `packages/ingestion/`:** ~60% deterministic code (table normalization rules, regex-based classification, citation metadata extraction), ~30% rule-based orchestration (parser routing logic, confidence thresholds, LangGraph flow control), ~10% LLM calls (semantic understanding only — resolving ambiguous table relationships, intent classification where rules fail). Never use an LLM where a library or rule works.
- **Naming:** No generic module names (`utils.py`, `helpers.py`, `common.py`). Use descriptive names (`table_normalization_helpers.py`, `citation_metadata_extractor.py`). Acceptable abbreviations: `id`, `url`, `http`, `db`, `api`, `auth`. Functions ≤ ~100 lines; files ≤ ~1,000 lines.
- **FCIS pattern:** Every production Python module must start with a `# pattern: Functional Core` or `# pattern: Imperative Shell` comment (type-only files exempt). This enforces testability at module boundaries — pure functions (FC) are tested directly; I/O orchestrators (IS) are mocked at the boundary.
- **Functional Core modules in `apps/api/services/`**: `r2r_client_helpers.py` (e.g. `_label_from_score`), `r2r_chunk_adapter.py` (DocQuery chunk headers for R2R pre-chunked ingest), `figure_store.py` (figure load + retrieval-time matching), `citation_marker_rewriter.py` (`rewrite_brackets` — rewrites R2R `[shortid]` markers to ordered `[N]` and reorders citations/retrieved_contexts in lockstep), `ingest_job_ttl.py` (`is_terminal`, `is_expired` — pure status + TTL predicates for the ingest job store), `notebook_helpers.py` (`generate_notebook_id`, `slug_from_name`), `wiki_xml_parser.py` (deepwiki-XML → `WikiStructure` dataclasses with single-page fallback on parse failure), and `wiki_prompts.py` (Gemini structure + page prompts) hold pure helpers split out from the Imperative Shell modules. Add future pure helpers to a matching FC module — never to `r2r_client.py`, `notebook_store.py`, or `wiki_store.py` directly.
- **Ingest job persistence:** async ingest job state lives in SQLite at `data/ingest_jobs.db` via `ingest_job_store.py` (IS). The file is gitignored and recreated on demand (`_connect()` mkdirs the parent). On API startup, `lifespan` calls `ingest_job_store.mark_stale_running_jobs()` which flips any `running` jobs to `failed` with `error="interrupted by restart"` (refreshes `updated_at` so they get a full TTL window). Terminal jobs older than 60 minutes are lazily evicted on read by `get_job`. There is no background sweeper — eviction happens on read, and the restart sweep happens once on startup.
- **Notebooks, wikis, conversations: separate SQLite stores per concern.** `notebook_store.py` (IS) owns `data/notebooks.db` (tables: `notebooks`, `notebook_documents`); `wiki_store.py` (IS) owns `data/wiki.db` (tables: `wiki_jobs`, `wiki_structure`, `wiki_pages`); `conversation_store.py` (IS) owns `data/conversations.db` (table: `conversations`, metadata only — R2R owns the actual message history). All three call `mkdir(parents=True, exist_ok=True)` on connect and `_ensure_tables()` per call so fresh clones need no setup. `lifespan` in `apps/api/main.py` also calls `notebook_store.migrate_default_notebook()` after the stale-ingest-jobs sweep — idempotent back-fill that creates a "Default Notebook" + R2R collection and assigns any pre-existing `data/documents/*/manifest.json` documents to it; per-manifest failures are caught and logged via `logger.warning` (never silently swallowed) so one bad manifest doesn't abort the sweep. Notebook deletion removes the R2R collection but preserves R2R documents. All four local stores — `data/ingest_jobs.db`, `data/notebooks.db`, `data/wiki.db`, `data/conversations.db` — plus `data/test_*.db` are gitignored.
- **Wiki generation pipeline:** `wiki_generator.generate_wiki(notebook_id, r2r_collection_id, job_id)` runs as a FastAPI `BackgroundTask` (not the `asyncio` ingest-jobs model). Step 1 — one Gemini call (`gemini-3-flash-preview`, temperature 0) returns deepwiki-style XML, parsed by `wiki_xml_parser.parse_wiki_structure_xml` (single-page "Overview" fallback on parse failure; strips markdown fences). Step 2 — pages are generated in parallel via `ThreadPoolExecutor(max_workers=4)`; each worker calls `r2r_client.rag_query` scoped to either the page's `source_doc_ids` or the notebook's `r2r_collection_id`, then invokes Gemini with `wiki_prompts.build_page_prompt`. Per-page failures store an error stub for that page but never fail the whole job. `wiki_store.increment_pages_done(job_id)` is a single atomic `UPDATE ... SET pages_done = pages_done + 1` inside `_LOCK` so parallel workers don't lose increments.
- **Conversation history is owned by R2R (not local SQLite).** `r2r_agent.agent_query()` and `agent_stream()` both call `/retrieval/agent` with the persistent `conversation_id`; R2R replays prior turns server-side. `conversation_store.py` only stores conversation metadata (id, notebook_id, title, timestamps) — it does **not** have an `add_message` / `get_messages` API or a `conversation_messages` table. Do not reintroduce client-side history injection via `task_prompt` for history — multi-turn is native. The streaming path handles `ToolCallEvent` (re-emits a `searching` status beat) and silently consumes `ToolResultEvent` / `ThinkingEvent`. **Agent search behavior:** `use_system_context=False` + a `task_prompt` is required on the `/retrieval/agent` call — gemini-2.5-flash with R2R's default system prompt asks the user for permission to search instead of searching automatically. The two cannot both be True (R2R 500 error). When `SearchResultsEvent` is not emitted (observed with `use_system_context=False`), `_async_search_chunks()` performs a post-stream `retrieval.search()` to supply citations/retrieved_contexts.
- **R2R ingest path:** `/ingest` runs the DocQuery pipeline first and sends returned chunks to `R2RClient.documents.create(chunks=[...])`. Each chunk starts with a `DocQuery Citation:` header containing `document_id`, `source_file`, `page_start`, `page_end`, `section_path`, and `chunk_index`; `rag_query()` parses this header out of retrieved text before returning citations and retrieved contexts. Raw PDF ingest is now only the fallback when the pipeline fails or emits no chunks. `r2r_client.ingest_file(file_path, collection_id=None)` forwards an optional `collection_id` as `collection_ids=[...]` to `documents.create`, and `ingest_file_with_pipeline` passes the caller's `collection_id` through both the raw-file fallback path and the `figures.md` manifest re-ingest — so all three sibling R2R documents (pre-chunked, fallback, figure manifest) land in the same notebook collection.
- **Multi-format ingest:** non-PDF sources (DOCX, PPTX, URL) take a parallel path. `POST /notebooks/{id}/documents` accepts `.pdf`, `.docx`, `.pptx` (whitelist in `_ALLOWED_EXTENSIONS`); `POST /notebooks/{id}/ingest/url` accepts `{url}`. Non-PDF sources route through `r2r_client.ingest_source_with_pipeline(path_or_url, original_filename, collection_id)` which calls `packages.ingestion.pipeline.run_pipeline_for_source()`. DOCX/PPTX use python-docx/python-pptx (`docling_loader.load_document_with_docling` — name retained for back-compat; parser field is `"python-docx/pptx"`, torch-free for slim image); URLs use trafilatura (`web_loader.load_url`). Both produce page dicts matching `parse_pdf.py`'s shape (synthetic letter-size bboxes `[0,0,612,792]`, empty `text_lines`) so downstream chunking is unchanged. Non-PDF sources skip figure extraction. URL ingest enforces SSRF protection via `_is_safe_url()` in `routes/notebooks.py` — rejects private, loopback, and link-local IPs with 422; URLs that fail trafilatura return 502.
- **Suggested questions caching:** both `ingest_file_with_pipeline` and `ingest_source_with_pipeline` call `question_generator.generate_questions()` with chunk text previews immediately after `write_chunks_manifest`, and persist the result to `data/documents/<doc_id>/questions.json` via `write_questions_cache`. `GET /documents/{id}/questions` is cache-first — serves the file instantly on hit; generates+caches on miss (self-healing for pre-existing docs). If `GOOGLE_API_KEY` is unset or Gemini fails, the write is silently skipped and the route falls back to on-demand generation.
- **Figure pipeline:** ingestion extracts embedded raster figures (PyMuPDF) into `data/figures/<doc_id>/`, writes `figures.json` + `figures.md`, and the API re-ingests the markdown sidecar into R2R so figure references are retrievable. The API serves PNGs at `/figures/...` — `apps/api/main.py` mkdirs `data/figures/` at startup, then mounts `StaticFiles` unconditionally, so the mount always exists (even on a fresh clone with no ingested documents). `/ask` responses include up to 6 matched figures via `figure_store.figures_for_response` (Stage 1 regex on retrieved text + Stage 2 page-match against citations).
