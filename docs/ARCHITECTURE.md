# ARCHITECTURE — Manifest AI

## 1. Pipeline Flow

```
Email (JSON record)
      │
      ▼
┌──────────────────────┐
│ #1 CLASSIFIER AGENT    │  → category + evidence
└──────────────────────┘
      │ (only BL_COMPARISON continues)
      ▼
┌──────────────────────┐
│ #3 EXTRACTOR           │  → per-doc fields + confidence + source snippet
│   (+ #8 ensemble vote) │     (or: missing_attachment / unreadable / wrong_doc_type)
└──────────────────────┘
      │
      ▼
┌──────────────────────┐
│ #2 FIELD MATCHER        │  → aligns SI/BL fields despite label differences
│  (dict → embeddings)   │
└──────────────────────┘
      │
      ▼
┌──────────────────────┐
│ COMPARATOR (#8 fuzzy)  │  → per-field match/mismatch, avoids false positives
└──────────────────────┘
      │
      ▼
┌──────────────────────┐
│ #4 CONFIDENCE ROUTER    │
└──────────────────────┘
      │                    │
  high confidence      low confidence / missing / unreadable
      ▼                    ▼
  submission.json      NEEDS_REVIEW + review_reason
   entry (OK/          → #6 Dashboard escalation queue
    MISMATCH)           → human resolves → #5 feedback loop
```

`#7` (Pub/Sub) wraps the whole flow so it triggers per-email instead of one
batch script. `#6` (dashboard) is the terminal, human-facing layer for every
outcome — auto-cleared or escalated.

## 2. Shared Data Contract (Pydantic — put in `shared/schemas/`)

This is the single most important file in the repo. Every module reads/writes
only these shapes. No module should invent its own ad-hoc dict shape.

```python
from pydantic import BaseModel
from typing import Literal, Optional

class ClassificationResult(BaseModel):
    email_id: str
    category: Literal["BL_COMPARISON","SI_REQUEST","INVOICE_QUERY","GENERAL","SPAM"]
    evidence: list[str]
    confidence: float

class ExtractedField(BaseModel):
    field_name: Literal["shipper","consignee","notify_party","port_of_loading",
                         "port_of_discharge","container_count","gross_weight_kg"]
    value: Optional[str]
    source_snippet: Optional[str]
    confidence: float

class ExtractionResult(BaseModel):
    email_id: str
    doc_type: Literal["SI","BL"]
    fields: list[ExtractedField]
    doc_status: Literal["ok","missing","unreadable","wrong_doc_type"] = "ok"

class FieldComparison(BaseModel):
    field_name: str
    si_value: Optional[str]
    bl_value: Optional[str]
    match: bool
    match_confidence: float

class ComparisonResult(BaseModel):
    email_id: str
    field_results: list[FieldComparison]
    overall_confidence: float

class SubmissionEntry(BaseModel):
    category: Literal["BL_COMPARISON","SI_REQUEST","INVOICE_QUERY","GENERAL","SPAM"]
    status: Optional[Literal["OK","MISMATCH","NEEDS_REVIEW"]] = None
    review_reason: Optional[Literal["wrong_doc_type","missing_attachment",
                                     "unreadable","missing_value"]] = None
    has_defect: bool = False
    defect_fields: list[str] = []
```

`SubmissionEntry` is what finally gets dumped into `submission.json` — this
exact shape, and only this shape, is what `score_cli.py` / `/submit` expect.

## 3. Confidence Routing Rule (critical correctness rule)

A blank or unreadable field is **never** a mismatch. The router must check
`doc_status` and per-field extraction confidence **before** comparing values:

```
if doc_status == "missing"        → NEEDS_REVIEW, review_reason=missing_attachment
if doc_status == "unreadable"     → NEEDS_REVIEW, review_reason=unreadable
if doc_status == "wrong_doc_type" → NEEDS_REVIEW, review_reason=wrong_doc_type
if any required field has null/blank value → NEEDS_REVIEW, review_reason=missing_value
else → compare normally → OK or MISMATCH
```

## 4. Module Ownership (see PRD.md §6 and BUILD-ORDER.md for sequencing)

| Module | Owner | Depends on |
|---|---|---|
| #1 Orchestration | Person A | shared schemas |
| #3 Extraction | Person B | shared schemas |
| #2 Matching + #8 Ensemble | Person C | #3's output shape |
| #4 Escalation + #6 Dashboard | Person D (+ friends on #6) | #2/#3/#8 output |
| #7 Infra + #5 Feedback Loop | Person E | Firestore schema |

## 5. Escalation Evidence Packet (for #4 → #6)

Every escalation must carry, not just a flag:
```json
{
  "email_id": "email_045",
  "review_reason": "missing_value",
  "field": "gross_weight_kg",
  "source_snippet": "GROSS WEIGHT: ???",
  "system_guess": null
}
```
