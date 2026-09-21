---
name: unit-04-comparator
description: Build the field comparator with fuzzy matching (#8, 2-method tier)
---

## Goal
Compare SI vs BL field values (already run through `unit-03`'s matcher)
without false-flagging trivial formatting differences as mismatches.

## Prerequisite
`unit-03-semantic-matching.md` complete.

## Steps
1. In `matching/ensemble_voter.py` (comparator portion), write a function
   that takes two `ExtractionResult`s (SI + BL) and returns a
   `ComparisonResult` (see `shared/schemas/`).
2. Before flagging a mismatch, normalize and fuzzy-match string values (e.g.
   trim whitespace, case-fold, Levenshtein distance) so "Singapore" vs
   "SINGAPORE " vs "Singapore Port" are recognized as the same value.
3. Only flag a real mismatch when values genuinely differ after
   normalization.

## Test
Run against 10 SI/BL pairs with **known** injected defects — check
`local-server/data-advanced/ground_truth.json` yourself, manually, to verify
correctness. Do **not** wire `ground_truth.json` into any pipeline code.

## Exit Criteria
- Zero false-positive mismatches on the fuzzy-match test cases.
- Real injected defects are correctly caught.

## Next
Move to `unit-05-confidence-router.md`.
