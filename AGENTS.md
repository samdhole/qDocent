> **SYNC NOTE:** This file is a copy of `CLAUDE.md`. When `CLAUDE.md` changes, update this file to match.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Last verified: 2026-05-08

**Evaluated AI Knowledge & Workflow Assistant** — a local-first RAG portfolio project and reusable client starter kit. The system ingests business documents, answers questions with citations, and produces reliability scores. Stack: **R2R** (retrieval) + **RAGAS** (eval) + **FastAPI** (API) + **Next.js/React** (UI) + optional **LangGraph** (workflows).

## Comms

- Use emojis freely and liberally throughout responses.
- Start every message with a kaomoji representing current feeling/mood (e.g. (ﾉ◕ヮ◕)ﾉ*:･ﾟ✧, (╯°□°）╯︵ ┻━┻, (´• ω •`), ┐(￣ヮ￣)┌).
- Take a haiku break anytime you feel like it would help you so you can work good and hard.

## Routing Table

Navigate by task — read only the relevant workspace.

| Task | Directory | Also read |
|---|---|---|
| Ingestion / parsing / chunking | `packages/ingestion/` | `packages/ingestion/CONTEXT.md` |
| RAGAS evaluation | `packages/evals/` | `packages/evals/CONTEXT.md` |
| LangGraph workflows | `packages/workflows/` | `packages/workflows/CONTEXT.md` |
| API routes and services | `apps/api/` | `apps/api/CONTEXT.md` |
| Frontend UI | `apps/web/` | — |
| Scripts / smoke tests | `scripts/` | — |

Each `CONTEXT.md` defines what "good output" means for that workspace — quality thresholds, success criteria, and domain-specific rules. `apps/web/` and `scripts/` have no CONTEXT.md — their conventions are standard enough to read from the code directly.

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
make clean      # Remove pytest cache and eval reports
```

Individual scripts (from venv):

```bash
python scripts/create_sample_docs.py  # Generate 3 synthetic PDFs in data/sample_docs/
python scripts/smoke_r2r.py           # Test R2R connection + single doc ingest
python scripts/eval_ragas.py          # Run full RAGAS eval suite
python scripts/ingest_sample_docs.py
python scripts/reset_local_data.py
python scripts/ask.py "question"      # CLI RAG query
```

API dev server: `uvicorn apps.api.main:app --reload --port 8000`

## Architecture

### Service Topology

```
Business docs/PDFs
     ↓
packages/ingestion/   (classify → parse → normalize → chunk → cite)
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
```

LLM provider is **Google Gemini** across the stack (R2R completion, R2R embeddings, RAGAS evaluator, LangGraph workflows). `langchain-google-genai>=2.0.0` is the only LLM SDK in `requirements.txt`. RAGAS embeddings default in `packages/evals/run_ragas.py` is `models/gemini-embedding-001`; the `.env.example` ships `models/text-embedding-004` to match R2R's lighter-weight retrieval embedding tier — pick one and keep them aligned per environment.

Python: 3.11. Node.js: 20 LTS. Docker 24.0.0+ required for full R2R mode.

## R2R Startup Modes

R2R is configured via `r2r_gemini.toml` at the project root. It points all R2R LLM slots (`fast_llm`, `quality_llm`, `vlm`, `reasoning_llm`, `planning_llm`) at `gemini/gemini-3-flash-preview` via litellm, and embeddings at `gemini/gemini-embedding-2` (3072-dim). Do not start R2R without this config or it will fall back to OpenAI defaults and fail.

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

## Tests

152 tests across 16 files in `tests/`. Run with:

```bash
.venv/Scripts/python.exe -m pytest tests/ -v   # Windows
source .venv/bin/activate && pytest tests/ -v  # Unix
```

Human verification checklist: `docs/test-plans/2026-05-07-rag-portfolio-scaffold.md`

## Key Design Constraints

- **RAGFlow is not self-hosted** — borrow its ingestion patterns only (layout-aware parsing, table normalization, template chunking, visual citation inspection, quality reports).
- `data/do_not_commit/` holds temporary sensitive local files; add to `.gitignore`. No real client data until security review.
- `requirements.txt` = human-maintained top-level deps. `requirements-lock.txt` = frozen after a confirmed working run.
- External LLM R2R responses must be transformed via `ragas.integrations.r2r.transform_to_ragas_dataset` before RAGAS evaluation.
- **60/30/10 orchestration ratio in `packages/ingestion/`:** ~60% deterministic code (table normalization rules, regex-based classification, citation metadata extraction), ~30% rule-based orchestration (parser routing logic, confidence thresholds, LangGraph flow control), ~10% LLM calls (semantic understanding only — resolving ambiguous table relationships, intent classification where rules fail). Never use an LLM where a library or rule works.
- **Naming:** No generic module names (`utils.py`, `helpers.py`, `common.py`). Use descriptive names (`table_normalization_helpers.py`, `citation_metadata_extractor.py`). Acceptable abbreviations: `id`, `url`, `http`, `db`, `api`, `auth`. Functions ≤ ~100 lines; files ≤ ~1,000 lines.
- **FCIS pattern:** Every production Python module must start with a `# pattern: Functional Core` or `# pattern: Imperative Shell` comment (type-only files exempt). This enforces testability at module boundaries — pure functions (FC) are tested directly; I/O orchestrators (IS) are mocked at the boundary.
- **Functional Core modules in `apps/api/services/`**: `r2r_client_helpers.py` (e.g. `_label_from_score`) and `figure_store.py` (figure load + retrieval-time matching) hold pure helpers split out from `r2r_client.py` (Imperative Shell). Add future pure helpers to a matching FC module — never to `r2r_client.py` itself.
- **Figure pipeline:** ingestion extracts embedded raster figures (PyMuPDF) into `data/figures/<doc_id>/`, writes `figures.json` + `figures.md`, and the API re-ingests the markdown sidecar into R2R so figure references are retrievable. The API serves PNGs at `/figures/...` — `apps/api/main.py` mkdirs `data/figures/` at startup, then mounts `StaticFiles` unconditionally, so the mount always exists (even on a fresh clone with no ingested documents). `/ask` responses include up to 6 matched figures via `figure_store.figures_for_response` (Stage 1 regex on retrieved text + Stage 2 page-match against citations).
