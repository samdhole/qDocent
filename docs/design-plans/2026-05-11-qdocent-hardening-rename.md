# qDocent Hardening + Rename Design

## Summary

This design plan hardens the existing qDocent RAG assistant for client-facing use and renames its branding from the internal working name "DocQuery" to "qDocent." The work is organized into five independent passes: a branding rename across the UI and API layer, authentication and CORS hardening, replacing the in-memory ingest job store with a SQLite-backed one, wiring up GitHub Actions CI, and documenting the licensing posture of key dependencies.

The approach is deliberately conservative: no new external services are introduced, no retrieval or evaluation paths change, and all R2R wire-format identifiers (the `"DocQuery Citation:"` chunk header and `"docquery_document_id"` metadata key) are left untouched to avoid invalidating previously ingested documents. Each pass is scoped to the smallest change that eliminates a concrete gap — string substitution for the rename, a one-liner environment read for CORS, a drop-in module swap for the job store — so phases can be reviewed and merged independently with low regression risk.

## Definition of Done

- All user-visible "DocQuery" strings replaced with "qDocent" across UI, docs, and localStorage keys (wire-format strings left unchanged)
- R2R auth enabled in `r2r_gemini.toml.example`; default admin password removed from committed config
- CORS origins read from `CORS_ORIGINS` env var instead of hardcoded `localhost:3000`
- Ingest jobs persist to SQLite; process restart no longer loses queued/running jobs
- Startup sweep flips orphaned `running` jobs to `failed` on restart
- GitHub Actions CI runs `pytest` + `vitest` on every push and PR
- Dependabot configured for pip and npm ecosystems
- `docs/licensing.md` documents PyMuPDF AGPL posture and all major dependency licenses
- All existing tests continue to pass

## Acceptance Criteria

### qdocent-hardening-rename.AC1: Branding rename complete
- **AC1.1 Success:** Browser tab title reads "qDocent" (`layout.tsx`)
- **AC1.2 Success:** Sidebar header label reads "qDocent" (`AppSidebar.tsx`)
- **AC1.3 Success:** Landing page `<h1>` reads "qDocent" (`page.tsx`)
- **AC1.4 Success:** FastAPI OpenAPI title reads "qDocent API" (`main.py`)
- **AC1.5 Success:** Login card title reads "qDocent" (`LoginCard.tsx`)
- **AC1.6 Success:** localStorage keys use `qdocent.*` prefix in all three hooks
- **AC1.7 Invariant:** `"DocQuery Citation:"` string unchanged in `r2r_chunk_adapter.py` (wire format preserved)
- **AC1.8 Invariant:** `"docquery_document_id"` metadata key unchanged in `r2r_client.py` (wire format preserved)

### qdocent-hardening-rename.AC2: Auth + CORS hardened
- **AC2.1 Success:** `r2r_gemini.toml.example` has `require_authentication = true`
- **AC2.2 Success:** `r2r_gemini.toml.example` has `default_admin_password = "CHANGE_ME"` (placeholder, not a real password)
- **AC2.3 Success:** `r2r_gemini.toml` listed in `.gitignore`
- **AC2.4 Success:** `apps/api/main.py` reads `CORS_ORIGINS` from env — no string literal `"http://localhost:3000"` in `allow_origins`
- **AC2.5 Success:** `.env.example` contains `CORS_ORIGINS=http://localhost:3000`

### qdocent-hardening-rename.AC3: SQLite ingest queue
- **AC3.1 Success:** `POST /ingest/jobs` creates a row in `data/ingest_jobs.db`
- **AC3.2 Success:** `GET /ingest/jobs/{id}` returns the job after API process is killed and restarted
- **AC3.3 Success:** A job in `running` state at shutdown is returned as `failed` on first `GET` after restart
- **AC3.4 Success:** `GET /ingest/jobs/{id}` returns 404 for terminal jobs older than 60 minutes
- **AC3.5 Failure:** Non-existent `job_id` returns 404
- **AC3.6 Invariant:** `POST /ingest/jobs` response shape unchanged (`{job_id, status}` with HTTP 202)
- **AC3.7 Invariant:** `GET /ingest/jobs/{id}` response shape unchanged (`{job_id, status, result?, error?}`)

### qdocent-hardening-rename.AC4: CI operational
- **AC4.1 Success:** Push to `master` triggers `.github/workflows/ci.yml`
- **AC4.2 Success:** `python-tests` job runs `pytest tests/` and all tests pass
- **AC4.3 Success:** `frontend-tests` job runs `npm test` in `apps/web/` and all tests pass
- **AC4.4 Success:** `.github/dependabot.yml` configured for `pip` (root) and `npm` (`apps/web`)
- **AC4.5 Success:** `make test` target exists and runs both suites locally

### qdocent-hardening-rename.AC5: Licensing documented
- **AC5.1 Success:** `docs/licensing.md` exists, lists PyMuPDF as AGPL-3.0, states commercial license required for closed-source deployment
- **AC5.2 Success:** `requirements.txt` `pymupdf` line has inline `# AGPL-3.0; commercial license required for closed-source deployment` comment
- **AC5.3 Success:** `README.md` has a `## Licensing` section linking to `docs/licensing.md`

## Glossary

- **R2R**: Open-source retrieval-augmented generation framework (by SciPhi-AI) that handles vector storage, document ingestion, and RAG query execution. qDocent wraps it behind a FastAPI layer; the UI never calls R2R directly.
- **RAG (Retrieval-Augmented Generation)**: A pattern where relevant document passages are retrieved from a vector store and injected into an LLM prompt before the model generates an answer, grounding responses in source material rather than training knowledge alone.
- **RAGAS**: A Python library for evaluating RAG pipelines. Produces faithfulness, answer relevancy, and context precision scores for a set of question/answer/context triples.
- **FastAPI**: Python web framework used for the `apps/api/` layer. Exposes the qDocent REST API on port 8000 and mediates all communication between the frontend and R2R.
- **LangGraph**: Graph-based workflow orchestration library from LangChain. Used in `packages/workflows/` for multi-step business logic (triage, approval, escalation); not involved in basic Q&A.
- **FCIS pattern (Functional Core / Imperative Shell)**: A module-level architectural convention enforced in this codebase. Pure-function modules are tagged `# pattern: Functional Core` and tested directly; I/O orchestrators are tagged `# pattern: Imperative Shell` and tested via mocks at the boundary.
- **Wire format**: The exact string representation embedded in data that has already been stored or transmitted — in this context, the `"DocQuery Citation:"` chunk header written into every R2R vector-store entry. Changing a wire-format string requires re-ingesting all existing documents.
- **Pre-chunked ingest**: The qDocent ingest path where the local DocQuery pipeline splits documents into chunks (each prefixed with citation metadata) and sends them to R2R via `documents.create(chunks=[...])`, rather than letting R2R chunk raw PDFs itself.
- **SQLite**: A lightweight, file-based relational database. Used in Phase 3 to persist ingest job state across process restarts without requiring a separate database service.
- **CORS (Cross-Origin Resource Sharing)**: A browser security mechanism that controls which origins can make HTTP requests to an API. The FastAPI layer must explicitly allow the frontend's origin; currently hardcoded to `localhost:3000`.
- **TOML**: A configuration file format used by R2R (`r2r_gemini.toml`). R2R reads auth settings, LLM provider routing, and embedding model selection from this file at startup.
- **Dependabot**: A GitHub service that automatically opens pull requests when dependencies in `requirements.txt` or `package.json` have newer published versions.
- **PyMuPDF / Artifex**: PyMuPDF is the Python PDF-parsing library used for figure extraction and layout-aware parsing. It is published under AGPL-3.0 by Artifex Software; closed-source commercial deployments require a separate commercial license from Artifex.
- **AGPL-3.0**: GNU Affero General Public License v3. A copyleft license that requires derived works — including software offered as a network service — to release their source code under the same terms unless a commercial license is obtained.
- **vitest**: JavaScript unit test runner used for the `apps/web/` Next.js frontend.
- **uvicorn**: ASGI server used to run the FastAPI application. Defaults to single-worker mode; multi-worker mode (`--workers N`) would require changes to the SQLite job store strategy.
- **litellm**: A Python library that provides a unified interface to multiple LLM providers. R2R uses it internally to route completion and embedding calls to Gemini.
- **TTL (Time-to-Live)**: The duration after which a record is considered expired and eligible for deletion. Phase 3 uses a 60-minute TTL for terminal ingest job records.
- **Startup sweep**: A one-time check run when the API process starts. In Phase 3 it finds any jobs left in `running` state (orphaned by a prior crash or kill) and marks them `failed` before the server begins accepting requests.

---

## Architecture

Five independent hardening passes applied to the existing qDocent scaffold. No new external services. No schema migrations to R2R. No changes to the retrieval or eval paths.

**Branding rename:** String substitution only. Five user-visible UI locations, README headings, and three localStorage key prefixes. The internal `"DocQuery Citation:"` chunk header and `"docquery_document_id"` R2R metadata key are deliberately unchanged — they are wire-format identifiers embedded in every ingested R2R chunk; renaming them would invalidate all previously ingested documents.

**Auth + CORS:** R2R auth is a server-side TOML setting — the FastAPI wrapper has zero awareness of it. The fix is: ship `r2r_gemini.toml.example` with `require_authentication = true` and a placeholder password, gitignore the real TOML (like `.env`), and add a one-liner to `apps/api/main.py` to read `CORS_ORIGINS` from the environment.

**SQLite ingest queue:** New module `apps/api/services/ingest_job_store.py` replaces the in-memory `_JOBS` dict in `apps/api/services/ingest_jobs.py`. Public API is identical so route files need no changes. A startup sweep in `apps/api/main.py` flips stale `running` jobs to `failed`. Temp-file lifecycle is unchanged (still deleted in `finally`).

**CI:** Two workflow files under `.github/workflows/`. No R2R server in CI — all existing tests mock R2R. Dependabot covers both ecosystems weekly.

**Licensing:** Documentation-only deliverable. No code changes to PyMuPDF usage; client procures Artifex commercial license separately.

---

## Existing Patterns

Investigation found the following patterns this design follows:

- **FCIS pattern:** Every Python production module starts with `# pattern: Functional Core` or `# pattern: Imperative Shell`. The new `ingest_job_store.py` (I/O) will be tagged `Imperative Shell`; TTL expiry logic extracted to a `Functional Core` helper following the same split used in `r2r_client_helpers.py`.
- **Env-driven config:** `apps/api/main.py` already reads `R2R_BASE_URL`, `LOG_LEVEL`, etc. from environment via `python-dotenv`. CORS origins follow the same pattern.
- **In-memory job store pattern (to be replaced):** `apps/api/services/ingest_jobs.py` exposes `create_job`, `update_job`, `get_job`, `run_ingest_job`. The SQLite store keeps the same public API so call sites in `apps/api/routes/ingest.py` are unmodified.
- **Makefile targets:** Existing targets (`make r2r`, `make api`, `make web`, `make eval`). New `make test` target follows the same pattern.

No existing CI or licensing documentation found.

---

## Implementation Phases

<!-- START_PHASE_1 -->
### Phase 1: Branding Rename
**Goal:** Replace all user-visible "DocQuery" strings with "qDocent". No logic changes.

**Components:**
- `apps/web/app/layout.tsx:18` — `title: "DocQuery"` → `"qDocent"`
- `apps/web/app/page.tsx:18` — `<h1>DocQuery</h1>` → `<h1>qDocent</h1>`
- `apps/web/components/AppSidebar.tsx:31` — sidebar header label
- `apps/web/components/LoginCard.tsx:28` — login card title
- `apps/api/main.py:11` — FastAPI OpenAPI title `"DocQuery API"` → `"qDocent API"`
- `apps/web/lib/useQueryMode.ts:8` — localStorage key `"docquery.queryMode"` → `"qdocent.queryMode"`
- `apps/web/lib/useAuthStub.ts:6` — localStorage key `"docquery.auth"` → `"qdocent.auth"`
- `apps/web/lib/useConversationStream.ts:8` — localStorage key `"docquery.messages"` → `"qdocent.messages"`
- `README.md` — heading, `cd docquery` reference, any branding mentions
- `apps/web/package.json` — `"name"` field (currently `"web"`, update to `"qdocent-web"` for clarity)

**Not changed:** `"DocQuery Citation:"` chunk header, `"docquery_document_id"` metadata key, `"docquery_pre_chunked"` ingestion mode, `DOCQUERY_API_BASE_URL` env var in `scripts/demo_readiness.py` (internal tooling).

**Dependencies:** None

**Done when:** No user-visible "DocQuery" string remains in the browser UI or page title. Existing vitest and pytest suites pass unchanged.
<!-- END_PHASE_1 -->

<!-- START_PHASE_2 -->
### Phase 2: Auth + CORS Hardening
**Goal:** Remove insecure defaults. Make CORS env-driven.

**Components:**
- `r2r_gemini.toml.example` (new file) — copy of current `r2r_gemini.toml` with `require_authentication = true`, `require_email_verification = true`, `default_admin_password = "CHANGE_ME"`. Document: set real password before first start, never commit the real TOML.
- `.gitignore` — add `r2r_gemini.toml` entry (keep `.example` tracked)
- `apps/api/main.py:18` — replace `allow_origins=["http://localhost:3000"]` with `allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")`
- `.env.example` — add `CORS_ORIGINS=http://localhost:3000`
- `CLAUDE.md` — update R2R startup section to reference `r2r_gemini.toml.example`

**Dependencies:** Phase 1 (establishes clean baseline)

**Done when:** No hardcoded `localhost` origin in Python source. `r2r_gemini.toml` is gitignored. `r2r_gemini.toml.example` committed with auth enabled and placeholder password. Existing tests pass (CORS config is not exercised by the mock-based test suite).
<!-- END_PHASE_2 -->

<!-- START_PHASE_3 -->
### Phase 3: SQLite Ingest Queue
**Goal:** Ingest job state survives process restart.

**Components:**
- `apps/api/services/ingest_job_store.py` (`# pattern: Imperative Shell`) — SQLite-backed job store. Database file at `data/ingest_jobs.db`. Exposes: `create_job`, `update_job`, `get_job`, `evict_expired`, `mark_stale_running_jobs`.
- `apps/api/services/ingest_job_ttl.py` (`# pattern: Functional Core`) — pure TTL expiry helpers: `is_expired(updated_at, ttl) → bool`, `is_terminal(status) → bool`.
- `apps/api/services/ingest_jobs.py` — replace `_JOBS` dict and `_LOCK` with calls to `ingest_job_store`. Public API (`create_job`, `update_job`, `get_job`, `run_ingest_job`) unchanged; route files untouched.
- `apps/api/main.py` — call `ingest_job_store.mark_stale_running_jobs()` at startup (after app init, before serving).
- `data/ingest_jobs.db` — added to `.gitignore`.

**Schema:**
```sql
CREATE TABLE IF NOT EXISTS jobs (
  job_id    TEXT PRIMARY KEY,
  filename  TEXT,
  status    TEXT,
  created_at TEXT,
  updated_at TEXT,
  result    TEXT,   -- JSON blob or NULL
  error     TEXT    -- error message or NULL
);
```

**Dependencies:** Phase 1 and 2 (clean baseline)

**Done when:** `POST /ingest/jobs` creates a SQLite row. Killing and restarting the API server does not return 404 for an existing job. A job that was `running` at shutdown is visible as `failed` after restart. `GET /ingest/jobs/{id}` returns 404 for jobs older than 60 minutes. Tests cover all four cases.
<!-- END_PHASE_3 -->

<!-- START_PHASE_4 -->
### Phase 4: CI Setup
**Goal:** Every push and PR runs the full test suite automatically.

**Components:**
- `.github/workflows/ci.yml` — two parallel jobs: `python-tests` (Python 3.11, pip install, `pytest tests/ -v`) and `frontend-tests` (Node 20, `npm ci`, `npm test` in `apps/web/`). Triggers: `push` and `pull_request` on `master`.
- `.github/dependabot.yml` — weekly updates for `pip` (root) and `npm` (`apps/web`).
- `Makefile` — add `test` target: runs pytest then vitest locally, matching CI.

**Dependencies:** Phase 3 (all tests must pass before wiring CI)

**Done when:** A push to `master` triggers the workflow. Both jobs pass. Dependabot PRs appear for outdated dependencies within a week of setup.
<!-- END_PHASE_4 -->

<!-- START_PHASE_5 -->
### Phase 5: Licensing Documentation
**Goal:** Client and contributors understand PyMuPDF AGPL posture and all major dependency licenses.

**Components:**
- `docs/licensing.md` (new) — table of all major dependencies, their licenses, and the PyMuPDF AGPL callout. States: "Closed-source deployments require an Artifex commercial PyMuPDF license."
- `requirements.txt:23` — inline comment on `pymupdf` line: `# AGPL-3.0; commercial license required for closed-source deployment`
- `README.md` — add "## Licensing" section linking to `docs/licensing.md` and calling out PyMuPDF explicitly.

**Dependencies:** None (docs-only, can run in parallel with any phase)

**Done when:** `docs/licensing.md` exists and is committed. `requirements.txt` PyMuPDF line has the inline comment. README has the Licensing section.
<!-- END_PHASE_5 -->

---

## Additional Considerations

**Wire-format stability:** `"DocQuery Citation:"` is embedded in every R2R chunk created by the pre-chunked ingest path. Any rename of this string requires a full re-ingest of all documents. This is explicitly out of scope.

**`r2r_gemini.toml` migration:** Existing local setups that already have `r2r_gemini.toml` will not be auto-updated. The `CLAUDE.md` update in Phase 2 documents the migration step (copy `.example`, set real password).

**SQLite concurrency:** The current ingest route is single-process (uvicorn default). SQLite's write locking is sufficient. If the client later moves to multi-worker uvicorn (`--workers N`), the job store will need a connection-pooling strategy or migration to Postgres.
