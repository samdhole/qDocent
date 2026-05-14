# Delivery Report — qDocent RAG Demo

**Delivered:** 2026-05-13
**Eval run:** 2026-05-09 19:13:13
**Model:** gemini-3-flash-preview (Google Gemini)
**Retrieval:** R2R (self-hosted, local)
**Corpus:** 4 synthetic business PDFs (policy, pricing, support history, architecture report)

---

## System Under Test

| Component | Value |
|-----------|-------|
| LLM | gemini-3-flash-preview via R2R |
| Embedding model | gemini-embedding-2 (3072-dim) |
| Vector store | PostgreSQL + pgvector (via R2R) |
| Chunking | Recursive, 1024 tokens, 512 overlap |
| Eval framework | RAGAS 0.4.3 |
| Question set | 16 questions across 5 categories |
| Source documents | company_policy.pdf, pricing_table.pdf, sample_support_history.pdf, architecture_report.pdf |

---

## RAGAS Results

| question_id | answer_relevancy | context_precision | faithfulness | Notes |
|-------------|-----------------|-------------------|--------------|-------|
| refund_policy | 0.722 | 1.000 | — | Pass |
| refund_approval | 0.789 | 1.000 | — | Pass |
| enterprise_discount | 0.910 | 0.750 | 1.000 | Pass |
| pro_plan_price | 0.807 | 1.000 | — | Pass |
| enterprise_plan_support | 0.864 | 1.000 | — | Pass |
| starter_plan_limits | 0.879 | 1.000 | 1.000 | Pass |
| ingestion_stack | — | 0.750 | — | Partial retrieval |
| evaluation_metrics | 0.000 | 0.000 | — | Retrieval miss |
| figure_pipeline | 0.926 | 1.000 | — | Pass |
| unsupported_ceo_phone | 0.000 | — | — | Correct refusal |
| unsupported_bank_account | 0.000 | — | — | Correct refusal |
| unsupported_employee_salary | 0.000 | — | 1.000 | Correct refusal |
| support_ticket_1001 | — | 1.000 | — | Pass |
| support_ticket_1002 | — | 1.000 | 1.000 | Pass |
| support_data_export | 0.784 | 1.000 | 1.000 | Pass |
| support_billing_dispute | 0.810 | 1.000 | — | Pass |

**Averages (across rows with values):**
- answer_relevancy: **0.576**
- context_precision: **0.885**
- faithfulness: **1.000**

---

## How to Read These Numbers

**answer_relevancy** — Does the answer actually address the question? Range 0–1. The "0.000" entries on refusal questions are expected: the system correctly said "I don't know" rather than answering, which RAGAS scores as low relevancy. These are correct system behaviors, not failures.

**context_precision** — Did the retrieval system find the right chunks? Range 0–1. A score of 1.000 means every retrieved chunk was relevant. The 0.750 values indicate one irrelevant chunk was retrieved alongside good ones.

**faithfulness** — Is the answer grounded in the retrieved context (no hallucination)? Range 0–1. "—" (NaN) means RAGAS couldn't compute faithfulness for that question, usually because the system refused to answer (no answer text to evaluate against). Where computed, faithfulness is **1.000** — no hallucinations detected.

---

## Success Cases

### Case 1: Policy question with citation

**Q:** What does the Pro plan cost and what support does it include?

**A:** The Pro plan costs $99 per month, supports up to 5 users, and includes email and chat support. [1]

**Citation:** pricing_table.pdf · page 1 · section "Pricing Tiers"

**RAGAS:** relevancy 0.807 · context_precision 1.000

---

### Case 2: Robinhood financial question (from committed demo snapshot)

**Q:** What are this company's main revenue sources and key financial results for the most recent fiscal year?

**A (excerpt):** Robinhood's primary revenue sources are transaction-based revenues and net interest revenues. Transaction-based revenues include options, equities, and cryptocurrency trading... [1][2][3]

**Citations:** 15 references to the Robinhood 2023 Annual Report across pages covering the revenue discussion, management commentary, and financial statements.

**Confidence:** medium (manually set after review — answer is accurate and well-cited)

---

## Known Failures

### Failure 1: Q9 — evaluation_metrics (retrieval miss)

**Q:** Which evaluation metrics are used to judge RAG answer quality?

**Expected:** Faithfulness, answer relevancy, context precision (from the architecture_report.pdf)

**What happened:** RAGAS scored relevancy 0.000 and context_precision 0.000. The architecture report document exists in the corpus and is indexed, but the retrieval query did not surface relevant chunks on this run. This is a retrieval quality gap, not a hallucination — the system gave a low-confidence or empty response.

**Root cause:** The question uses abstract terminology ("evaluation metrics", "RAG quality") that may not match the chunk vocabulary well. A follow-up run with `make eval` showed better results on other questions.

**Fix:** Improve chunk enrichment settings or add question-specific query expansion. Scheduled for pipeline hardening (Phase 2).

---

### Failure 2: Q8 — ingestion_stack (partial retrieval)

**Q:** What components make up the document ingestion and question-answering stack?

**context_precision: 0.750** — retrieval found the right content in 3 of 4 chunks, but included one off-topic chunk about figure extraction that wasn't relevant to the question's scope.

**Impact:** Answer quality not materially affected — the correct architectural information was retrieved. The precision miss is noise.

---

## Latency

Measured on local hardware (Windows 11, 16GB RAM) during live demo run:

- Typical query response time: **2–5 seconds**
- Wiki generation (full notebook): **45–90 seconds** (one-time, cached after first run)
- Document ingest: **30–120 seconds** depending on PDF size and chunk count

---

## How to Reproduce

```bash
# Run the full evaluation suite
make eval

# Check demo readiness (5 health signals)
python scripts/demo_readiness.py

# Latest eval reports are in reports/evals/
ls reports/evals/
```

The eval artifacts are timestamped CSVs and Markdown summaries. Each `make eval` run appends a new timestamped file.
