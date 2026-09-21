---
name: unit-05-confidence-router
description: Build the confidence router and NEEDS_REVIEW / review_reason logic (#4, core)
---

## Goal
Correctly route missing, unreadable, wrong-doc-type, and blank-value cases to
`NEEDS_REVIEW` with the right `review_reason` — **before** any value
comparison happens. This is one of the highest-priority correctness rules in
the whole project: a blank field must never be reported as `MISMATCH`.

## Prerequisite
`unit-04-comparator.md` complete.

## Steps
1. In `escalation/confidence_router.py`, implement this exact rule order
   (see `docs/ARCHITECTURE.md` §3):
   ```
   if doc_status == "missing"        → NEEDS_REVIEW, review_reason=missing_attachment
   if doc_status == "unreadable"     → NEEDS_REVIEW, review_reason=unreadable
   if doc_status == "wrong_doc_type" → NEEDS_REVIEW, review_reason=wrong_doc_type
   if any required field is null/blank → NEEDS_REVIEW, review_reason=missing_value
   else → compare normally → OK or MISMATCH
   ```
2. Output a `SubmissionEntry` (see `shared/schemas/`) matching the exact
   required submission shape.

## Test
Run against the **20 labeled edge cases** in
`local-server/data-advanced/inbox/email_501`–`email_520`. Score the result
with `local-server/server/score_cli.py`.

## Exit Criteria
- Correctly assigns `review_reason` for all/most of the 20 edge cases.
- A blank field is never reported as `MISMATCH` in any test case.

## Next
Move to `unit-06-dashboard.md` — **but read its gate instructions first.**
