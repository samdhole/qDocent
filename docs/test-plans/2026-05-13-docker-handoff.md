# Human Test Plan: Docker Handoff
**Implementation plan:** `docs/implementation-plans/2026-05-13-docker-handoff/`
**Generated:** 2026-05-14

## Prerequisites
- Windows 11 host with Docker Desktop (WSL2 backend) ≥ 24.0.0, plus a Linux host with Docker Engine ≥ 24.0 for AC1.4
- Fresh `git clone` of master at HEAD `10a2597`
- A valid `GOOGLE_API_KEY`
- `r2r_gemini.toml` created from `r2r_gemini.toml.example` with a real `default_admin_password`
- A small test PDF on disk (e.g. one of `data/sample_docs/*.pdf` generated via `python scripts/create_sample_docs.py`, or the Robinhood 10-K)
- PowerShell 5.1 or PowerShell 7 (`pwsh.exe`) — **no `make`, no bash, no WSL shell**

---

## Phase 1: Environment File Sanity (AC3)

| Step | Action | Expected |
|------|--------|----------|
| 1.1 | Open `.env.example` in an editor | All five `R2R_POSTGRES_HOST`, `R2R_POSTGRES_PORT`, `R2R_POSTGRES_USER`, `R2R_POSTGRES_PASSWORD`, `R2R_POSTGRES_DBNAME` keys are present as uncommented `KEY=` lines (AC3.1) |
| 1.2 | Same file | `GOOGLE_API_KEY=`, `R2R_BASE_URL=`, `NEXT_PUBLIC_API_URL=`, `NEXT_PUBLIC_DEMO_NOTEBOOK_ID=` all present as uncommented `KEY=` lines (AC3.2) |
| 1.3 | Open `.env.example.client` | A clearly delimited block annotates `GOOGLE_API_KEY` with key-swap instructions (AC3.4) |
| 1.4 | Same file | A block referencing `NEXT_PUBLIC_API_URL` notes the rebuild requirement and "set to server IP" for VPS (AC3.5) |
| 1.5 | Have a reviewer who has not seen the design plan copy `.env.example` → `.env`, fill only values the comments instruct them to fill, then `docker compose up -d` | Stack reaches healthy state with no extra guidance (AC3.3) |

---

## Phase 2: Line Endings (AC6)

| Step | Action | Expected |
|------|--------|----------|
| 2.1 | Open `.gitattributes` at repo root | Contains the literal line `* text=auto eol=lf` (AC6.1) |
| 2.2 | Same file | Contains both `*.bat text eol=crlf` and `*.cmd text eol=crlf` (AC6.4) |
| 2.3 | From a **fresh Windows clone**, run `git ls-files --eol docker/` | Every line's index attribute column (`i/`) reads `lf` (AC6.2) |
| 2.4 | From the same Windows clone, run `docker compose build` | Build completes with no `\r` shebang errors, no `/usr/bin/env: 'python\r'` failures (AC6.3) |

---

## Phase 3: Stack Startup — Windows (AC1)

| Step | Action | Expected |
|------|--------|----------|
| 3.1 | From the Windows clone, in `pwsh.exe`: `docker compose up -d` | Command returns; no `make` / `bash` / `sh` invoked anywhere (AC1.5) |
| 3.2 | `docker compose ps` | All four services (postgres, r2r, api, web) show `Up (healthy)` or `Up` in dependency order (AC1.1, AC1.3) |
| 3.3 | `Invoke-WebRequest http://localhost:7272/v3/health` | HTTP 2xx (AC1.2) |
| 3.4 | `Invoke-WebRequest http://localhost:8000/health` | HTTP 2xx (AC1.2) |
| 3.5 | `Invoke-WebRequest http://localhost:3000` | HTTP 2xx (AC1.2) |
| 3.6 | Edit `.env` to remove `GOOGLE_API_KEY`, then `docker compose up r2r` | R2R logs print an explicit error referencing the missing `GOOGLE_API_KEY` within 30s (no silent hang) (AC1.6) |
| 3.7 | Restore `GOOGLE_API_KEY`. Rename `r2r_gemini.toml` → `r2r_gemini.toml.bak`, then `docker compose up r2r` | Bind-mount or config-load error names the missing `r2r_gemini.toml` within 30s. Restore the file. (AC1.7) |

---

## Phase 4: Stack Startup — Linux (AC1.4)

| Step | Action | Expected |
|------|--------|----------|
| 4.1 | On a Linux host with Docker Engine ≥ 24.0: repeat Phase 3 Steps 3.1–3.5 | Identical pass result (AC1.4) |

---

## Phase 5: Persistence (AC2)

| Step | Action | Expected |
|------|--------|----------|
| 5.1 | With the stack up, ingest a test PDF via the UI at `http://localhost:3000` | Document appears in notebook; figures land under `./data/figures/<doc_id>/*.png` on the host |
| 5.2 | Confirm `./data/figures/<doc_id>/*.png` exists on the host filesystem | PNG files present |
| 5.3 | Create a notebook via the UI | Notebook listed |
| 5.4 | `docker compose down` (no `-v`) | Stack stops |
| 5.5 | `docker volume ls` | `qdocent_r2r_pg_data` still listed (AC2.4) |
| 5.6 | `docker compose up -d`, then refresh `http://localhost:3000` | Prior notebook still listed (AC2.2); `r2r documents list` shows prior document (AC2.1) |
| 5.7 | Confirm `./data/figures/<doc_id>/*.png` still present after restart; re-ask a question that referenced the figure | Figure resurfaces in the answer (AC2.3) |
| 5.8 | Note `./data/notebooks.db` mtime between restarts to confirm it is the same file, not a recreated one | mtime predates the restart (AC2.2) |

---

## Phase 6: Deployment Documentation Review (AC4, AC5, AC2.5)

| Step | Action | Expected |
|------|--------|----------|
| 6.1 | Open `docs/client-handoff/deployment.md` | Contains named sections: Prerequisites, One-Time Setup, Starting the Application, Verifying, Stopping/Restarting, Troubleshooting (AC4.2) |
| 6.2 | Scan all primary steps | No bash-only constructs: no `$()` substitution, no single-quoted heredocs, no unguarded `&&`, no `export FOO=bar` (AC4.1) |
| 6.3 | Spot-check at least three primary PowerShell steps | Each has an adjacent Linux-equivalent footnote/callout (AC4.5) |
| 6.4 | Find the "VPS / Remote Server Deployment" section | Section present; includes setting `NEXT_PUBLIC_API_URL` to server IP and rebuilding the web image (AC4.3) |
| 6.5 | Find the "Key Handoff" section | Both "new owner does" and "previous owner does" sub-sections present, with order clarification (AC4.4) |
| 6.6 | Find the "Complete Data Wipe" section | `docker compose down -v` named, flagged destructive, distinguished from routine `down` (AC2.5) |
| 6.7 | Find the "Security Note" section | Sub-section names the Robinhood 10-K and states it is publicly filed / safe for demo (AC5.1) |
| 6.8 | Same section | "Using with real confidential documents" sub-section requires client-owned `GOOGLE_API_KEY` + explicit security review before production (AC5.2) |
| 6.9 | Recruit a Windows reviewer unfamiliar with the project; they follow `deployment.md` only (no Slack, no other repo files) to `http://localhost:3000` | They reach a working notebook with zero clarifying questions (AC4.6) |

---

## End-to-End: Fresh Windows Clone → Running Demo

**Purpose:** Validates AC1.3 + AC1.5 + AC3.3 + AC4.6 + AC6.2 + AC6.3 jointly — the headline handoff promise.

Steps:
1. On a Windows 11 host with Docker Desktop running, in a clean directory: `git clone <repo-url>` then `cd` into it.
2. Following **only** `docs/client-handoff/deployment.md`, in `pwsh.exe`:
   - Copy `.env.example` → `.env`, fill `GOOGLE_API_KEY`.
   - Copy `r2r_gemini.toml.example` → `r2r_gemini.toml`, set `default_admin_password`.
   - Pre-create data dir: `wsl mkdir -p data && wsl sudo chown -R 1001:1001 data`
   - `docker compose build` (must complete with no CRLF errors).
   - `docker compose up -d`.
3. Browse to `http://localhost:3000`, create a notebook, ingest a small PDF, ask a question.
4. Expected: cited answer rendered in the UI; no `make`, no bash, no manual file edits beyond the two env files; reviewer did not need to read any other repo file.

## End-to-End: Restart Survives Data

**Purpose:** Validates AC2.1 + AC2.2 + AC2.3 + AC2.4 jointly.

Steps:
1. After the End-to-End above, note the document ID and one figure filename under `./data/figures/`.
2. `docker compose down` (no `-v`).
3. `docker volume ls` shows `qdocent_r2r_pg_data` still present.
4. `docker compose up -d`; UI lists the prior notebook; prior document still queryable; same figure file still on disk and still surfaces in a re-asked question.

---

## Traceability

| Acceptance Criterion | Automated Test | Manual Step |
|----------------------|----------------|-------------|
| AC1.1 | — | 3.2 |
| AC1.2 | — | 3.3, 3.4, 3.5 |
| AC1.3 | — | 3.1–3.5 (Windows) |
| AC1.4 | — | 4.1 (Linux) |
| AC1.5 | — | 3.1 |
| AC1.6 | — | 3.6 |
| AC1.7 | — | 3.7 |
| AC2.1 | — | 5.6 |
| AC2.2 | — | 5.3, 5.6, 5.8 |
| AC2.3 | — | 5.2, 5.7 |
| AC2.4 | — | 5.5 |
| AC2.5 | — | 6.6 |
| AC3.1 | — (optional pre-flight guard not added) | 1.1 |
| AC3.2 | — (optional pre-flight guard not added) | 1.2 |
| AC3.3 | — | 1.5 |
| AC3.4 | — | 1.3 |
| AC3.5 | — | 1.4 |
| AC4.1 | — | 6.2 |
| AC4.2 | — | 6.1 |
| AC4.3 | — | 6.4 |
| AC4.4 | — | 6.5 |
| AC4.5 | — | 6.3 |
| AC4.6 | — | 6.9 |
| AC5.1 | — | 6.7 |
| AC5.2 | — | 6.8 |
| AC6.1 | — (optional pre-flight guard not added) | 2.1 |
| AC6.2 | — | 2.3 |
| AC6.3 | — | 2.4 |
| AC6.4 | — (optional pre-flight guard not added) | 2.2 |
