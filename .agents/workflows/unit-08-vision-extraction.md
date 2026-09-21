---
name: unit-08-vision-extraction
description: Extend extraction to PDF/DOCX/XLSX/scanned documents (#3, vision upgrade)
---

## Goal
Handle real binary document formats and scanned/unreadable documents
gracefully, without crashing the pipeline.

## Prerequisite
`unit-07-orchestration-assembly.md` complete and stable. Do not start this
unit while Unit 7 is still unstable — debugging two unstable layers at once
wastes time.

## Steps
1. In `extraction/vision_pipeline.py`, add document-type detection: route
   plain text to the existing `unit-02` parser, PDFs/scans to Gemini Vision,
   DOCX to `python-docx`, XLSX to `openpyxl`.
2. Handle multi-page documents — don't miss fields on page 2+.
3. Attach per-field confidence scores from the vision model's output.
4. Detect and handle the 3 "unreadable" failure modes explicitly:
   - image-only PDF with no text layer
   - empty 0-byte file
   - truncated/garbled PDF
   All three must set `doc_status: "unreadable"`, never crash.
5. Detect `wrong_doc_type` (e.g. the "BL" is actually a Commercial Invoice,
   Packing List, or Certificate of Origin) and set `doc_status` accordingly.

## Test
Run against `local-server/data-advanced/attachments/` — specifically the
`.pdf`, `.docx`, `.xlsx` files, and the edge cases built by
`local-server/data-advanced/generator/edgecases.py`.

## Exit Criteria
- No crashes on any binary format.
- All 3 unreadable variants correctly route to `NEEDS_REVIEW` instead of
  erroring out.

## Next
Move to `unit-09-ensemble-embeddings.md`.
