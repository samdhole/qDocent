# DocQuery

**Evaluated AI Knowledge & Workflow Assistant** — a local-first RAG portfolio project and reusable client starter kit.

The system ingests business documents (PDFs), answers questions with citations and confidence scores, evaluates answer quality with RAGAS, and routes complex requests through approval-gated LangGraph workflows.

## What it demonstrates

- **Differentiated ingestion**: classifies PDFs by type (text-heavy, table-heavy, scanned) and routes to the right parser — pdfplumber, camelot, or Tesseract OCR
- **Citation-rich chunking**: every chunk carries a 9-field metadata schema (`document_id`, `source_file`, `page_start`, `page_end`, `section_path`, `bbox`, `parser`, `chunk_template`, `confidence`)
- **Quality reporting**: per-document JSON + Markdown ingestion report (tables detected, low-confidence pages, citation coverage estimate)
- **RAG with confidence**: R2R retrieval answers questions with `high`/`medium`/`low` confidence labels and a `needs_human_review` flag
- **RAGAS evaluation**: automated scoring across AnswerRelevancy, ContextPrecision, and Faithfulness — including deliberate negative questions to test refusal
- **Workflow automation**: LangGraph support-triage graph with a human-approval gate for refunds, discounts, legal questions, and low-confidence answers

## Architecture

```
Business docs (PDFs)
     ↓
packages/ingestion/        classify → parse → normalize → chunk → quality report
     ↓
R2R :7272                  vector store + RAG responses
     ↓
apps/api/ :8000            FastAPI wrapper (never expose R2R SDK to frontend)
     ↓
apps/web/ :3000            Next.js 16 demo UI (Ask, Documents, Workflows, Evals pages)
     ↓
packages/evals/            RAGAS offline evaluation → reports/evals/
packages/workflows/        LangGraph triage + email-draft graphs (additive)
```

## Stack

| Layer | Technology |
|-------|-----------|
| Retrieval / RAG | R2R ≥ 3.6.6 |
| Evaluation | RAGAS ≥ 0.4.3 |
| API | FastAPI + Uvicorn |
| Frontend | Next.js 16 (App Router) |
| Workflows | LangGraph ≥ 1.1.10 |
| PDF parsing | pdfplumber, camelot-py (pdfium), PyMuPDF, pytesseract |
| LLM / embeddings | Google Gemini (`gemini-3-flash-preview`, `gemini-embedding-2`) |

**Runtime requirements:** Python 3.11 · Node.js 20 LTS · [uv](https://github.com/astral-sh/uv) · Docker 24+ (full R2R mode only)

## Quick start

```bash
# 1. Clone and set up Python environment
git clone <this-repo>
cd docquery
make setup           # creates .venv and installs deps

# 2. Configure environment
cp .env.example .env
# Edit .env: add GOOGLE_API_KEY

# 3. Generate sample documents
python scripts/create_sample_docs.py

# 4. Start services (each in its own terminal)
make r2r             # R2R server  → :7272
make api             # FastAPI     → :8000
make web             # Next.js UI  → :3000

# 5. Ingest sample docs and verify
make smoke           # connection smoke test
make ingest          # ingest company_policy.pdf, pricing_table.pdf, sample_support_history.pdf
make demo-check      # verify API, docs, citations, workflows, and latest eval artifact
```

Then open `http://localhost:3000`.

Commercial-demo status and evidence are tracked in `docs/handoff.md` and `docs/commercial-demo-completion-audit-2026-05-08.md`.

## Commands

```bash
make setup           # Create .venv + install Python deps
make r2r             # Start R2R retrieval server
make api             # Start FastAPI wrapper
make web             # Start Next.js UI (npm install + dev server)
make smoke           # Smoke test: connect to R2R, ingest one doc, run RAG query
make ingest          # Ingest all PDFs in data/sample_docs/
make eval            # Run RAGAS evaluation (requires GOOGLE_API_KEY + running R2R)
make demo-check      # Check commercial-demo readiness before showing it
make clean           # Remove pytest cache and eval reports
```

Individual scripts (activate venv first: `.venv/Scripts/activate`):

```bash
python scripts/ask.py "What is the refund policy?"
python scripts/create_sample_docs.py    # regenerate sample PDFs
python scripts/ingest_sample_docs.py    # bulk ingest
python scripts/eval_ragas.py            # run eval, save timestamped CSV + MD
python scripts/demo_readiness.py        # check API/docs/ask/workflows/eval readiness
python scripts/reset_local_data.py      # delete all R2R docs + report files
```

## Environment variables

Copy `.env.example` → `.env` (never commit `.env`):

```bash
GOOGLE_API_KEY=...
R2R_BASE_URL=http://localhost:7272
RAGAS_EVAL_MODEL=gemini-3-flash-preview
RAGAS_EMBEDDING_MODEL=models/gemini-embedding-001
APP_ENV=local
LOG_LEVEL=INFO
```

## R2R startup modes

**Light mode** (fastest, no Docker):

```bash
make r2r
# or: uv run python -m r2r.serve
```

**Full Docker mode** (Postgres + full pipeline):

```bash
git clone git@github.com:SciPhi-AI/R2R.git external/R2R
cd external/R2R
R2R_CONFIG_NAME=full GEMINI_API_KEY=<key> \
  docker compose -f compose.full.yaml --profile postgres up -d
```

Keep upstream R2R under `external/` — never modify it. Wrap everything through `apps/api/`.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness check → `{"status":"ok"}` |
| `POST` | `/ask` | RAG query → `{answer, citations, retrieved_contexts, confidence_label, needs_human_review}` |
| `POST` | `/ingest` | Upload PDF → runs ingestion pipeline + ingest to R2R |
| `POST` | `/ingest/jobs` | Upload PDF → queue an async ingest job |
| `GET` | `/ingest/jobs/{id}` | Poll async ingest job status/result |
| `GET` | `/documents` | List stored source PDFs |
| `GET` | `/documents/{id}/source` | Serve the stored source PDF for clickable citations |
| `DELETE` | `/documents/{id}` | Delete stored source PDF and known R2R documents |
| `GET` | `/eval/results` | Latest RAGAS scores (CSV rows) |
| `POST` | `/eval/run` | Trigger RAGAS evaluation (synchronous) |
| `GET` | `/reports/ingestion/{id}` | Quality report for a document |
| `POST` | `/workflows/support/triage` | Run support triage graph |
| `POST` | `/workflows/support/email-draft` | Draft customer email (always approval-gated) |

## Testing

```bash
# Run full test suite (192 tests)
.venv/Scripts/python.exe -m pytest tests/ -v   # Windows
source .venv/bin/activate && pytest tests/ -v  # Unix
```

Test coverage:
- `tests/test_api_routes.py` — FastAPI routes (health, ask, eval, reports)
- `tests/test_r2r_client.py` — confidence label helper, pre-chunked ingest wiring, retrieval citation parsing
- `tests/test_r2r_chunk_adapter.py` — DocQuery citation headers for R2R chunks
- `tests/test_report_writer.py` — report reader service
- `tests/test_document_store.py` — persisted source PDF storage, manifest metadata, and delete
- `tests/test_classify_document.py` — PDF type classification rules
- `tests/test_normalize_tables.py` — table normalization (dual storage, header promotion)
- `tests/test_chunk_templates.py` — 9-field chunk schema across all template types
- `tests/test_quality_report.py` — quality report generation + file output
- `tests/test_parse_pdf.py` — PDF parsing (fast-text, table-aware, OCR paths)
- `tests/test_pipeline.py` — end-to-end ingestion pipeline
- `tests/test_ingest_jobs.py` — async ingest job state transitions
- `tests/test_demo_readiness.py` — local commercial-demo readiness checks
- `tests/test_extract_figures.py` — figure extraction pipeline (PyMuPDF, bbox, dedup)
- `tests/test_extract_figures_helpers.py` — figure ID generation, caption detection
- `tests/test_figure_store.py` — figure loading + Stage 1/2 response matching
- `tests/test_approval_policy.py` — approval policy rules + confidence scoring
- `tests/test_eval_dataset.py` — RAGAS dataset breadth and refusal coverage
- `tests/test_run_ragas.py` — RAGAS metric construction compatibility
- `tests/test_script_entrypoints.py` — direct script entrypoint importability
- `tests/test_support_triage_graph.py` — support triage LangGraph (mocked)
- `tests/test_email_draft_graph.py` — email draft LangGraph (mocked, deterministic fallback without `GOOGLE_API_KEY`)
- `tests/test_route_ingest.py`, `test_route_reports.py`, `test_route_workflows.py` — API route tests
- `tests/test_route_documents.py` — source PDF route tests

Human verification scenarios: `docs/test-plans/2026-05-07-rag-portfolio-scaffold.md`

## Project layout

```
docquery/
├── apps/
│   ├── api/                  FastAPI app
│   │   ├── main.py
│   │   ├── routes/           ask, ingest, evals, documents, reports, workflows
│   │   └── services/         r2r_client, r2r_client_helpers, document_store, figure_store, ragas_runner, report_writer
│   └── web/                  Next.js 16 UI
│       ├── app/              App Router pages
│       ├── components/       AskForm, AnswerCard, EvalTable
│       └── lib/types.ts      Shared TypeScript types
├── packages/
│   ├── evals/                RAGAS evaluation harness
│   │   ├── eval_dataset.yaml 12 questions across policy, pricing, architecture, and refusal
│   │   └── run_ragas.py      load_dataset() + run_eval()
│   ├── ingestion/            Differentiated PDF ingestion pipeline
│   │   ├── classify_document.py
│   │   ├── parse_pdf.py
│   │   ├── normalize_tables.py
│   │   ├── chunk_templates.py
│   │   ├── extract_figures.py
│   │   ├── extract_figures_helpers.py
│   │   ├── quality_report.py
│   │   └── pipeline.py
│   └── workflows/            LangGraph approval-gated workflows
│       ├── state.py          SupportState TypedDict
│       ├── approval_policy.py
│       ├── support_triage_graph.py
│       └── email_draft_graph.py
├── scripts/                  CLI utilities
├── tests/                    192 pytest tests
├── data/sample_docs/         Generated sample PDFs (3 documents)
├── reports/
│   ├── evals/                RAGAS CSV + Markdown reports (timestamped)
│   └── ingestion/            Per-document JSON + Markdown quality reports
├── docs/
│   ├── implementation-plans/ Phase-by-phase build plan
│   └── test-plans/           Human verification checklist
├── Makefile
├── requirements.txt          Top-level deps (human-maintained)
├── requirements-lock.txt     Frozen after confirmed working run
└── .env.example
```

## Design decisions

**60/30/10 orchestration ratio** (in `packages/ingestion/`): ~60% deterministic code, ~30% rule-based orchestration, ~10% LLM calls for genuine semantic ambiguity. Never use an LLM where a library or rule works.

**FCIS pattern**: every production module is marked `# pattern: Functional Core` or `# pattern: Imperative Shell` to enforce testability at module boundaries.

**DocQuery chunks are the R2R ingest path**: the ingestion pipeline produces citation-rich chunks, and the API sends them to R2R with `documents.create(chunks=[...])`. Each chunk starts with a compact `DocQuery Citation:` header so retrieved chunks can be mapped back to `source_file`, page, and section. If the pipeline fails or emits no chunks, ingest falls back to raw PDF upload.

**Approval gate is in-node**: the LangGraph `send_response` node enforces the approval gate by returning `"[Awaiting human approval]"` — no `interrupt_before` or LangGraph checkpointer is required.

**RAGFlow patterns, not RAGFlow**: layout-aware parsing, table normalization, template chunking, and visual citation inspection are borrowed from RAGFlow's design; RAGFlow is not self-hosted.
