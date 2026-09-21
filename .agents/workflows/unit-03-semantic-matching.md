---
name: unit-03-semantic-matching
description: Build the synonym-dictionary field matcher (#2, dictionary tier only)
---

## Goal
Map differently-labeled fields (e.g. "Load Port" vs "Port of Loading") to
canonical field names, using a hardcoded dictionary. Embeddings fallback
comes later (`unit-09`).

## Prerequisite
`unit-02-text-extraction.md` complete.

## Steps
1. In `matching/synonym_dict.py`, build a dictionary mapping known raw labels
   to canonical field names, e.g.:
   `"Load Port": "port_of_loading"`, `"To the Order of": "consignee"`,
   `"Gross Wt (kgs)": "gross_weight_kg"`.
2. Pull real synonym examples from
   `local-server/data-advanced/README.md` (§ "Attachments") — it explicitly
   documents the label variants used in the dataset.
3. Write a lookup function: given a raw label, return the canonical field
   name, or `None` if unrecognized (unrecognized labels are handled in
   `unit-09`, not here).

## Test
Feed it 15+ known synonym pairs from the dataset README. Confirm every one
resolves to the correct canonical field name.

## Exit Criteria
- All documented synonym pairs from the dataset README resolve correctly.

## Next
Move to `unit-04-comparator.md`.
