# qDocent Upwork Productization Roadmap

Last updated: 2026-05-14

This roadmap turns qDocent from a strong local RAG demo into something that can
be sold, delivered, and maintained through Upwork-style milestone work.

## Roadmap Principles

- qDocent is proof and a starter kit; the buyer buys a solved problem.
- Do not sell a platform first. Sell a working document Q&A prototype, repair, or
  integration.
- Every milestone must produce a reviewable artifact: demo URL, PR, Docker
  package, eval report, deployment doc, or walkthrough video.
- Normal buyers should not run three terminals. Terminal commands are acceptable
  only for developer handoff.
- Build generic platform features only after the demo and delivery story are
  credible.
- After analytics, integrations should be buyer-pulled, not speculative.

## Phase 1: Client-Demo Handoff Package ✅ COMPLETE (2026-05-13)

**Target time:** 1-2 days

**Goal:** Make qDocent understandable and approvable as a first Upwork milestone.

**Build:**

- A realistic demo corpus with PDF-heavy business or technical documents.
- 10-20 representative test questions.
- A first-milestone delivery folder under `docs/client-handoff/sample-rag-demo/`.
- `README_CLIENT.md` explaining what the client receives and how to use it.
- `test-questions.md` with expected behaviors.
- `delivery-report.md` with cited-answer results and failure notes.
- `known-limits.md` describing security/data limits.
- `api-key-and-deployment-notes.md`.
- A 60-90 second demo script.
- One reusable Upwork proposal template for "build/fix a RAG chatbot over
  PDFs/internal documents."

**Done when:** a buyer can understand the demo without reading the repo, and the
demo shows ask, cited answer, source inspection, refusal/not-found behavior, and
eval/reliability evidence.

**Delivered:** `docs/client-handoff/sample-rag-demo/` (README, test-questions, delivery-report, known-limits, api-key-and-deployment-notes, demo-script) + `docs/client-handoff/upwork-proposal-template.md`. Real Robinhood 10-K snapshots committed to `/demo` page.

## Phase 2: Docker / Deployment Handoff ✅ COMPLETE (2026-05-14)

**Target time:** 3-7 days

**Goal:** Make qDocent deliverable without requiring three terminal sessions.

**Build:**

- A client handoff path based on one documented startup command, ideally
  `docker compose up`.
- Compose services for R2R, FastAPI, web UI, and persistent data volumes.
- `.env.example.client`.
- Client-safe R2R config example if needed.
- `docs/client-handoff/deployment.md`.
- A security boundary note explaining sample-doc safety versus real confidential
  client docs.
- A simple hosted-demo option or explicit interim "demo is hosted by us during
  review" path.

**Done when:** a technical client can start the app from docs, and a
non-technical client can test via browser if you host/deploy it.

**Delivered:** `docker-compose.yml` (4-service stack: postgres → r2r → api → web with healthcheck chain), `docker/api/Dockerfile` (two-stage FastAPI with Playwright/docling/tesseract, non-root appuser), `docker/web/Dockerfile` (three-stage Next.js standalone, non-root nextjs user), `.env.example.client`, `.gitattributes` (LF enforcement), `.dockerignore`, `apps/web/next.config.ts` (`output: "standalone"`), `docs/client-handoff/deployment.md` (Windows-first guide with VPS, key-handoff, and security sections). Human test plan: `docs/test-plans/2026-05-13-docker-handoff.md`. Operational smoke tests (AC1–AC2, AC6.3) require live Docker run on Windows + Linux.

## Phase 3: Minimal Real Auth And Permissions

**Target time:** 1-2 weeks

**Goal:** Answer the first serious buyer objection: "Can users only see the docs
they are allowed to see?"

**Build:**

- Server-side auth. Do not rely on localStorage demo login.
- Organisation/workspace model.
- Simple roles: admin, editor, viewer.
- Notebook-level ACLs.
- Route enforcement for notebooks, documents, source files, ask, conversations,
  and wiki.
- Negative tests for cross-user access, unauthorized source fetches, viewer
  deletes, and unauthenticated requests.

**Done when:** the app can support a small secure internal-docs prototype and
permission failure behavior is tested.

## Phase 4: Admin Dashboard Polish

**Target time:** about 1 week

**Goal:** Let a buyer operate the system without asking you to touch the
terminal, database, or local files.

**Build:**

- Notebook create/rename/archive/delete.
- Document upload, delete, reassignment if needed.
- Ingest status, failure details, and retry flow.
- User invitation, role assignment, and notebook access management.
- Basic health page for API, R2R, model key, latest eval, and failed jobs.

**Done when:** an admin can manage common operations from the browser and failed
ingestion is visible and actionable.

## Phase 5: Analytics And Eval Reporting

**Target time:** about 1 week

**Goal:** Prove the assistant is working and expose where it is failing.

**Build:**

- Question/event log with notebook, user, timestamp, confidence, cited docs, and
  not-found outcomes.
- Unanswered/low-confidence report.
- Citation quality report.
- Eval run history with score trend and failed questions.
- Admin-facing reliability dashboard with tables first, charts later.

**Done when:** a buyer can see which questions failed, which docs are used, and
whether eval quality is improving.

## Phase 6: First Buyer-Pulled Integration

**Target time:** 1-2 weeks

**Goal:** Remove the first real adoption blocker named by a buyer.

**Choose based on job demand:**

- If the buyer says docs live in SharePoint, Google Drive, Notion, Zendesk,
  Intercom, HubSpot, Salesforce, or Freshdesk: build one connector.
- If the buyer says put this on our website or portal: build the embeddable
  widget.
- If the buyer says staff work in Slack or Teams: build one bot.
- If the buyer says support agents need it in tickets: build one Zendesk or
  Intercom sidebar.

**Default recommendation:** start with one document-source connector, likely
Google Drive, SharePoint, or Notion, because manual upload becomes the common
internal-docs blocker.

**Done when:** one integration works end to end and has clear setup docs plus a
minimal admin surface.

## Phase 7: Make The First Integration Supportable

**Target time:** 3-7 days

**Goal:** Make the first integration boring before cloning the pattern.

**Build:**

- Last sync time and failed sync reason.
- Retry button.
- Partial-success and rate-limit handling.
- Source provenance with original URL/path/id, last modified timestamp, and
  re-ingest history.
- Admin controls for enable/disable, credential rotation, source selection, and
  forced resync.
- Support runbook.
- Integration-specific eval set.

**Done when:** you can support the integration without manual database surgery,
and a future connector can reuse the same patterns.

## Phase 8: Embeddable Widget Or Second Channel

**Target time:** 1-2 weeks

**Goal:** Expand where users ask questions, but only after the data-source story
is credible.

**Default next build:** embeddable website/internal-portal widget.

**Build:**

- JS snippet or iframe.
- Read-only notebook token.
- Widget theme/config.
- Cross-origin deployment hardening.
- Minimal usage docs.

**Alternative:** if a live buyer pulls harder toward Slack/Teams or
Zendesk/Intercom, build that instead.

## Phase 9: Single-Tenant Managed Deployment

**Target time:** 1-2 weeks

**Goal:** Turn "I built a demo" into "I can keep this running for your team."

**Build:**

- Single-tenant deployment template with isolated database/storage, isolated env
  keys, domain, and TLS.
- Operational monitoring for app health, R2R health, failed ingest jobs,
  model/API failures, and storage usage.
- Backup and restore for local stores, documents, figures, and config/env.
- Update and rollback procedure.
- Managed-service terms for monitoring, response expectations, re-ingestion,
  model/API key rotation, and monthly eval report.

**Done when:** qDocent can be sold as a managed single-tenant internal-docs RAG
system with a clear boundary between one-off build and ongoing support.

## Timeline Summary

- **Upwork-ready demo and handoff:** about 1 week.
- **Credible paid prototype delivery:** 1-2 weeks.
- **Secure internal-docs project readiness:** 4-6 weeks.
- **Managed single-tenant service readiness:** 8-12 weeks.

The first sales threshold is Phase 1 plus enough of Phase 2 to avoid a brittle
handoff. Later phases should be funded by buyer demand whenever possible.
