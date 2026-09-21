---
name: unit-12-failure-simulator
description: Build the demo-only Synthetic Test / Failure Simulator panel
---

## Goal
A standalone tool that generates known failure types on demand and runs them
through the live pipeline, so judges can watch reliability proven live
instead of taking a successful example on faith.

## Prerequisite
`unit-11-realtime-architecture.md` complete (or skipped if time-boxed — this
unit only needs the Unit 7 pipeline to exist).

## Steps
1. In `tests/synthetic_failures/`, build a small script or panel with
   toggles for the 4 known failure types: wrong container count, wrong
   weight, missing BL, unreadable document, different field names, unit
   mismatch, wrong shipment ID.
2. Each toggle should generate or select a test case exhibiting that
   failure, run it through the pipeline, and display pass/fail against the
   expected `review_reason` or `defect_fields`.

## Test
Run all failure types, confirm each is caught with the correct outcome.

## Exit Criteria
- Works reliably enough to run live during the pitch video without
  surprises.

## Next
Move to `unit-13-final-integration.md`.
