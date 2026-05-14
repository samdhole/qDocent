# Known Limits — qDocent RAG Demo

This document is honest about what the system does and does not do in its current Phase 1 (local demo) state. Every item here has a planned path forward in the productization roadmap.

---

## Security and Authentication

**No production authentication or per-user document scoping.**

The current system has no login, no user accounts, and no access control. Anyone who can reach the web UI can see all documents and ask any question.

**Implication:** Do not upload real confidential client documents, proprietary data, HR records, legal files, or anything that should not be visible to all users.

**Path forward:** Phase 3 of the roadmap adds server-side auth, an org/workspace model, roles (admin/editor/viewer), and notebook-level access control lists (ACLs).

---

## Data Scope

**The system only answers from uploaded documents.**

It does not search the internet, use general knowledge, or fill in gaps by guessing. If the answer isn't in an uploaded document, the system should say so.

This is a feature, not a bug — citation-backed answers require source documents. The refusal behavior is tested: see `test-questions.md` questions 11–13.

**Edge case:** Occasionally the retrieval step may fail to surface a relevant chunk even when the content exists in the corpus (see Q9 failure in `delivery-report.md`). The answer will then be low-confidence or a refusal. Re-indexing or query reformulation typically resolves this.

---

## Deployment

**Local-only for Phase 1. No hosted URL, no Docker.**

The system requires three local processes (R2R on port 7272, FastAPI on port 8000, Next.js on port 3000). A developer reviewer can run it; a non-technical buyer cannot without help.

**Path forward:** Phase 2 adds a `docker compose up` path that starts all services from a single command. A simple hosted-demo option (for review purposes) is also on the roadmap.

See `api-key-and-deployment-notes.md` for the current local setup.

---

## Response Streaming

**Responses are not streamed.** The full answer loads at once, typically 2–5 seconds after submission.

**Path forward:** Streaming is a UI polish item. The API infrastructure supports it, but the current frontend waits for the complete response.

---

## Citation Display

**Citations open the source PDF at the cited page.** They do not highlight the specific passage inline (no in-PDF text overlay).

The chunk schema preserves bounding box coordinates (`bbox`), so a future PDF viewer can add precise passage highlights. The data is there; the UI overlay is not.

---

## Evaluation Coverage

**16-question RAGAS benchmark on synthetic + Robinhood data.**

This is a proof-of-quality benchmark, not a statistically exhaustive evaluation. The synthetic documents (policy, pricing, support history, architecture) are short and focused. The eval is honest: failed rows are visible, not hidden (see `delivery-report.md`).

**Path forward:** Phase 5 adds a question/event log, unanswered/low-confidence reports, and eval run history with score trends. A larger, domain-specific eval set is recommended before production deployment.

---

## Concurrent Users

**Tested single-user local.** Multi-user concurrency and load behavior have not been validated.

The FastAPI backend is async and R2R handles concurrent queries, but no load testing has been performed for this demo.

---

## Multi-Format Documents

**Supported:** PDF, DOCX, PPTX, web URLs (crawl4ai).

**Not supported:** Excel files (.xlsx), scanned PDFs without text layers (OCR requires a Mistral API key, not configured in the demo), audio/video transcription.

---

## Language

**English only.** The LLM (Gemini) can respond in other languages, but the evaluation dataset, chunking strategies, and citation parsing are tuned for English text.

---

## What Is Solid

- Ingestion pipeline: classify → parse → normalize → chunk → cite headers
- R2R pre-chunked ingest: DocQuery chunk headers preserve source/page/section metadata
- Figure extraction: PyMuPDF → PNG assets + manifest + R2R sidecar
- RAGAS evaluation loop: timestamped CSV and Markdown per run
- Workflow demo: support triage and email draft with human approval state
- 192 automated tests (~13 seconds runtime)
- Commercial-demo readiness gate: `python scripts/demo_readiness.py`
