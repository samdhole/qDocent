# API Key and Deployment Notes

Everything you need to run the system locally. One API key required.

---

## Required: Google API Key

**Only one external API key is needed: a Google Gemini API key.**

The system uses Google Gemini for all LLM operations — document Q&A, wiki generation, and evaluation. The same key covers everything.

### How to get one (free tier is sufficient for demo)

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Sign in with a Google account
3. Click "Get API key" → "Create API key"
4. Copy the key (starts with `AIza...`)

The free tier allows enough requests for local demo and evaluation runs. No billing required for this demo.

---

## Environment Setup

```bash
# 1. Copy the example env file
cp .env.example .env

# 2. Open .env and set your key
GOOGLE_API_KEY=AIza...your-key-here...

# Leave all other values as-is for local demo
```

**Never commit `.env` to git.** It is gitignored. The `.env.example` file shows what variables exist with empty values — that is safe to commit.

---

## Frontend Environment Variables

The Next.js frontend uses two `NEXT_PUBLIC_` variables baked in at build time:

| Variable | Default | Purpose |
|----------|---------|---------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Points the frontend to the FastAPI backend |
| `NEXT_PUBLIC_DEMO_NOTEBOOK_ID` | *(empty)* | When set, the `/demo` page's "Try It Live" section uses this notebook |

To set these for local dev, create `apps/web/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_DEMO_NOTEBOOK_ID=  # fill in after running make demo-setup
```

**Important:** After changing any `NEXT_PUBLIC_*` variable, restart `make web`. These are baked into the Next.js bundle at build time — a running dev server must be restarted to pick them up.

---

## R2R Configuration

R2R (the retrieval server) needs its own config file pointing all LLM slots at Gemini:

```bash
# Copy the example config
cp r2r_gemini.toml.example r2r_gemini.toml

# Edit r2r_gemini.toml:
# Set default_admin_password to something non-default before first run
```

`r2r_gemini.toml` is gitignored (never committed — it contains your admin password).

---

## Start Sequence

Three terminal windows, in this order:

```bash
# Terminal 1: Retrieval server (R2R)
make r2r
# Wait for: "Uvicorn running on http://0.0.0.0:7272"
# Takes ~20-30 seconds

# Terminal 2: API server (FastAPI)
make api
# Wait for: "Application startup complete."
# Takes ~10-15 seconds

# Terminal 3: Web UI (Next.js)
make web
# Wait for: "Ready on http://localhost:3000"
# Takes ~5-10 seconds
```

---

## Verify Everything Works

```bash
# Checks API health, stored documents, citations, workflow, and latest eval artifact
python scripts/demo_readiness.py
```

Expected output:
```
[PASS] API health check
[PASS] Source documents stored
[PASS] Citations returned by /ask
[PASS] Workflow endpoint responds
[PASS] Eval artifact present (reports/evals/)

READY
```

If any check fails, the script prints the specific error. Common issues:

| Error | Fix |
|-------|-----|
| API health check fails | R2R not running; start `make r2r` first |
| No source documents | Run `make ingest` or upload via `/documents` |
| No eval artifact | Run `make eval` to generate a RAGAS report |

---

## Demo Corpus Setup (Robinhood 10-K)

To populate the `/demo` page with real Robinhood financial data:

```bash
make demo-setup
```

This downloads the Robinhood 2023 Annual Report from SEC EDGAR, ingests it, generates a 6-page wiki, captures a Q&A snapshot, and extracts a figure. Takes 2-10 minutes. Idempotent — safe to run again.

After completion, set `NEXT_PUBLIC_DEMO_NOTEBOOK_ID` to the printed `DEMO_NOTEBOOK_ID` value in `apps/web/.env.local` and restart `make web`.

---

## Phase 2 Note: Docker

Phase 1 requires three terminal windows. Phase 2 of the productization roadmap adds a `docker compose up` path that starts all services from a single command and includes persistent data volumes, `.env.example.client`, and a deployment guide. Local three-terminal setup is the supported path until then.
