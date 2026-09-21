---
name: unit-02-text-extraction
description: Build plain-text extraction for SI/BL attachments (#3, text path only)
---

## Goal
Extract all 7 required fields from a **plain-text** SI or BL attachment, with
confidence and a source snippet per field. No PDF/DOCX/vision yet.

## Prerequisite
`unit-01-classifier.md` complete.

## Steps
1. In `extraction/text_parser.py`, write a function that takes raw text
   (from `sdk.loader.Inbox.read_text()`) and returns an `ExtractionResult`
   (see `shared/schemas/`) with all 7 fields: shipper, consignee,
   notify_party, port_of_loading, port_of_discharge, container_count,
   gross_weight_kg.
2. Each extracted field must include: the value, a confidence score, and the
   exact source line/sentence it came from (`source_snippet`).
3. Set `doc_status: "ok"` when extraction succeeds normally.

## Test
Run against 10 known plain-text SI/BL pairs in `data-basic/attachments/`.
Manually check extracted values against the raw `.txt` files.

## Exit Criteria
- All 7 fields extracted correctly on the plain-text sample.
- `doc_status` stays `"ok"` for genuinely fine documents.
- Output validates against the `ExtractionResult` schema.

## Next
Move to `unit-03-semantic-matching.md`.
