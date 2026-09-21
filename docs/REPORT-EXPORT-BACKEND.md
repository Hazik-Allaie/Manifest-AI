# POST-UNIT-13 ADD-ON — PDF Report Export (Backend Changes)

> Status: **Not yet started.** This is a stretch feature, only build if Unit
> 13 is fully complete, submitted, and time remains before the deadline.

## What This Adds

A downloadable, formatted PDF report for a single shipment — standalone,
shareable outside the dashboard (email attachment, compliance record, print).

## Backend Changes Required

### 1. New Module: `dashboard/backend/report_export.py`

```python
from shared.schemas import ComparisonResult, SubmissionEntry

def generate_shipment_report_pdf(email_id: str) -> bytes:
    """
    Pull the full result for one email (from Firestore or submission.json),
    render it into a formatted PDF, return the PDF bytes.
    """
    # 1. Fetch ComparisonResult + timeline + metadata for email_id
    # 2. Render into a PDF template (see Library choice below)
    # 3. Return raw PDF bytes (or write to a temp file and return the path)
```

### 2. New API Endpoint (add to `dashboard/backend/`)

```
GET /api/shipments/{email_id}/report.pdf
```
Returns the generated PDF as a file download (`Content-Type: application/pdf`,
`Content-Disposition: attachment; filename="shipment_{email_id}_report.pdf"`).

### 3. Library Choice

Use `reportlab` (already listed as an optional dependency in
`docs/TECHSTACK.md`) or `weasyprint` if you'd rather template with HTML/CSS
first (often faster to get a clean-looking layout).

```
pip install reportlab
# or
pip install weasyprint
```

### 4. Report Content — Must Match the Dashboard's Comparison View

Pull directly from the same `ComparisonResult` + `ExtractionResult` data the
dashboard already renders — do not re-derive or re-query separately, to
avoid the report and the dashboard ever showing different numbers for the
same shipment. Include:
- Email ID, subject, sender, processed timestamp
- Category + status (OK / MISMATCH / NEEDS_REVIEW)
- Field-by-field table: SI value | BL value | match/mismatch
- Timeline (from the pipeline trace log)
- If `NEEDS_REVIEW`: the `review_reason` and reviewer's resolution (if
  already corrected)

### 5. Schema Addition (small, additive — does not break existing contract)

No changes needed to `shared/schemas/` — this feature only *reads* existing
`ComparisonResult`/`SubmissionEntry` data, it doesn't introduce a new shape
other modules depend on. Safe to build without re-opening the frozen
contract.

## Testing

- Generate a report for one `OK`, one `MISMATCH`, and one `NEEDS_REVIEW`
  email — confirm all three render correctly and match what the dashboard
  shows for the same email.
- Confirm the PDF opens correctly outside the browser (a real download, not
  a broken/corrupt file).

## Effort Estimate

Small — roughly 2–4 hours for one person familiar with the codebase,
assuming `reportlab`/`weasyprint` and the data-fetching logic go smoothly.
