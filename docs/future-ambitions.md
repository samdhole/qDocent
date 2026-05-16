# Future Ambitions

Last reviewed: 2026-05-15

This file separates actual code/product features from product packaging and sales
assets. qDocent already has the core proof for document RAG: notebooks,
multi-format ingestion, streaming chat, source inspection, citations, figures,
wiki generation with inter-page links and source citation badges, and eval infrastructure.

## Already in the product

- Notebook-scoped retrieval through R2R collections.
- PDF, DOCX, PPTX, and URL ingestion (one file at a time).
- Streaming conversations with native R2R multi-turn (`conversation_id`).
- Wiki generation: parallel page generation, Mermaid diagrams, inter-page cross-links, source doc citation badges linking to PDF viewer.
- Anti-hallucination: collection-scoped retrieval fallback when doc-scoped returns empty; explicit no-invention grounding rule in page prompts.
- Source inspection: citations with bbox highlighting, chunks manifest, figures, quality reports.
- Suggested questions cache — generated at ingest, served instantly on hit.
- `/demo` showcase page with real Robinhood 10-K snapshots (wiki, cited Q&A, figure, live fallback).
- Search baseline with hybrid retrieval, RRF, `limit: 15`, and chunk enrichment.
- Full-stack Docker compose with healthcheck chain; Windows + Linux installer/launcher scripts.
- R2R auth enabled in example config. This is not full app-level auth.
- ~614 automated tests (~50 test files).

## Code / Product Features Left

These require code, infrastructure, UI, tests, or deployment work.

### Buyer-Relevant Code Features

#### Real Auth, Organisations, Roles, And Notebook Permissions

**Relevance:** High for jobs mentioning secure internal docs, RBAC,
document-level permissions, admin/user roles, or company knowledge platforms.

**Missing:** Server-side users, organisations/workspaces, roles, notebook ACLs,
API keys, and route-level authorization checks.

#### External Connectors

**Relevance:** High when buyers name SharePoint, Notion, Google Drive, Zendesk,
Intercom, HubSpot, Salesforce, Freshdesk, webpages, ticket history, or knowledge
base sync.

**Missing:** OAuth/API-key setup, scheduled sync, dedupe/update logic, connector
health, and source-to-notebook mapping.

#### Admin Dashboard For Document Operations

**Relevance:** Medium-high for buyers who want a usable internal tool rather
than only an API or demo.

**Missing:** Buyer-grade notebook/document management, ingest job history with
errors, source status, user/permission management, and API-key management.

#### Usage Analytics And Eval Reporting

**Relevance:** Medium-high for jobs about hallucination reduction, unanswered
questions, RAG quality, monitoring, or proving the chatbot improved.

**Missing:** Event log, citation-click tracking, low-confidence/not-found
tracking, unanswered-question report, document-gap report, and an evaluation
dashboard/export.

#### Embeddable Website Chatbot

**Relevance:** Medium. Strong only for buyers asking to put a chatbot on a
website or client portal.

**Missing:** Hosted JS snippet, widget configuration, cross-origin deployment,
and read-only notebook-scoped auth/API key.

#### Hosted Deployment / Production Deployment

**Relevance:** Medium-high for jobs that say production-ready, deploy to AWS,
Docker, SaaS backend, or ready for users.

**Missing:** Verified deployment path, secrets, TLS/domain, backups, monitoring,
tenant isolation, billing if SaaS, and operational runbook.

### Buyer-Triggered Integrations

Build only when a job pulls them:

- SSO with Google Workspace or Microsoft Entra.
- Slack or Microsoft Teams bot.
- Zendesk or Intercom app/sidebar.

#### Folder / Library Bulk Ingestion

**Relevance:** High for buyers with Zotero libraries, Calibre collections, disorganised downloads folders, or any corpus larger than a handful of files.

**Approach:** Browser `webkitdirectory` folder picker — the browser walks the directory tree and sends files as individual uploads. No zip, no server-side filesystem access. Client-side extension filter (`_ALLOWED_EXTENSIONS`). Batched uploads (4 concurrent) to the existing single-file endpoint. Aggregate progress UI: `12 / 47 ingested · 3 failed`. Deduplication by `source_file` basename against existing notebook documents. Zero new pipeline code — every file goes through the existing `run_pipeline()` / `run_pipeline_for_source()` path.

**Missing:** Folder picker UI component, batch job state manager in the frontend, aggregate progress bar, per-file error list, dedup check on upload.

### Low-Priority Or Speculative Code Features

These are real software features, but they do not help first-pass Upwork sales
unless a buyer asks for them:

- YouTube/audio ingestion.
- Mind map view.
- GraphRAG entity graph.

## Product Packaging / Sales Assets Left

These are not product features. They make qDocent legible, sellable, and
deliverable.

### Flagship Proof / Demo Page ✅ COMPLETE (2026-05-13)

`/demo` page ships with real Robinhood 10-K snapshots: wiki panel, cited Q&A
with 15 inline citation badges, extracted figure, and a live chat box that
falls back to a cached example when the API is offline. `make demo-setup`
populates it idempotently. Client handoff package in `docs/client-handoff/`.
Demo script: `docs/client-handoff/sample-rag-demo/demo-script.md`.

### Upwork Delivery / Handoff Model

Each funded milestone should produce a visible artifact the client can review:
demo URL, PR, Docker package, eval report, deployment doc, or walkthrough video.

**Prototype milestone:** client sends sample docs and questions; deliver browser
demo or recording, cited answers for 10-20 questions, and reliability notes.

**Build milestone:** deliver app/API/PR configured for the client's corpus,
including source inspection and eval/smoke questions.

**Deployment milestone:** deliver deployed app URL, Dockerized package, or repo
handoff with `.env.example`, key setup, restart/update docs, known limits, and a
walkthrough video.

**API-key rule:** prototypes may use a temporary limited dev key if agreed;
ongoing client use should use the client's own Gemini/OpenAI/R2R/cloud/vector DB
keys. Never leave personal keys in a client repo or deployment.

### Proposal Angles For Real Upwork Job Types

- "Build a RAG chatbot over your company docs."
- "Fix your chatbot because it gives wrong answers."
- "Add document Q&A to your SaaS or internal tool."
- "Improve retrieval for large PDFs with citations and source inspection."
- "Set up evals so you know the bot is not making things up."

### Acceptance Criteria Templates

- Answers cite the provided documents.
- Out-of-scope questions get a refusal/not-found response.
- Representative questions pass a fixed eval set.
- Returned citations open the right source/page/context.
- Latency and corpus-size assumptions are stated.

### Existing Chatbot Repair Checklist

- Chunking and document parsing.
- Retrieval ranking and filters.
- Citation fidelity.
- Refusal behavior.
- Eval set quality.
- UI/source inspection gaps.

### Onboarding / Document Import Service

Service workflow, not code by default: audit source folders, clean file
structure, ingest corpus, verify citations, and hand off a populated notebook.

### Maintenance / Managed Service Package

Operating agreement, not code by default: model/version updates, re-ingestion,
monitoring, support contact, and periodic eval review.
