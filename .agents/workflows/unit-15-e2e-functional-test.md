---
name: unit-15-e2e-functional-test
description: Test every feature of the deployed system end-to-end through the live frontend against the live backend
---

## Prerequisite
`unit-14-frontend-build-deploy.md` complete — both frontend and backend are
live and connected (see `docs/DEPLOYMENT-LOG.md` for the URLs).

## Goal
Verify every feature actually works correctly when used through the real,
deployed website — not mock data, not localhost, not isolated unit tests.
This is the final check that the whole system behaves correctly as a real
user (a shipping ops reviewer) would experience it.

## Steps — Test Every Feature Individually

Go through each item below using the live frontend URL. For each, record
pass/fail and a short note.

### 1. Data Loading
- [ ] Dashboard loads real processed email data from the live backend on
      first visit (not a blank screen, not mock data, not an error state).

### 2. Kanban Triage Board (`docs/DESIGN.md` §2.1)
- [ ] Auto-Cleared column shows only `status: OK` emails.
- [ ] Discrepancy Found column shows only `status: MISMATCH` emails.
- [ ] Exception/Needs Review column shows only `status: NEEDS_REVIEW`
      emails, and sub-groups correctly by `review_reason`.
- [ ] Card counts match the actual data (spot-check against
      `submission.json` or Firestore).

### 3. Side-by-Side Comparison View (§2.2)
- [ ] Clicking a `MISMATCH` card shows SI value vs BL value per field.
- [ ] Mismatched fields are visually distinct (e.g. red) from matched ones.
- [ ] Source snippet is shown for at least the mismatched field(s).

### 4. Shipment Timeline (§2.3)
- [ ] Opening any email shows its full stage-by-stage timeline in correct
      chronological order.

### 5. Search / Filter (§2.4)
- [ ] Filtering by category returns only matching emails.
- [ ] Filtering by status returns only matching emails.
- [ ] Filtering by date range works correctly.
- [ ] Filtering/searching by customer/shipper name works correctly.
- [ ] Filters can be combined without breaking.

### 6. Analytics Panel (§2.5)
- [ ] Total email count matches the real dataset size.
- [ ] Per-category breakdown numbers are correct.
- [ ] Mismatch rate, human-review count, and average processing time
      display and look plausible (not zero/null/NaN).
- [ ] Accuracy-over-time chart renders with real score history data.

### 7. One-Click "Draft Correction Email" (§2.6)
- [ ] Button appears only on `MISMATCH` cards.
- [ ] Clicking it generates a real drafted email body referencing the
      correct field, SI value, and BL value for that specific shipment.
- [ ] Confirm the draft is **not** auto-sent — it only displays/offers to
      copy.

### 8. Review / Correction Interface (§2.7)
- [ ] A reviewer can open a `NEEDS_REVIEW` or `MISMATCH` case and either
      confirm or correct the system's finding.
- [ ] Submitting a correction is saved (check Firestore or reload the page
      to confirm persistence).
- [ ] The corrected case's displayed status updates accordingly.

### 9. Daily Digest (§2.8)
- [ ] The digest view/export shows a correct summary matching the
      Analytics Panel's underlying data for that period.

### 10. Edge Cases — Live Verification
- [ ] Open at least one email of each `review_reason` type
      (`wrong_doc_type`, `missing_attachment`, `unreadable`,
      `missing_value`) through the live UI and confirm it displays
      correctly and matches the backend's actual classification.

### 11. Cross-Browser / Basic Resilience
- [ ] Reload the page mid-session — state doesn't break.
- [ ] No unhandled JavaScript errors in the browser console on any view
      tested above.

### 12. Report Export (only if `unit-13`'s stretch add-on was built —
       see `REPORT-EXPORT-FRONTEND.md`)
- [ ] "Download Report" button generates and downloads a correctly
      formatted PDF for at least one `OK`, one `MISMATCH`, and one
      `NEEDS_REVIEW` shipment.

## Output

Produce `docs/E2E-TEST-REPORT.md` containing:
- A pass/fail table, one row per checklist item above
- Screenshots or console-error excerpts for anything that failed (if
  browser automation tooling is available; otherwise a clear text
  description of the failure)
- A final **"Production Ready: Yes/No"** verdict
- If "No," a clearly separated **"Blocking Issues"** list — the specific
  features that must be fixed before this is demo-ready

## Rules
- Do not fix issues automatically during this pass — this is verification
  only. Report findings, then wait for review before making changes.
- Test using the actual live URLs from `docs/DEPLOYMENT-LOG.md`, not
  localhost and not mock data — the whole point of this unit is to catch
  what only shows up in the real deployed environment.
