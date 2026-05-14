# Human Test Plan: RAG Portfolio Scaffold

**Implementation plan:** `docs/implementation-plans/2026-05-07-rag-portfolio-scaffold/`
**Generated:** 2026-05-08
**Automated gate:** 98/98 tests passing (`pytest tests/ -q`)

---

## Prerequisites

- Python 3.11 venv active: `.venv\Scripts\activate` (Windows)
- `.env` populated with `OPENAI_API_KEY` and `R2R_BASE_URL=http://localhost:7272`
- Sample docs generated: `python scripts/create_sample_docs.py` — confirm `data/sample_docs/company_policy.pdf`, `pricing_table.pdf`, `sample_support_history.pdf` exist
- All four services running, each in its own terminal:
  - Terminal 1: `make r2r` — wait for R2R to bind to port 7272
  - Terminal 2: `make api` — wait for `Uvicorn running on http://0.0.0.0:8000`
  - Terminal 3: `make web` — wait for `Local: http://localhost:3000`
- Automated test gate: `.venv/Scripts/python.exe -m pytest tests/ -q` reports `98 passed`

---

## Phase 1 — Connection and Ingestion (AC1)

| Step | Action | Expected |
|------|--------|----------|
| 1.1 | Run `make smoke` | Console prints "Connecting to R2R at http://localhost:7272", "Document created: ...", "RAG response: ...", and final line "Smoke test passed.". Exit code 0. |
| 1.2 | Run `make ingest` | One "OK" line per PDF in `data/sample_docs/` (3 lines), final line "Done.". Exit code 0. |
| 1.3 | Stop the R2R terminal (Ctrl+C in Terminal 1). Run `python scripts/smoke_r2r.py` | Script prints "Ingestion failed: …" followed by "Is R2R running? Start it with: make r2r". Exit code non-zero (sys.exit). |
| 1.4 | Restart `make r2r` in Terminal 1 before continuing | R2R reachable again. |

---

## Phase 2 — RAGAS Evaluation (AC2)

| Step | Action | Expected |
|------|--------|----------|
| 2.1 | `python -c "import yaml; d=yaml.safe_load(open('packages/evals/eval_dataset.yaml')); print(len(d['questions']), [q['id'] for q in d['questions']])"` | Prints `4 ['refund_policy', 'enterprise_discount', 'pro_plan_price', 'unsupported_answer']`. |
| 2.2 | Run `make eval` | Console prints "Running RAGAS evaluation (4 questions) ...", a per-question results table, and final lines "Saved CSV: reports/evals/ragas_results_<timestamp>.csv" + "Saved Markdown: …". Exit code 0. |
| 2.3 | List outputs: `ls reports/evals/ragas_results_*.csv reports/evals/ragas_summary_*.md` | At least one CSV and one MD file with timestamp suffixes (e.g. `ragas_results_20260508_143012.csv`). |
| 2.4 | Inspect latest CSV: open it in any viewer | Header row contains `question_id, answer_relevancy, context_precision, faithfulness` (additional columns acceptable). At least 4 data rows, one per question ID from step 2.1. |
| 2.5 | Inspect latest MD file | Contains "# RAGAS Evaluation Summary", per-question table, and "## Averages" section listing all three metrics. |

---

## Phase 3 — FastAPI Endpoints (AC3)

| Step | Action | Expected |
|------|--------|----------|
| 3.1 | `curl http://localhost:8000/health` | Body `{"status":"ok"}`, HTTP 200. |
| 3.2 | `curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"question":"What is the refund policy?"}'` | HTTP 200. Body has all of: `answer`, `citations` (≥1 element), `retrieved_contexts` (≥1 element), `confidence_label` ∈ {high, medium, low, needs_review}, `needs_human_review` boolean. Answer mentions 30 days, support email, or CSM approval. |
| 3.3 | `curl -X POST http://localhost:8000/ingest -F "file=@data/sample_docs/company_policy.pdf"` | HTTP 200, body contains `"status":"ok"` and a `result` field with quality report. |
| 3.4 | `curl -X POST http://localhost:8000/ingest -F "file=@README.md"` (any non-PDF) | HTTP 400, body `{"detail":"Only PDF files are supported."}`. |
| 3.5 | `curl http://localhost:8000/eval/results` | HTTP 200, body is a JSON array of objects each containing `question_id` plus the 3 RAGAS metric columns from step 2.4. |
| 3.6 | Stop R2R (Terminal 1, Ctrl+C). `curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"question":"test"}'` | Output `503`. Restart `make r2r` afterward. |

---

## Phase 4 — Web UI (AC4)

| Step | Action | Expected |
|------|--------|----------|
| 4.1 | Open `http://localhost:3000` in a browser | Page loads with "DocQuery" heading and three navigation cards/links: "Ask", "Documents", "Evals". Each link navigates to `/ask`, `/documents`, `/evals` respectively. |
| 4.2 | Navigate to `/ask`, type "What is the refund policy?" into the input, click submit | Within ~10s the page renders: an answer text block, at least one citation chip/badge (showing source filename + page), a retrieved-chunks panel with at least one chunk and a numeric score, and a confidence badge (label one of high/medium/low/needs_review). |
| 4.3 | On `/ask`, type "What is the CEO's personal phone number?" and submit | Response renders without inventing a phone number. Confidence badge shows `low` OR answer text says the information is not in the provided documents. No string of digits resembling a phone number appears in the answer body. |
| 4.4 | Navigate to `/evals` | Table appears with one row per question from `eval_dataset.yaml`. Columns include `question_id`, `answer_relevancy`, `context_precision`, `faithfulness`. Numeric values are decimals (e.g. 0.85). Pass scores render in green, fail in red. |
| 4.5 | Navigate to `/documents`. Upload `data/sample_docs/pricing_table.pdf` via the upload control | Success message displays. Confirm `reports/ingestion/pricing_table.json` and `pricing_table.md` now exist on disk. |

---

## Phase 5 — Ingestion Pipeline Quality (AC5, AC6, AC7)

| Step | Action | Expected |
|------|--------|----------|
| 5.1 | `python -c "from packages.ingestion.classify_document import classify_document; print(classify_document('data/sample_docs/company_policy.pdf'))"` | Output dict has all 7 keys: `file_name`, `is_scanned`, `has_tables`, `has_columns`, `document_type`, `recommended_template`, `recommended_parser`. `document_type=='general'` and `recommended_parser=='fast_text'`. |
| 5.2 | `python -c "from packages.ingestion.classify_document import classify_document; print(classify_document('data/sample_docs/pricing_table.pdf'))"` | `document_type=='table_heavy'`, `recommended_parser=='table_aware'`. |
| 5.3 | `cat reports/ingestion/pricing_table.json` (or open in viewer) after step 4.5 | JSON has all 9 keys: `document_id`, `document_type`, `parser_used`, `pages`, `chunks`, `tables_detected` (≥1 for pricing PDF), `figures_detected`, `low_confidence_pages` (list), `citation_coverage_estimate` (float 0–1). |
| 5.4 | Open `reports/ingestion/pricing_table.md` | Contains "# Ingestion Quality Report:" header, "## Summary" section with field values, and a warnings section. |
| 5.5 | *(OCR — only if Tesseract installed)* `python -c "from packages.ingestion.parse_pdf import parse_pdf; pages = parse_pdf('data/sample_docs/company_policy.pdf', 'ocr'); print([(p['page_number'], p['confidence']) for p in pages])"` | Each page has a `confidence` float in [0.0, 100.0]. Skip if Tesseract not installed locally. |

---

## Phase 6 — Support Triage Workflow (AC8)

| Step | Action | Expected |
|------|--------|----------|
| 6.1 | `curl -X POST http://localhost:8000/workflows/support/triage -H "Content-Type: application/json" -d '{"message":"I need a refund for my purchase."}'` | HTTP 200. Body has all 8 fields: `customer_message`, `intent`, `retrieved_contexts`, `draft_response`, `citations`, `confidence_label`, `requires_human_approval` (`true`), `final_response` (`"[Awaiting human approval]"`). |
| 6.2 | `curl -X POST http://localhost:8000/workflows/support/triage -H "Content-Type: application/json" -d '{"message":"What are your business hours?"}'` | If R2R retrieved high-confidence non-sensitive context: `requires_human_approval` is `false` and `final_response` equals the `draft_response` (not the placeholder). |
| 6.3 | `curl -X POST http://localhost:8000/workflows/support/email-draft -H "Content-Type: application/json" -d '{"message":"Draft an email about the refund."}'` | HTTP 200. `requires_human_approval` is `true`. `final_response` is `"[Awaiting human approval before sending email]"`. |
| 6.4 | Stop R2R, then re-run step 6.1 | HTTP 503. Restart R2R. |

---

## Phase 7 — End-to-End User Journey

**Purpose:** Validates the full RAG portfolio loop a portfolio reviewer would walk through — ingest → ask → evaluate → inspect.

1. Reset state: `python scripts/reset_local_data.py` then `make clean`. Confirm `reports/evals/` and `reports/ingestion/` are emptied.
2. `make ingest` — confirm 3 OK lines.
3. Open `http://localhost:3000/ask`, ask "What does the Pro plan cost?" — answer should mention `$99/month`, 5 users, email/chat support; at least one citation references `pricing_table.pdf`.
4. Open `http://localhost:3000/ask`, ask "Who can approve a 25% enterprise discount?" — answer should mention VP Sales; high or medium confidence badge.
5. Open `http://localhost:3000/ask`, ask "What is the CEO's personal phone number?" — confidence `low` and graceful refusal (no fabricated number).
6. Run `make eval` — confirm new timestamped CSV/MD appear in `reports/evals/`.
7. Open `http://localhost:3000/evals` — table renders all four questions with metric scores; verify color coding shows pass on the three supported questions.
8. `curl -X POST http://localhost:8000/workflows/support/triage -H "Content-Type: application/json" -d '{"message":"Can I get a discount?"}'` — confirm `requires_human_approval: true` and `final_response: "[Awaiting human approval]"`.

---

## Phase 8 — Failure-mode Resilience

**Purpose:** Validates the system degrades gracefully when R2R is unavailable.

1. With all services running, open `/ask` in browser, submit "What is the refund policy?" — confirm normal answer.
2. Stop R2R (Terminal 1, Ctrl+C). Refresh `/ask`, submit the same question.
3. UI surfaces an error state (not a crash, not a fabricated answer). Browser console may show 503 from `/ask`.
4. `curl -X POST http://localhost:8000/workflows/support/triage -H "Content-Type: application/json" -d '{"message":"hi"}'` — HTTP 503, body has `detail` field.
5. Restart `make r2r`, refresh `/ask`, resubmit — answer returns successfully.

---

## Traceability

| Acceptance Criterion | Automated Test | Manual Step |
|----------------------|----------------|-------------|
| AC1.1 smoke ingest+RAG | — | Phase 1 step 1.1 |
| AC1.2 bulk ingest | — | Phase 1 step 1.2 |
| AC1.3 R2R-down error msg | — | Phase 1 step 1.3 |
| AC2.1 dataset shape | — (yaml validated by inline command) | Phase 2 step 2.1 |
| AC2.2 eval e2e | — | Phase 2 step 2.2 |
| AC2.3 timestamped outputs | — | Phase 2 step 2.3 |
| AC2.4 per-question rows | — | Phase 2 step 2.4 |
| AC2.5 three RAGAS metrics | — | Phase 2 step 2.4 |
| AC3.1 GET /health | `tests/test_api_routes.py::test_health` | Phase 3 step 3.1 |
| AC3.2 POST /ask fields | `tests/test_api_routes.py::test_ask_success` | Phase 3 step 3.2 |
| AC3.3 POST /ingest PDF | `tests/test_route_ingest.py::test_post_ingest_pdf_success` | Phase 3 steps 3.3–3.4 |
| AC3.4 GET /eval/results | `tests/test_api_routes.py::test_eval_results_with_data` | Phase 3 step 3.5 |
| AC3.5 503 when R2R down | `tests/test_api_routes.py::test_ask_r2r_unavailable` | Phase 3 step 3.6 |
| AC4.1 landing page nav | — | Phase 4 step 4.1 |
| AC4.2 /ask rendering | — | Phase 4 step 4.2 |
| AC4.3 /evals table | — | Phase 4 step 4.4 |
| AC4.4 unsupported question | — | Phase 4 step 4.3 |
| AC5.1 classify_document fields | `tests/test_classify_document.py::test_classify_document_required_fields` | Phase 5 step 5.1 |
| AC5.2 policy/pricing types | `tests/test_classify_document.py::TestClassifyType::*` | Phase 5 steps 5.1–5.2 |
| AC6.1 chunks 9 fields | `tests/test_chunk_templates.py::test_make_chunk_all_required_fields` | Phase 4 step 4.5 |
| AC6.2 table chunks markdown+text | `tests/test_chunk_templates.py::test_table_aware_chunks_with_table_metadata` | Phase 5 step 5.3 |
| AC6.3 OCR confidence | — | Phase 5 step 5.5 (Tesseract required) |
| AC7.1 JSON+MD reports | `tests/test_quality_report.py::test_json_file_written` | Phase 5 steps 5.3–5.4 |
| AC7.2 JSON 9 fields | `tests/test_quality_report.py::test_generate_report_required_fields` | Phase 5 step 5.3 |
| AC7.3 low-conf pages | `tests/test_quality_report.py::test_low_confidence_page_threshold` | (automated only) |
| AC8.1 run_support_triage state | `tests/test_support_triage_graph.py::test_support_triage_returns_full_state` | Phase 6 step 6.1 |
| AC8.2 sensitive-topic approval | `tests/test_approval_policy.py::test_requires_approval_sensitive_topic_*` | Phase 6 step 6.1 |
| AC8.3 no-citations approval | `tests/test_approval_policy.py::test_requires_approval_no_citations` | (automated only) |
| AC8.4 confidence_label='low' | `tests/test_approval_policy.py::TestConfidenceFromContexts::*` | (automated only) |
| AC8.5 final_response branches | `tests/test_support_triage_graph.py::test_support_triage_returns_full_state` + `test_support_triage_high_confidence_clean_no_approval` | Phase 6 steps 6.1–6.2 |
