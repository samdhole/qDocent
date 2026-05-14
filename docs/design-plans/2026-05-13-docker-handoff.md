# Docker Handoff Design

## Summary

This design containerises the full qDocent application stack — Postgres (with pgvector), R2R, FastAPI, and Next.js — behind a single `docker compose up` command, making the system deployable by a client on Windows or Linux without any local Python or Node.js tooling installed. The approach uses official Docker Hub images for the two infrastructure services (pgvector Postgres and R2R) and custom multi-stage Dockerfiles for the two application services. All four services run on a shared internal Docker bridge network; only the three user-facing ports (3000, 7272, 8000) are exposed to the host.

Persistence is split along ownership lines: R2R's vector store lives in a named Docker volume (opaque to the host, survives `docker compose down` by default) while the application's own SQLite stores, ingested documents, and extracted figures are kept in a relative bind mount so they remain directly accessible on the host filesystem. A subtle but load-bearing constraint governs the frontend: Next.js bakes `NEXT_PUBLIC_*` environment variables into the JavaScript bundle at build time rather than reading them at runtime, so each deployment target (local, VPS) requires its own `docker compose build` pass with the correct API URL. Supporting this, the design adds `.gitattributes` LF enforcement so Dockerfiles are never corrupted by Windows line endings, and a Windows-first `deployment.md` with PowerShell-compatible commands to guide the client through first-run setup, restart, and key handoff.

## Definition of Done

- `docker compose up` (single command) starts all 4 services — Postgres+pgvector, R2R, FastAPI, Next.js — on Windows Docker Desktop (WSL2) and Linux, with no `make` dependency for the client
- Data survives restarts: named Docker volume for Postgres vectors, relative bind mounts for `data/` SQLite stores, `data/figures/`, and `data/documents/` (cross-platform paths)
- `.env.example` and `.env.example.client` updated to include all required variables (`R2R_POSTGRES_*`, `GOOGLE_API_KEY`, `NEXT_PUBLIC_*`)
- `docs/client-handoff/deployment.md` written Windows-first (PowerShell-compatible commands) with Linux footnotes covering startup, env setup, restart procedure, and key-swap on handoff
- Security note explains sample-corpus safety vs real confidential client docs
- Dockerfiles enforce LF line endings to prevent Windows CRLF breakage

## Acceptance Criteria

### docker-handoff.AC1: Stack starts with a single command on Windows and Linux

- **docker-handoff.AC1.1 Success:** `docker compose up` starts all four services (postgres, r2r, api, web) in dependency order without errors
- **docker-handoff.AC1.2 Success:** All host ports are reachable after startup: R2R at 7272, API at 8000, web UI at 3000
- **docker-handoff.AC1.3 Success:** Stack starts on Windows Docker Desktop with WSL2 backend from a fresh clone
- **docker-handoff.AC1.4 Success:** Stack starts on Linux with Docker Engine
- **docker-handoff.AC1.5 Success:** No `make`, bash, or Unix shell commands are required — PowerShell `docker compose` commands are sufficient
- **docker-handoff.AC1.6 Failure:** Missing `GOOGLE_API_KEY` in `.env` causes a clear startup error, not a silent hang
- **docker-handoff.AC1.7 Failure:** Missing `r2r_gemini.toml` causes a clear error at startup, not a cryptic R2R internal panic

### docker-handoff.AC2: Data survives container restarts

- **docker-handoff.AC2.1 Success:** Vectors ingested before `docker compose down` are retrievable after `docker compose up` (named volume survives)
- **docker-handoff.AC2.2 Success:** Notebooks, conversations, and ingest job records in `data/` SQLite stores persist across restarts
- **docker-handoff.AC2.3 Success:** Extracted figures in `data/figures/` persist across restarts
- **docker-handoff.AC2.4 Success:** `docker compose down` (without `-v`) does NOT delete vector data
- **docker-handoff.AC2.5 Edge:** `docker compose down -v` is documented as the explicit wipe path; standard `down` is safe for routine restarts

### docker-handoff.AC3: Environment files are complete and client-ready

- **docker-handoff.AC3.1 Success:** `.env.example` contains all five `R2R_POSTGRES_*` vars (`HOST`, `PORT`, `USER`, `PASSWORD`, `DBNAME`)
- **docker-handoff.AC3.2 Success:** `.env.example` contains `GOOGLE_API_KEY`, `R2R_BASE_URL`, `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_DEMO_NOTEBOOK_ID`
- **docker-handoff.AC3.3 Success:** A developer following `.env.example` alone can configure the full stack without reading any other documentation
- **docker-handoff.AC3.4 Success:** `.env.example.client` includes annotated key-swap instructions for transferring `GOOGLE_API_KEY` ownership on handoff
- **docker-handoff.AC3.5 Success:** `.env.example.client` notes that `NEXT_PUBLIC_API_URL` must be updated before building when deploying to a VPS

### docker-handoff.AC4: Deployment documentation is Windows-first and self-contained

- **docker-handoff.AC4.1 Success:** `deployment.md` uses PowerShell-compatible commands throughout (no bash-only syntax in primary steps)
- **docker-handoff.AC4.2 Success:** Doc covers prerequisites, one-time setup, start, verify, stop/restart as distinct sections
- **docker-handoff.AC4.3 Success:** Doc covers VPS deployment variant (setting `NEXT_PUBLIC_API_URL` to server IP before build)
- **docker-handoff.AC4.4 Success:** Doc covers key-swap procedure for client handoff
- **docker-handoff.AC4.5 Success:** Linux-equivalent commands present as footnotes or callout for each major step
- **docker-handoff.AC4.6 Edge:** A Windows user unfamiliar with the project can follow the doc to a running app without asking for help

### docker-handoff.AC5: Security boundary is documented

- **docker-handoff.AC5.1 Success:** Security note explains the Robinhood 10-K sample corpus is safe for demonstration purposes
- **docker-handoff.AC5.2 Success:** Security note states that real confidential client documents require the client's own API key and a security review before production use

### docker-handoff.AC6: LF line endings enforced for cross-platform builds

- **docker-handoff.AC6.1 Success:** `.gitattributes` committed with `* text=auto eol=lf` rule
- **docker-handoff.AC6.2 Success:** All files under `docker/` show LF endings on a Windows clone (`git ls-files --eol`)
- **docker-handoff.AC6.3 Success:** `docker compose build` completes without CRLF-related errors on a fresh Windows clone
- **docker-handoff.AC6.4 Edge:** `.bat`/`.cmd` files (if any) correctly retain CRLF via the `*.bat text eol=crlf` override rule

## Glossary

- **R2R**: Open-source RAG engine by SciPhi AI. Handles document ingestion, vector search, and LLM-grounded answer generation. Runs as a Docker service using the official `sciphiai/r2r` image.
- **pgvector**: A Postgres extension that adds a vector column type and approximate-nearest-neighbor search. R2R uses it as its vector store; `pgvector/pgvector:pg16` is a Postgres 16 image with the extension pre-installed.
- **RAG (Retrieval-Augmented Generation)**: A pattern where relevant document chunks are retrieved from a vector store and injected into an LLM prompt so the model answers from provided context rather than training data alone.
- **FCIS (Functional Core / Imperative Shell)**: Module-boundary pattern used throughout the FastAPI codebase. Pure functions in the Functional Core are unit-tested directly; I/O orchestration in the Imperative Shell is tested with mocks. Unaffected by containerisation.
- **`r2r_gemini.toml`**: Project-local R2R configuration file routing all R2R LLM slots to Google Gemini via litellm. Must be present and bind-mounted into the R2R container; its absence causes a startup panic.
- **Named volume**: A Docker-managed persistent storage volume identified by a name (`r2r_pg_data`). Survives `docker compose down` but not `docker compose down -v`. Host cannot browse its contents directly.
- **Bind mount**: A direct mapping of a host filesystem path into a container (`./data:/app/data`). Host and container share the files; changes are immediately visible in both directions.
- **Multi-stage build**: A Dockerfile technique using multiple `FROM` stages. Builder stages install compilers and heavyweight tools; the runtime stage copies only compiled artefacts, producing a smaller image.
- **`output: "standalone"`**: A Next.js build mode producing a self-contained `server.js` entry point. Required for Docker deployment because the default output assumes `node_modules` is present at runtime.
- **`NEXT_PUBLIC_*` vars**: Next.js environment variables baked into the JavaScript bundle at `next build` time, not at runtime. Changing the API URL requires a rebuild, not just a container restart.
- **`ipc: host`**: Docker Compose service setting sharing the host IPC namespace with the container. Required by Playwright/Chromium which uses shared memory for inter-process coordination.
- **WSL2 (Windows Subsystem for Linux 2)**: The Linux kernel layer that Docker Desktop on Windows uses as its container runtime backend.
- **Playwright**: Browser automation library used by the FastAPI service for URL ingestion. Requires the Chromium binary and system dependencies in the container.
- **Tesseract**: Open-source OCR engine installed as a system package in the API container. Used during PDF ingestion to extract text from scanned or image-heavy pages.
- **Docling**: Document parsing library (IBM) that converts DOCX and PPTX files into structured page dicts for the ingestion pipeline.
- **uv**: Fast Python package installer and virtual environment manager (Astral, written in Rust). Used in the API Dockerfile builder stage.
- **uvicorn**: ASGI server hosting the FastAPI application. Container entrypoint: `uvicorn apps.api.main:app --host 0.0.0.0 --port 8000`.
- **PaaS (Platform as a Service)**: Cloud hosting products (Railway, Render, Fly.io) managing underlying infrastructure. Mentioned as a deferred alternative deployment path for Phase 9.
- **AGPL-3.0**: GNU Affero General Public License v3. PyMuPDF is AGPL-3.0 — derivative software distributed to users must also be open-sourced, or a commercial license purchased.
- **PyMuPDF**: Python binding for MuPDF used for PDF rendering and raster figure extraction. AGPL-3.0 license is carried into the Docker image.
- **`pg_isready`**: Postgres utility reporting whether the database server accepts connections. Used as the Docker health check for the postgres service.
- **Robinhood 10-K sample corpus**: Publicly available annual report filing used as the demo dataset — safe for demonstration without additional data-handling agreements.

## Architecture

Four services coordinated by a single `docker-compose.yml` at the project root. All services share an internal Docker bridge network (`qdocent`). Only three ports are exposed to the host.

```
┌─────────────────── network: qdocent ──────────────────────┐
│                                                             │
│  postgres  (pgvector/pgvector:pg16)                        │
│    volume: r2r_pg_data → /var/lib/postgresql/data          │
│    internal port: 5432                                      │
│                                                             │
│  r2r  (sciphiai/r2r:3.6.6)                                 │
│    bind mount: ./r2r_gemini.toml → /app/r2r_gemini.toml:ro │
│    env: GOOGLE_API_KEY, R2R_POSTGRES_HOST=postgres         │
│    host port: 7272                                          │
│    depends_on: postgres (healthy)                           │
│                                                             │
│  api  (docker/api/Dockerfile, Python 3.11)                 │
│    bind mount: ./data → /app/data                          │
│    env: R2R_BASE_URL=http://r2r:7272, GOOGLE_API_KEY       │
│    host port: 8000   ipc: host (Playwright requirement)    │
│    depends_on: r2r                                          │
│                                                             │
│  web  (docker/web/Dockerfile, Node 20)                     │
│    build args: NEXT_PUBLIC_API_URL, NEXT_PUBLIC_DEMO_*     │
│    host port: 3000                                          │
│    depends_on: api                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Key wiring decisions:**

- `api` reaches R2R via Docker DNS (`http://r2r:7272`), not `localhost`
- `NEXT_PUBLIC_API_URL` defaults to `http://localhost:8000` — the host-facing URL, because browser JS calls it from the client machine, not from inside the Docker network
- Postgres is not exposed to the host by default; remove the `ports:` entry from the postgres service after initial validation
- `ipc: host` on the api service is required for Playwright/Chromium shared memory

**Persistence:**

| Data | Mechanism | Survives restart |
|---|---|---|
| R2R vectors (pgvector) | Named volume `r2r_pg_data` | Yes |
| SQLite stores (`ingest_jobs.db`, `notebooks.db`, `wiki.db`, `conversations.db`) | Relative bind mount `./data:/app/data` | Yes |
| Ingested documents (`data/documents/`) | Same bind mount | Yes |
| Extracted figures (`data/figures/`) | Same bind mount | Yes |

**`NEXT_PUBLIC_*` handling:**

Build args in `docker-compose.yml` → `ARG`/`ENV` in `docker/web/Dockerfile` → baked into the bundle by `next build`. One `docker compose build` required per environment. Requires `output: "standalone"` in `apps/web/next.config.ts`.

## Existing Patterns

No Docker infrastructure existed before this design. The `docker/` directory is a committed placeholder (`.gitkeep` only).

The `apps/api/` FCIS pattern (Functional Core / Imperative Shell) is not affected by containerisation — the Dockerfile wraps the existing `uvicorn apps.api.main:app` entry point unchanged.

The `apps/web/` Next.js app already uses `npm run build` + `npm start`; the Dockerfile formalises this into a multi-stage build with `output: "standalone"`.

The `.env` / `.env.example` convention is already established. This design extends it by adding the missing `R2R_POSTGRES_*` vars and introducing `.env.example.client` as a client-facing variant with handoff annotations.

## Implementation Phases

<!-- START_PHASE_1 -->
### Phase 1: Postgres + R2R Services

**Goal:** Verify the two external-image services start correctly with the project's Gemini config and persist vector data across restarts.

**Components:**
- `docker-compose.yml` — skeleton with `postgres` and `r2r` services only; named volume `r2r_pg_data`; health check on postgres (`pg_isready`); `r2r` depends on postgres healthy
- `docker/` directory — already exists as placeholder; no new subdirectories needed for this phase

**Dependencies:** None (first phase)

**Done when:** `docker compose up postgres r2r` starts both services; R2R logs show successful Postgres connection; `docker compose down && docker compose up` retains previously ingested vectors
<!-- END_PHASE_1 -->

<!-- START_PHASE_2 -->
### Phase 2: Environment File Fixes

**Goal:** Ensure any fresh clone has all required variables documented and a client-ready `.env` template exists.

**Components:**
- `.env.example` — add `R2R_POSTGRES_HOST`, `R2R_POSTGRES_PORT`, `R2R_POSTGRES_USER`, `R2R_POSTGRES_PASSWORD`, `R2R_POSTGRES_DBNAME` (currently missing); update `R2R_BASE_URL` default to `http://r2r:7272` for Docker context with a comment noting `http://localhost:7272` for local dev
- `.env.example.client` — client-facing copy with annotated instructions: which vars to change, key-swap note (client replaces `GOOGLE_API_KEY` on handoff), `NEXT_PUBLIC_API_URL` note (change to server IP if deploying to VPS)

**Dependencies:** Phase 1 (confirms which vars R2R actually reads)

**Done when:** A developer following only `.env.example` can configure R2R Postgres connection without external documentation; `.env.example.client` is self-contained for a non-developer buyer
<!-- END_PHASE_2 -->

<!-- START_PHASE_3 -->
### Phase 3: FastAPI Dockerfile

**Goal:** Containerise the FastAPI wrapper with all heavy ingestion dependencies.

**Components:**
- `docker/api/Dockerfile` — multi-stage (`builder` + `runtime`), base `python:3.11-slim-bookworm`; builder installs uv, system packages (`tesseract-ocr`, `tesseract-ocr-eng`, `libcairo2-dev`, `poppler-utils`, `ghostscript`, `libglib2.0-0`, Playwright system deps), PyTorch CPU-only index, `requirements.txt` deps, `playwright install chromium --with-deps`; runtime stage copies site-packages, Playwright Chromium binaries, and app source; `CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]`
- `docker-compose.yml` api service — `build: { context: ., dockerfile: docker/api/Dockerfile }`, `ipc: host`, `./data:/app/data` bind mount, env vars

**Dependencies:** Phase 1 (compose file exists), Phase 2 (env vars defined)

**Done when:** `docker compose build api` succeeds; `docker compose up api` starts without import errors; `POST /ingest` with a PDF processes through the full pipeline (tesseract, docling, Playwright URL ingest); `./data` bind mount persists SQLite stores across restarts
<!-- END_PHASE_3 -->

<!-- START_PHASE_4 -->
### Phase 4: Next.js Dockerfile

**Goal:** Containerise the Next.js frontend with baked-in `NEXT_PUBLIC_*` vars.

**Components:**
- `apps/web/next.config.ts` — add `output: "standalone"` (required for Docker standalone server)
- `docker/web/Dockerfile` — three-stage (`deps` → `builder` → `runner`), base `node:20-alpine`; deps stage runs `npm ci --omit=dev`; builder stage accepts `ARG NEXT_PUBLIC_API_URL` and `ARG NEXT_PUBLIC_DEMO_NOTEBOOK_ID`, sets as `ENV`, runs `npm run build`; runner stage copies `.next/standalone`, `.next/static`, `public`; `CMD ["node", "server.js"]`
- `docker-compose.yml` web service — `build: { args: { NEXT_PUBLIC_API_URL, NEXT_PUBLIC_DEMO_NOTEBOOK_ID } }`, port `3000:3000`, `depends_on: api`

**Dependencies:** Phase 3 (compose file has api service to depend on)

**Done when:** `docker compose build web` succeeds; `http://localhost:3000` loads the notebooks page; browser network tab shows API calls going to the configured `NEXT_PUBLIC_API_URL`
<!-- END_PHASE_4 -->

<!-- START_PHASE_5 -->
### Phase 5: Full Compose Integration + Smoke Test

**Goal:** All four services start together and the end-to-end RAG flow works.

**Components:**
- `docker-compose.yml` — final wiring: all four services, health checks, correct `depends_on` chain, postgres port removed from host exposure
- Smoke test: `docker compose up -d`, upload a PDF via the UI, ask a question, verify a cited answer is returned

**Dependencies:** Phases 1–4

**Done when:** `docker compose up` from a clean state (no prior volumes) starts all services without error; full RAG flow (ingest → ask → cited answer) completes via browser at `http://localhost:3000`; `docker compose down && docker compose up` retains notebooks and ingested documents
<!-- END_PHASE_5 -->

<!-- START_PHASE_6 -->
### Phase 6: CRLF Guard

**Goal:** Prevent Windows line-ending corruption in Dockerfiles and shell-adjacent files for any contributor.

**Components:**
- `.gitattributes` — `* text=auto eol=lf` with `*.bat text eol=crlf` and `*.cmd text eol=crlf` overrides; committed to repo so all contributors and clones are covered

**Dependencies:** Phase 5 (all files exist before enforcing endings)

**Done when:** `.gitattributes` committed; `git ls-files --eol docker/` shows `lf` for all Dockerfiles on a Windows clone; `docker compose build` succeeds on a fresh Windows clone without CRLF-related shebang errors
<!-- END_PHASE_6 -->

<!-- START_PHASE_7 -->
### Phase 7: Deployment Documentation

**Goal:** A Windows-first client can start the app from docs alone, and the handoff key-swap procedure is clear.

**Components:**
- `docs/client-handoff/deployment.md` — Windows-first (PowerShell commands throughout); sections: prerequisites (Docker Desktop with WSL2, Git), one-time setup (clone, copy config files, set `GOOGLE_API_KEY`), start (`docker compose build && docker compose up`), verify (`http://localhost:3000`), stop/restart, VPS deployment variant (set `NEXT_PUBLIC_API_URL` to server IP before build), key-swap on handoff (client sets their own `GOOGLE_API_KEY`), security note (sample corpus safety vs real confidential docs), Linux footnotes

**Dependencies:** Phase 5 (confirmed working flow to document)

**Done when:** A technically literate Windows user with no prior project knowledge can follow the doc to a running app; doc covers all failure modes discovered during Phase 5 smoke testing
<!-- END_PHASE_7 -->

## Additional Considerations

**PyMuPDF AGPL license:** `requirements.txt` flags PyMuPDF as AGPL-3.0, requiring a commercial license for closed-source deployment. This is inherited by the Docker image. Note this in `deployment.md` and `.env.example.client` for client awareness before production use.

**PaaS non-Docker path (deferred to Phase 9):** Railway ($15–25/mo, official R2R template), Render ($21–40/mo), and Fly.io ($40–80/mo) all support pgvector. Free tiers are insufficient — the full stack needs ~1.5–3 GB RAM minimum. These are viable alternatives for managed single-tenant deployment but are out of scope here.

**R2R image Python version mismatch:** The official `sciphiai/r2r:3.6.6` image uses Python 3.12; the project uses Python 3.11. This affects only the R2R service container, which is not the custom application code. If R2R SDK behaviour differences surface between 3.11 and 3.12, pin to a custom R2R Dockerfile as a fallback.

**VPS deployment note:** When deploying to a remote server, `NEXT_PUBLIC_API_URL` must be set to the server's public IP or domain before `docker compose build`. The compose `build.args` default of `http://localhost:8000` only works for local same-machine access.
