# PRD — Manifest AI
### Shipping Document Verification System
**Averis x Monash Hackathon 2026** | Preliminary deadline: **22 Sept 2026, 12:00pm**

---

## 1. Problem Statement

A shipping operations team receives mixed emails in one inbox: document-comparison
requests, new SI requests, invoice queries, general messages, and spam. For a
document-comparison request, the team must check a draft **Bill of Lading (BL)**
against the **Shipping Instruction (SI)** — the source of truth — before the BL is
finalized.

Manual triage and comparison is slow, repetitive, and error-prone. The same field
is often labeled differently across documents ("Port of Loading" vs "Load Port"),
causing false mismatches or missed ones.

## 2. Goal

Build an AI system that:
1. **Classifies** every inbox email into one of 5 categories.
2. **Extracts** structured data from SI/BL attachments (text, PDF, DOCX, XLSX,
   scanned images).
3. **Compares** 7 required fields between SI and BL, recognizing that the same
   field may be labeled differently.
4. **Escalates** to a human when it cannot decide confidently — never guesses.
5. Produces a submission JSON in the exact required shape and improves over time
   from human corrections.

## 3. Required Output Schema (authoritative — from organizer `sdk/README.md`)

```json
{
  "email_001": {
    "category": "BL_COMPARISON",
    "status": "MISMATCH",
    "review_reason": null,
    "has_defect": true,
    "defect_fields": ["consignee"]
  }
}
```

- `category`: `BL_COMPARISON` | `SI_REQUEST` | `INVOICE_QUERY` | `GENERAL` | `SPAM`
- `status` (BL_COMPARISON only): `OK` | `MISMATCH` | `NEEDS_REVIEW`
- `status` is **orthogonal** to `has_defect` — a blank/unreadable field is
  `NEEDS_REVIEW`, **never** `MISMATCH`. This is a top-priority correctness rule.
- `review_reason` (only when `NEEDS_REVIEW`): `wrong_doc_type` |
  `missing_attachment` | `unreadable` | `missing_value`

## 4. The 7 Compared Fields

`shipper`, `consignee`, `notify_party`, `port_of_loading`, `port_of_discharge`,
`container_count`, `gross_weight_kg`

## 5. Scoring (what we're optimizing for)

`final_score = 0.30 × stage1_macroF1 (classification) + 0.20 × stage3_defectF1
(field-level defect detection) + 0.50 × end_to_end (defects routed AND flagged
with exact fields)`. `NEEDS_REVIEW` cases are graded on a separate reliability
axis — get this right, it's free credit that doesn't hurt the core score.

Preliminary round rubric (100 pts): System Design 15, Working Core Prototype 25,
Tech Integration 15, Feasibility 15, Problem Understanding 10, Innovation 10,
Practical Value 10. **"Working Core Prototype" is the single biggest line —
a fully working simple system beats a broken ambitious one.**

## 6. Feature Set (8 core layers + confirmed additions)

| # | Layer | Core responsibility |
|---|---|---|
| 1 | Multi-Agent Orchestration | Routes each email through the pipeline; retries, error recovery, classifier evidence, full logging |
| 2 | Semantic Field Matching | Synonym dictionary → embeddings fallback; aligns differently-labeled fields |
| 3 | Extraction (Gemini Vision) | Reads text/PDF/DOCX/XLSX/scanned docs; per-field confidence + source snippet; missing-attachment detection |
| 4 | Confidence-Scored Escalation | Combines signals into one confidence score; routes low-confidence cases to human review with evidence |
| 5 | Self-Improving Feedback Loop | Logs corrections; few-shot injection now, periodic fine-tune later |
| 6 | Explainable Audit Dashboard | Kanban triage, side-by-side comparison, timeline, analytics, draft-email button *(held for teammates — see BUILD-ORDER.md)* |
| 7 | Real-Time Architecture | Pub/Sub-driven processing instead of one-shot batch |
| 8 | Multi-Method Ensemble Voting | Regex + OCR/NER + LLM extraction cross-checked; fuzzy match prevents false-positive mismatches |

Additional confirmed features: Synthetic Test / Failure Simulator (demo tool),
Daily digest add-on to dashboard analytics.

## 7. Non-Functional Requirements

- **AI must be core**, not bolt-on (hard hackathon requirement)
- **Must use Google Cloud** (Vertex AI, hard requirement)
- Must never read `ground_truth.json` from pipeline code — score only via
  `score_cli.py` or `/submit`
- Must never fabricate a mismatch on a blank/unreadable field
- System must degrade gracefully — a crash on one email must not stop the batch

## 8. Out of Scope (for Preliminary Round)

Shipment version tracking (BL v1/v2/v3), natural-language chatbot query
assistant — both deferred to a stated "Final Round roadmap" in the pitch, not
built now.

## 9. Success Criteria

- End-to-end pipeline runs against `data-basic/` with zero crashes
- Self-eval score via `score_cli.py` improves measurably across iterations
- All 20 edge cases in `data-advanced/` (the labeled `NEEDS_REVIEW` set) are
  correctly escalated with the right `review_reason`
- Dashboard renders real pipeline output, not just mock data, before submission
- 5-minute pitch video demonstrates: a mismatch caught, an escalation firing,
  the dashboard reacting live
