# qDocent

**Your company's second brain.** Drop in your business documents — PDFs, Word files, PowerPoints, or URLs — and get a searchable, conversational knowledge base with an auto-generated wiki, clickable citations, and matched figures.

Built as a local-first RAG portfolio project and reusable client starter kit.

---

## What it does

**1. Ingest any business document**
Upload PDFs, DOCX, PPTX, or paste a URL. The ingestion pipeline classifies the document, routes it to the right parser, normalises tables, extracts figures, and produces citation-rich chunks — each carrying source file, page range, section path, and bounding box.

**2. Auto-generate a structured wiki**
One click generates a navigable wiki from a notebook of documents: sections, pages, and Mermaid diagrams, all grounded in source passages. Parallel page generation with per-page failure isolation — one bad page never kills the whole job.

**3. Have a conversation**
Multi-turn streaming chat scoped to a notebook or a single document. Every answer cites the exact chunk it came from. Inline `[1]` markers expand on hover to show the verbatim passage, page, and document name.

**4. Click a citation — see the source**
The Source Panel opens the original PDF at the cited page with a yellow bounding-box highlight over the exact text region. No leaving the app to verify an answer.

**5. Figures surface automatically**
Figures embedded in PDFs are extracted, stored, and matched to answers — either by `Figure ID` marker in retrieved text or by page overlap with a citation. Up to 6 figures appear alongside any answer.

---

## Stack

| Layer | Technology |
|---|---|
| Retrieval / RAG | R2R ≥ 3.6.6 |
| Evaluation | RAGAS ≥ 0.4.3 |
| API | FastAPI + Uvicorn |
| Frontend | Next.js 16 (App Router) |
| Workflows | LangGraph ≥ 1.1.10 |
| PDF parsing | pdfplumber · camelot-py · PyMuPDF · pytesseract |
| DOCX / PPTX | Docling |
| URL ingestion | crawl4ai |
| PDF viewer | react-pdf (PDF.js) |
| LLM / embeddings | Google Gemini (`gemini-3-flash-preview`, `gemini-embedding-2`) |

**Runtime:** Python 3.11 · Node.js 20 LTS · [uv](https://github.com/astral-sh/uv) · Docker 24+ (full R2R mode only)

---

## Quick start

```bash
# 1. Clone and set up
git clone <this-repo> && cd docquery
make setup                # creates .venv, installs Python + Node deps

# 2. Configure
cp .env.example .env      # add GOOGLE_API_KEY
cp r2r_gemini.toml.example r2r_gemini.toml  # set admin password

# 3. Start services (three terminals)
make r2r                  # R2R retrieval server → :7272
make api                  # FastAPI wrapper      → :8000
make web                  # Next.js UI           → :3000
```

Open `http://localhost:3000` → create a notebook → upload documents → generate wiki.

---

## Notebooks

Everything is organised into **notebooks**. A notebook maps to an R2R collection so retrieval is scoped to its documents.

```
Notebook
├── Documents (PDF / DOCX / PPTX / URL)
├── Wiki (auto-generated, navigable)
└── Conversations (scoped to this notebook)
```

**Ingest a document:**
```bash
# Via UI: Notebooks → [notebook] → Upload
# Via API:
curl -X POST http://localhost:8000/notebooks/{id}/documents \
  -F "file=@report.pdf"

# URL ingest (SSRF-protected):
curl -X POST http://localhost:8000/notebooks/{id}/ingest/url \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/policy"}'
```

---

## Architecture

```
Business docs (PDF / DOCX / PPTX / URL)
     │
     ▼
packages/ingestion/
  classify → parse → normalise tables → chunk → extract figures → quality report
  PDFs:           pdfplumber / camelot / PyMuPDF / Tesseract OCR
  DOCX / PPTX:    Docling
  URLs:           crawl4ai (SSRF-protected)
     │
     ▼
R2R :7272          vector store · pre-chunked ingest · RAG retrieval
     │
     ▼
apps/api/ :8000    FastAPI wrapper (R2R SDK never exposed to frontend)
  /notebooks        CRUD + document membership
  /conversations    multi-turn SSE streaming chat
  /ask              single-shot RAG (used by RAGAS eval)
  /documents        source PDF · chunks manifest · suggested questions
  /wiki             generate · poll · read pages
  /figures          static PNG assets
     │
     ▼
apps/web/ :3000    Next.js 16 App Router
  /notebooks        grid + per-notebook view
  /notebooks/[id]   wiki tree nav + conversational chat
  /ask              standalone one-shot Q&A
  /documents        upload queue + source management
  /evals            RAGAS results table
     │
     ▼
packages/evals/    RAGAS offline evaluation → reports/evals/
packages/workflows/ LangGraph support-triage + email-draft graphs
```

---

## Commands

```bash
make setup        # create .venv + install deps
make r2r          # start R2R server (port 7272)
make api          # start FastAPI wrapper (port 8000)
make web          # start Next.js UI (port 3000)
make smoke        # smoke test: R2R connection + one-doc ingest
make ingest       # ingest sample docs into R2R
make eval         # run RAGAS evaluation (needs GOOGLE_API_KEY + R2R)
make demo-check   # verify API, docs, citations, workflows, latest eval
make test         # full pytest + vitest suites (mirrors CI)
make clean        # remove pytest cache and eval reports
```

---

## Environment variables

```bash
GOOGLE_API_KEY=                          # required for LLM + embeddings
R2R_BASE_URL=http://localhost:7272
RAGAS_EVAL_MODEL=gemini-3-flash-preview
RAGAS_EMBEDDING_MODEL=models/text-embedding-004
APP_ENV=local
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000       # comma-separated for multi-origin deploys
```

---

## R2R startup

> **First run:** copy `r2r_gemini.toml.example` → `r2r_gemini.toml` and set a real `default_admin_password`. Never commit `r2r_gemini.toml`.

**Light mode** (no Docker, recommended for local dev):
```bash
make r2r
# equivalent: R2R_CONFIG_PATH=r2r_gemini.toml uv run python -m r2r.serve
```

**Full Docker mode** (Postgres + complete pipeline):
```bash
git clone git@github.com:SciPhi-AI/R2R.git external/R2R
cd external/R2R
R2R_CONFIG_NAME=full GEMINI_API_KEY=<key> \
  docker compose -f compose.full.yaml --profile postgres up -d
```

R2R is configured via `r2r_gemini.toml`: all LLM slots point at `gemini/gemini-3-flash-preview` via litellm; embeddings use `gemini/gemini-embedding-2` (3072-dim).

---

## API reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `POST` | `/ask` | Single-shot RAG query |
| `POST` | `/ingest` | Upload PDF (legacy synchronous path) |
| `POST` | `/ingest/jobs` | Upload PDF → async ingest job |
| `GET` | `/ingest/jobs/{id}` | Poll async job status |
| `GET` | `/documents` | List stored documents |
| `GET` | `/documents/{id}/source` | Serve source PDF |
| `GET` | `/documents/{id}/chunks` | Chunk metadata (bbox, page, section) |
| `GET` | `/documents/{id}/questions` | Suggested questions (cache-first) |
| `DELETE` | `/documents/{id}` | Delete document + R2R records |
| `GET` | `/notebooks` | List notebooks |
| `POST` | `/notebooks` | Create notebook |
| `POST` | `/notebooks/{id}/documents` | Ingest file into notebook (.pdf/.docx/.pptx) |
| `POST` | `/notebooks/{id}/ingest/url` | Ingest URL into notebook |
| `POST` | `/notebooks/{id}/wiki/generate` | Kick off wiki generation |
| `GET` | `/notebooks/{id}/wiki/jobs/{job_id}` | Poll wiki generation progress |
| `GET` | `/notebooks/{id}/wiki` | Wiki structure (sections + page slugs) |
| `GET` | `/notebooks/{id}/wiki/{slug}` | Individual wiki page content |
| `POST` | `/conversations` | Create conversation |
| `POST` | `/conversations/{id}/messages` | Send message (blocking) |
| `POST` | `/conversations/{id}/messages/stream` | Send message (SSE streaming) |
| `GET` | `/eval/results` | Latest RAGAS scores |
| `POST` | `/eval/run` | Run RAGAS evaluation |
| `GET` | `/reports/ingestion/{id}` | Document quality report |
| `GET` | `/figures/{doc_id}/{fig_id}.png` | Figure image |
| `POST` | `/workflows/support/triage` | Support triage graph |
| `POST` | `/workflows/support/email-draft` | Draft approval-gated customer email |

---

## Testing

```bash
# Python (pytest)
.venv/Scripts/python.exe -m pytest tests/ -v   # Windows
source .venv/bin/activate && pytest tests/ -v  # Unix

# Frontend (vitest)
cd apps/web && npx vitest run
```

CI runs `make test` on every push to `master` via `.github/workflows/ci.yml`. Dependabot watches pip + npm weekly.

---

## Project layout

```
docquery/
├── apps/
│   ├── api/                   FastAPI app
│   │   ├── main.py            lifespan, mounts, CORS
│   │   ├── routes/            ask · ingest · documents · notebooks · conversations
│   │   │                      wiki · evals · reports · workflows
│   │   └── services/          r2r_client · r2r_agent · document_store · figure_store
│   │                          notebook_store · wiki_store · wiki_generator
│   │                          conversation_store · ingest_job_store · ragas_runner
│   └── web/                   Next.js 16 UI
│       ├── app/(app)/         route group (notebooks · ask · conversations · docs · evals)
│       ├── components/        AnswerCard · ConversationView · SourcePanel · CitationBadge
│       │                      NotebookGrid · WikiPage · WikiTreeNav · SuggestedQuestions
│       └── lib/               types · bboxConversion · remarkCitationBadges · useConversationStream
├── packages/
│   ├── ingestion/             6-stage PDF pipeline + Docling (DOCX/PPTX) + crawl4ai (URL)
│   ├── evals/                 RAGAS harness (eval_dataset.yaml + run_ragas.py)
│   └── workflows/             LangGraph support-triage + email-draft graphs
├── scripts/                   CLI utilities (ask · ingest · eval · demo-check · reset)
├── tests/                     pytest suite (100+ test functions)
├── data/
│   ├── sample_docs/           Sample PDFs for local demo
│   ├── documents/             Per-document artefacts (source PDF · chunks · questions)
│   └── figures/               Extracted figure PNGs
├── reports/
│   ├── evals/                 RAGAS CSV + Markdown (timestamped)
│   └── ingestion/             Per-document quality reports
├── Makefile
├── requirements.txt           Top-level Python deps (human-maintained)
├── requirements-lock.txt      Frozen after confirmed working run
└── .env.example
```

---

## Design notes

**60/30/10 rule** in `packages/ingestion/`: ~60% deterministic code (table normalisation, citation extraction), ~30% rule-based routing (parser selection, confidence thresholds), ~10% LLM calls (genuine semantic ambiguity only). Never use an LLM where a library or rule works.

**FCIS pattern**: every production module is annotated `# pattern: Functional Core` or `# pattern: Imperative Shell`. Pure functions are tested directly; I/O orchestrators are mocked at the boundary.

**Pre-chunked R2R ingest**: the pipeline produces citation-rich chunks sent to R2R via `documents.create(chunks=[...])`. Each chunk starts with a `DocQuery Citation:` header (document_id, source_file, page_start, page_end, section_path, chunk_index) that `rag_query()` parses back out — so citations are never `"unknown"`.

**R2R SDK isolation**: `r2r_client.py` and `r2r_agent.py` are the only files that import `r2r`. Routes and services never touch the SDK directly.

---

## Licensing

Most dependencies are MIT or Apache 2.0. **PyMuPDF** (`pymupdf`) is AGPL-3.0 — closed-source or proprietary deployments require a commercial licence from [Artifex](https://artifex.com/licensing/). See [`docs/licensing.md`](docs/licensing.md) for the full table.
