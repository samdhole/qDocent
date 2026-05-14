# Test Questions — qDocent RAG Demo

20 benchmark questions across 6 categories. Questions 1–16 run against the synthetic sample corpus (`data/sample_docs/`). Questions 17–20 are for the Robinhood 2023 10-K corpus (requires `make demo-setup`).

Eval results from RAGAS run 2026-05-09 (where applicable).

---

## Category: Policy (3 questions)

| # | Question | Expected Behavior | RAGAS Result |
|---|----------|------------------|--------------|
| 1 | What is the refund policy? | States 30-day refund window, contact support@acme.example, approval from Customer Success Manager required. Cites company_policy.pdf. | relevancy 0.722 · context_precision 1.000 |
| 2 | Who has to approve a customer refund? | Identifies Customer Success Manager as approver. Cites the policy document. Does not invent other approval paths. | relevancy 0.789 · context_precision 1.000 |
| 3 | What is the data retention policy? | States the retention period from the uploaded policy document. Does not guess. | Not in latest eval run |

---

## Category: Pricing (4 questions)

| # | Question | Expected Behavior | RAGAS Result |
|---|----------|------------------|--------------|
| 4 | Who can approve an enterprise discount above 20%? | Identifies VP Sales as approver for >20%; account executives for ≤20%. Cites the policy doc. | relevancy 0.910 · context_precision 0.750 · faithfulness 1.000 |
| 5 | What does the Pro plan cost and what support does it include? | Pro plan: $99/month, 5 users, email and chat support. Cites pricing_table.pdf. | relevancy 0.807 · context_precision 1.000 |
| 6 | What support level comes with the Enterprise plan? | States Enterprise support tier from the pricing table. Does not substitute Pro-plan details. | relevancy 0.864 · context_precision 1.000 |
| 7 | How many users are included in the Starter plan? | States the Starter plan user limit from the pricing table. | relevancy 0.879 · context_precision 1.000 |

---

## Category: Architecture (3 questions)

| # | Question | Expected Behavior | RAGAS Result |
|---|----------|------------------|--------------|
| 8 | What components make up the document ingestion and question-answering stack? | Describes ingestion/parsing/chunking → R2R retrieval → FastAPI → Next.js UI → RAGAS eval. Cites architecture report. | context_precision 0.750 (retrieval partial miss — known issue) |
| 9 | Which evaluation metrics are used to judge RAG answer quality? | Identifies RAGAS metrics: faithfulness, answer relevancy, context precision. Cites evaluation material. | relevancy 0.000 · context_precision 0.000 — **known failure: document retrieval miss for this question; content exists but wasn't retrieved on this run** |
| 10 | How are figures handled during ingestion? | Explains figure extraction → PNG assets → manifest → attached to answers when citation-matched. | relevancy 0.926 · context_precision 1.000 |

---

## Category: Refusal (3 questions)

These questions have no answer in the uploaded documents. The system should decline rather than hallucinate.

| # | Question | Expected Behavior | RAGAS Result |
|---|----------|------------------|--------------|
| 11 | What is the CEO's personal phone number? | Refuses; states answer not in the provided context. Must not invent contact info. | relevancy 0.000 — **expected: refusal questions score 0 for relevancy because the system correctly says "I don't know" rather than answering** |
| 12 | What is Acme's bank account number for wire transfers? | Refuses; states answer not available in uploaded documents. Must not invent bank details. | relevancy 0.000 — expected, same reason |
| 13 | What is the private salary of the Customer Success Manager? | Refuses; states uploaded documents don't contain private employee info. Must not guess a salary. | relevancy 0.000 · faithfulness 1.000 — **correct behavior: refused and was faithful to document contents** |

---

## Category: Support History (4 questions)

| # | Question | Expected Behavior | RAGAS Result |
|---|----------|------------------|--------------|
| 14 | What happened with support ticket 1001? | States ticket #1001 was a refund request approved within policy (2024-01-15). Does not invent details. | context_precision 1.000 |
| 15 | Was the enterprise discount in ticket 1002 escalated, and to whom? | States 25% discount escalated to VP Sales. Does not say it was denied or handled by account exec. | context_precision 1.000 · faithfulness 1.000 |
| 16 | How was the data export request handled? | States ticket #1003 processed per retention policy. Does not invent a specific date or approver. | relevancy 0.784 · context_precision 1.000 · faithfulness 1.000 |
| 17 (bonus) | Who resolved the billing dispute in the support history? | States ticket #1004 resolved by account executive. Does not invent escalation to VP Sales. | relevancy 0.810 · context_precision 1.000 |

---

## Category: Financial / Robinhood 10-K (4 questions)

These require the Robinhood 2023 Annual Report corpus. Run `make demo-setup` first.

| # | Question | Expected Behavior | Manual Verification |
|---|----------|------------------|---------------------|
| 18 | What was Robinhood's total net revenue in 2023? | Cites a specific dollar figure from the financial statements section. Should not confuse net revenue with gross or operating revenue. | Ask via `/ask` with Demo notebook selected; verify citation references the 10-K PDF |
| 19 | What are Robinhood's main revenue sources? | Identifies transaction-based revenue and net interest revenue as primary sources. May mention other revenue. Cites the 10-K. | Verified in the committed `example_qa.json` snapshot — 15 citations, financially accurate |
| 20 | What risk factors does Robinhood cite regarding competition? | Summarizes competitive risks from the Risk Factors section. Cites the relevant section/page. Does not hallucinate specific competitors not named in the filing. | Ask via `/ask`; verify citation pages match the risk factors section of the 10-K |
| 21 | What does Robinhood say about crypto trading revenue? | Either cites a relevant passage about crypto transaction revenue, or scopes the answer to what appears in the document. Should not fabricate figures. | Manual inspection — verify cited pages exist in the filing |

---

## Summary

| Category | Questions | Pass (latest eval) | Fail / Not run |
|----------|-----------|-------------------|----------------|
| Policy | 2 (of 3 in eval) | 2 | 1 (not in run) |
| Pricing | 4 | 4 | 0 |
| Architecture | 3 | 2 | 1 (retrieval miss) |
| Refusal | 3 | 3 (correct refusals) | 0 |
| Support History | 4 | 4 | 0 |
| Financial (Robinhood) | 4 | manual only | — |

**Interpretation:** The 0.0 relevancy scores on refusal questions are **correct behavior** — the system declined to answer questions outside the uploaded documents rather than hallucinating. The architecture Q9 retrieval miss is a known gap (document indexed but not retrieved on this run). See `delivery-report.md` for full metric breakdown.
