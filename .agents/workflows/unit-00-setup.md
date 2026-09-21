---
name: unit-00-setup
description: Prerequisite setup for Manifest AI — must complete before Unit 1 begins
---

## Goal
Get the environment, cloud project, and shared schema ready before any pipeline
code is written.

## Steps
1. Confirm GCP project exists, all 5 teammates have Editor access, and these
   APIs are enabled: Vertex AI, Pub/Sub, Firestore, Cloud Run, Cloud Scheduler,
   Cloud Storage.
2. Confirm a billing budget alert is set.
3. Confirm the repo folder structure matches `docs/FOLDER-MAP.md`.
4. Create `shared/schemas/` and add the Pydantic models from
   `docs/ARCHITECTURE.md` §2 exactly as written — this file must not change
   casually once other units depend on it.
5. Run `python3 local-server/server/score_cli.py --help` (or equivalent) to
   confirm the scoring tool works.
6. `pip install -r requirements.txt`.

## Verification / Exit Criteria
- A trivial Vertex AI call succeeds.
- One email from `data-basic/inbox/` can be read via `sdk/loader.py`.
- `score_cli.py` runs against `sdk/sample_submission.json` without error
  (a low/meaningless score is fine — this only proves the tool works).

## Next
Once all criteria pass, move to `unit-01-classifier.md`.
