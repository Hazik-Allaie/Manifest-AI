---
name: unit-09-ensemble-embeddings
description: Add 3rd extraction method + weighted voting (#8) and embeddings fallback (#2)
---

## Goal
Upgrade the comparator from 2 methods to 3 (regex, OCR+NER, LLM) with
weighted voting, and add a semantic embeddings fallback for labels the
synonym dictionary (`unit-03`) doesn't recognize.

## Prerequisite
`unit-08-vision-extraction.md` complete.

## Steps
1. In `matching/ensemble_voter.py`, add a third independent extraction
   method (OCR + NER) alongside the existing regex and LLM methods.
2. Implement weighted voting: when the 3 methods disagree on a field value,
   combine them (weighted by historical per-method reliability) rather than
   picking one arbitrarily. Disagreement itself should lower the field's
   confidence score, feeding into `unit-05`'s router.
3. In `matching/embeddings.py`, add a Vertex AI `text-embedding-004` lookup:
   when `unit-03`'s dictionary returns `None` for a label, embed it and find
   the closest known field label by cosine similarity. Borderline scores
   should route to `NEEDS_REVIEW` rather than guessing.

## Test
Re-run the full pipeline against `local-server/data-advanced/`. Compare the
`score_cli.py` result against the Unit 7 baseline score.

## Exit Criteria
- Score improves versus the Unit 7 baseline.
- No new crash classes introduced.

## Next
Move to `unit-10-escalation-feedback.md`.
