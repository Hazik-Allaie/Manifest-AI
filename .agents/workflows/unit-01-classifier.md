---
name: unit-01-classifier
description: Build the minimal email classifier (#1, standalone function)
---

## Goal
A single function that classifies one email into one of the 5 required
categories, with evidence — no orchestration framework yet.

## Prerequisite
`unit-00-setup.md` complete.

## Steps
1. In `agents/classifier.py`, write a function that takes one email JSON
   record (see `data-basic/inbox/email_XXX.json` for the shape) and returns
   a `ClassificationResult` (see `shared/schemas/`).
2. Prompt Gemini with the 5 categories — `BL_COMPARISON`, `SI_REQUEST`,
   `INVOICE_QUERY`, `GENERAL`, `SPAM` — and require it to return evidence
   (which signals in the email led to this label), not just the label.
3. Validate every output against the `ClassificationResult` Pydantic schema.

## Test
Run against 20 sample emails from `data-basic/inbox/`. Manually eyeball the
categories against what a human would call them.

## Exit Criteria
- Categories look correct on the eyeballed sample.
- 100% of outputs validate against the schema with zero errors.

## Next
Move to `unit-02-text-extraction.md`.
