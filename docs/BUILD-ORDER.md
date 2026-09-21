# BUILD-ORDER — Manifest AI

## 0. Governing Workflow Rule

**Build one unit → test that unit in isolation → only then move to the next
unit → integrate → test the integration → repeat.** No unit is considered
"done" until it passes its own test, using real sample data from
`data-basic/` (and later `local-server/data-advanced/`). This is how we avoid
a broken pile of half-integrated modules on Day 3.

Each unit below states: what it is, its test, and its exit criteria before
moving on.

---

## Unit 0 — Prerequisite Setup (do this first, nothing else until it's done)

1. Create GCP project, enable: Vertex AI API, Pub/Sub API, Firestore API,
   Cloud Run API, Cloud Scheduler API, Cloud Storage API.
2. Add all 5 teammates as Editors.
3. Set a billing budget alert.
4. Clone/create the repo with the folder structure from TECHSTACK.md §5.
5. Create `shared/schemas/` and paste in the Pydantic models from
   ARCHITECTURE.md §2 — **this file must not change casually once other
   units depend on it.**
6. Confirm `python3 local-server/server/score_cli.py --help` runs (or
   equivalent) — this is your scoring tool for every unit test from here on.
7. `pip install -r requirements.txt` (see TECHSTACK.md §3).

**Exit criteria**: everyone can run a "hello world" Vertex AI call, read one
email from `data-basic/`, and run `score_cli.py` against
`sample_submission.json` (it will score low — that's fine, this just proves
the tool works).

---

## Unit 1 — Classifier (#1, minimal)

**Build**: a single function that takes one email JSON record and returns a
`ClassificationResult`. Prompt Gemini with the 5 categories + ask for
evidence. No orchestration framework yet — just the function.

**Test**: run it against 20 sample emails from `data-basic/inbox/`, manually
eyeball the categories. Confirm output matches the `ClassificationResult`
schema exactly.

**Exit criteria**: classifies correctly on an eyeballed sample; output
validates against the Pydantic schema with zero errors.

---

## Unit 2 — Text Extraction (#3, plain-text path only)

**Build**: a function that takes an SI or BL **plain-text** attachment and
returns an `ExtractionResult` with all 7 fields + confidence + source
snippet. No vision/PDF/DOCX yet.

**Test**: run against 10 known plain-text SI/BL pairs from `data-basic/`.
Manually check extracted values against the raw text.

**Exit criteria**: all 7 fields extracted correctly on plain-text samples;
`doc_status` correctly stays `"ok"` when the doc is genuinely fine.

---

## Unit 3 — Semantic Field Matching (#2, dictionary tier only)

**Build**: the hardcoded synonym dictionary (`"Load Port": "port_of_loading"`,
etc.) that maps raw labels found during extraction to canonical field names.

**Test**: feed it 15+ known synonym pairs (see `local-server/data-advanced/README.md`
§"Attachments" for real examples used in the dataset). Confirm correct
mapping.

**Exit criteria**: dictionary correctly resolves all documented synonym pairs
from the dataset README.

---

## Unit 4 — Comparator + Fuzzy Match (#8, 2-method tier)

**Build**: takes two `ExtractionResult`s (SI + BL) already through Unit 3's
matcher, compares field-by-field. Include fuzzy/normalize logic ("Singapore"
vs "SINGAPORE " should match) before flagging a real mismatch.

**Test**: run against 10 SI/BL pairs with **known** injected defects (check
`ground_truth.json` yourself, manually, to verify — never wire this into the
pipeline). Confirm mismatches are found and non-defects aren't false-flagged.

**Exit criteria**: zero false-positive mismatches on the fuzzy-match test
cases; real defects correctly caught.

---

## Unit 5 — Confidence Router + Missing/Unreadable Handling (#4, core logic)

**Build**: the routing rule from ARCHITECTURE.md §3 — `NEEDS_REVIEW` handling
for missing attachments, unreadable docs, wrong doc type, missing values,
**before** any value comparison happens.

**Test**: run against the **20 labeled edge cases** in
`local-server/data-advanced/inbox/email_501`–`email_520`. Score with
`score_cli.py`. This is your best available ground-truth-adjacent test since
these are explicitly documented in the dataset README.

**Exit criteria**: correctly assigns `review_reason` for all/most of the 20
edge cases; a blank field is never reported as `MISMATCH`.

---

## Unit 6 — Dashboard (#6) — ⚠️ GATED UNIT, requires your go-ahead

**Before starting this unit, Antigravity must stop and ask:**

> "Unit 6 (Dashboard) is next. Should I build this now, or is this the part
> going to your teammates? If you say no, I'll mark it PENDING and move to
> Unit 7, and pick it back up only when you hand me their finished work for
> integration."

- If **yes**: build DESIGN.md's spec against the mock JSON in DESIGN.md §3.
- If **no**: skip to Unit 7. Mark Unit 6 status as `PENDING — externally
  built`. Do not build any part of it.

**When the teammates' work is later handed over**, run the **Integration
Evaluation Protocol** (see §Integration Evaluation below) before merging —
regardless of how much time has passed.

---

## Unit 7 — Orchestration Assembly (#1, full)

**Build**: wire Units 1–5 together into the real LangGraph/CrewAI pipeline
with retry logic and error recovery. This replaces the standalone functions
from earlier units with a connected agent graph.

**Test**: run the full pipeline against all of `data-basic/`. Generate a
`submission.json`, score with `score_cli.py`.

**Exit criteria**: pipeline runs end-to-end on the full basic dataset with
zero unhandled crashes; score is recorded as your baseline.

---

## Unit 8 — Vision Extraction (#3, PDF/DOCX/scanned upgrade)

**Build**: extend Unit 2's extractor with document-type detection routing to
Gemini Vision for PDFs/scans, `python-docx`/`openpyxl` for DOCX/XLSX.

**Test**: run against `local-server/data-advanced/attachments/` — specifically
the `.pdf`, `.docx`, `.xlsx` files, and the 3 `unreadable`-type edge cases
(image-only PDF, empty file, garbled PDF).

**Exit criteria**: no crashes on any binary format; unreadable docs correctly
route to `NEEDS_REVIEW` instead of erroring out.

---

## Unit 9 — Ensemble Voting (#8, 3-method upgrade) + Embeddings (#2, fallback tier)

**Build**: add the 3rd extraction method (OCR+NER) and weighted voting; add
Vertex AI embeddings as the fallback when the synonym dictionary (Unit 3)
doesn't recognize a label.

**Test**: re-run the full `data-advanced/` set, compare score against Unit 7's
baseline — confirm improvement, not regression.

**Exit criteria**: score improves vs. baseline; no new crash classes
introduced.

---

## Unit 10 — Escalation Notifications + Feedback Loop (#4 notify, #5)

**Build**: wire real Discord/webhook notification on `NEEDS_REVIEW`; build
correction logging to Firestore + few-shot injection into future prompts.

**Test**: manually trigger 3 escalations, confirm notifications fire with
correct evidence; submit 3 fake corrections, confirm they show up in
Firestore and influence a subsequent run.

**Exit criteria**: notification delivery confirmed; correction logging
confirmed; measurable prompt behavior change after injection.

---

## Unit 11 — Real-Time Architecture (#7)

**Build**: Pub/Sub topic + subscriber wrapping the Unit 7 pipeline; Cloud
Scheduler fallback/digest trigger.

**Test**: publish 3 test messages, confirm the pipeline reacts without manual
triggering.

**Exit criteria**: pipeline reacts to a published event within the demo's
acceptable latency (seconds, not minutes).

---

## Unit 12 — Synthetic Test / Failure Simulator (demo tool)

**Build**: a small standalone panel/script that generates the 4 known failure
types on demand and runs them through the live pipeline, showing pass/fail.

**Test**: run all 4 types, confirm each is caught with the correct
`review_reason`.

**Exit criteria**: works reliably enough to run live during the pitch video
without surprises.

---

## Unit 13 — Final Integration + Polish

- Full run against `data-advanced/`, final `score_cli.py` check.
- Deploy to Cloud Run.
- Merge Unit 6 (dashboard) if not already integrated — run the Integration
  Evaluation Protocol below if it came from teammates.
- Record pitch video, write README + written responses, submit.

---

## Integration Evaluation Protocol (for any externally-built unit, esp. #6)

When teammate-built code is handed over, before merging into the main branch:

1. **Schema check** — does every input/output match the Pydantic schemas in
   `shared/schemas/`? Reject/flag anything that invented its own shape.
2. **Smoke test** — does it run at all against the mock JSON (DESIGN.md §3)
   and, if ready, real pipeline output?
3. **Breakage check** — run the full pipeline test suite (Units 1–11's tests)
   after merging; confirm nothing that worked before now fails.
4. **Feature checklist** — cross-check against DESIGN.md §2's view list;
   flag anything missing or partially built.
5. **Report back** — a short pass/fail summary per feature, with specific
   fixes needed if something doesn't align, before it's considered merged.

Antigravity should run this protocol automatically whenever code is
introduced for a unit previously marked `PENDING — externally built`, without
needing to be re-asked.

---

## Additional Suggestions for Success

- **Freeze `shared/schemas/` after Unit 0.** Any change to it after Unit 1
  starts must be a deliberate, announced decision — this is the #1 cause of
  late-stage integration breakage.
- **Run `score_cli.py` after every unit from Unit 5 onward**, not just at the
  end — track the score in a simple log so you have the "60% → 89%" story
  for your pitch video for free.
- **Keep a running `KNOWN-ISSUES.md`** — anything you knowingly skip or
  simplify goes here, so your written responses/pitch can honestly say "here's
  our roadmap" instead of pretending it's not a gap.
- **Don't start Unit 8 (Vision) before Unit 7 (orchestration) is stable.**
  Vision debugging is slow; you don't want to debug two unstable layers at
  once.
- **Time-box Units 9–12.** They're valuable but not required — if you're
  behind schedule by Day 3 morning, skip straight to Unit 13 with whatever
  you have.
