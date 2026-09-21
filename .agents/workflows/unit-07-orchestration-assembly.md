---
name: unit-07-orchestration-assembly
description: Wire Units 1-5 into the real agent orchestration graph (#1, full)
---

## Goal
Replace the standalone functions from Units 1–5 with a connected LangGraph
(or CrewAI) agent pipeline, with retry logic and error recovery.

## Prerequisite
`unit-05-confidence-router.md` complete. (Unit 6 gate decision made, but
building this unit does not depend on that decision.)

## Steps
1. In `agents/orchestrator.py`, build the agent graph:
   Classifier → Extractor → Matcher → Comparator → Confidence Router.
2. Add retry logic: if any stage fails (e.g. API timeout, malformed JSON),
   retry 1–2 times before giving up.
3. Add error recovery: if a stage fails permanently, route that email
   straight to `NEEDS_REVIEW` rather than crashing the batch.
4. Add full pipeline logging per email (feeds the dashboard's Shipment
   Timeline later).

## Test
Run the full pipeline against all of `data-basic/`. Generate a
`submission.json`. Score it with `local-server/server/score_cli.py`.

## Exit Criteria
- Pipeline runs end-to-end on the full basic dataset with zero unhandled
  crashes.
- Score is recorded as the project's baseline (log it for the
  accuracy-over-time trend).

## Next
Move to `unit-08-vision-extraction.md`.
