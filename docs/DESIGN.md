# DESIGN — Manifest AI Dashboard (Layer #6)

> ⚠️ **Build status**: This layer is assigned to teammates and is **held**
> per BUILD-ORDER.md's Unit 6 gate. This file is the spec they build against.
> Antigravity must not start implementation here without explicit go-ahead —
> see BUILD-ORDER.md §6.

## 1. Purpose

The human-facing, terminal layer of the pipeline. Every processed email lands
here — auto-cleared or escalated — with enough context that a reviewer never
has to go dig through raw files.

## 2. Core Views

### 2.1 Triage Command Center (Kanban)
Three columns, auto-populated from `submission.json` + Firestore results:
- **Auto-Cleared** — `status: OK`
- **Discrepancy Found** — `status: MISMATCH`
- **Exception / Needs Review** — `status: NEEDS_REVIEW`, sub-grouped by
  `review_reason`

### 2.2 Side-by-Side Comparison View
For any `MISMATCH` card: SI value | BL value per field, mismatched fields in
red, matched fields in neutral/green. Includes the `source_snippet` per field
(explainability — no bounding boxes required for MVP, text snippet is enough).

### 2.3 Shipment Timeline
Vertical stage log per email, built from #1's pipeline trace:
`Email received → Classified → SI extracted → BL extracted → Fields compared
→ Discrepancies detected → Sent for review → Reviewer resolved`

### 2.4 Search / Filter
Filter the Kanban/table by: category, status, date, customer/shipper name.

### 2.5 Analytics Panel
Aggregate counts: total emails, per-category breakdown, mismatch rate,
human-review count, average processing time. Plus an **accuracy-over-time
chart** sourced from repeated `score_cli.py` runs (screenshot-worthy for the
pitch video).

### 2.6 One-Click "Draft Correction Email"
Button on any `MISMATCH` card → calls a small backend function (LLM call
using SI value, BL value, field name) → returns a drafted (never
auto-sent) email body for the reviewer to copy/send.

### 2.7 Review / Correction Interface
On any `NEEDS_REVIEW` or `MISMATCH` card: reviewer can confirm or correct the
system's finding. The correction is written to Firestore and feeds #5's
feedback loop.

### 2.8 Daily Digest (small add-on)
A scheduled summary view/export of the Analytics Panel, triggered by #7's
scheduler — not a separate page.

## 3. Data Contract for the Frontend

The dashboard reads only `SubmissionEntry` + `ComparisonResult` +
`ExtractionResult.fields[].source_snippet` (see ARCHITECTURE.md §2). Build
the entire UI against a **mock JSON file** matching this shape before any
real backend exists — this is the critical rule that keeps this layer
independent (see BUILD-ORDER.md).

```json
{
  "email_045": {
    "category": "BL_COMPARISON",
    "status": "MISMATCH",
    "has_defect": true,
    "defect_fields": ["container_count"],
    "field_results": [
      {"field_name": "container_count", "si_value": "3", "bl_value": "4",
       "match": false, "source_snippet": "Containers: 4 x 40HC"}
    ],
    "timeline": [
      {"time": "10:32", "stage": "Email received"},
      {"time": "10:34", "stage": "2 discrepancies detected"}
    ]
  }
}
```

## 4. Visual/UX Notes

- 3-column Kanban should feel like a real ops tool, not a demo toy —
  reference Trello/Linear-style card density, not sparse empty space.
- Red/green/amber color coding: consistent everywhere (mismatch=red,
  match=green/neutral, needs-review=amber).
- Mobile/responsive not required for the hackathon demo — optimize for a
  laptop screen shared during the pitch.

## 5. Stack Note

Build with Antigravity/Stitch generation tools once this unit is unlocked.
Suggested: React + Tailwind, or a single self-contained HTML/JS page if
faster for the team's experience level (see TECHSTACK.md §5 folder for where
this lives: `dashboard/frontend/`).
