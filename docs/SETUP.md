# SETUP — Manifest AI

Follow this once, as a team, before any unit in BUILD-ORDER.md begins.

## 1. Accounts & Access

- [ ] One person creates the GCP project: `manifest-ai` (or `manifest-ai-hackathon`)
- [ ] Add all 5 teammates as **Editor** in IAM
- [ ] Enable APIs: Vertex AI, Pub/Sub, Firestore, Cloud Run, Cloud Scheduler,
      Cloud Storage
- [ ] Set a billing budget alert (Vertex AI calls add up fast during testing)
- [ ] Pick one region (e.g. `asia-southeast1`) and use it everywhere

## 2. Repo

- [ ] Create the GitHub repo, push the existing folder structure
      (`data-basic/`, `local-server/`, `sdk/`)
- [ ] Add the new code folders: `shared/`, `agents/`, `extraction/`,
      `matching/`, `escalation/`, `dashboard/`, `infra/`, `tests/`, `docs/`
- [ ] Put PRD.md, TECHSTACK.md, ARCHITECTURE.md, DESIGN.md, BUILD-ORDER.md,
      this SETUP.md, and FOLDER-MAP.md into `docs/`
- [ ] Branch convention: `feature/<initial>-<module>`
      (e.g. `feature/b-vision-extraction`)

## 3. Local Environment (each teammate)

```bash
python3 -m venv venv
source venv/bin/activate          # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env              # fill in MANIFEST_GCP_PROJECT_ID etc.
gcloud auth application-default login
```

## 4. Verify the Toolkit Works

```bash
# read the dataset
python3 -c "from sdk.loader import Inbox; ib=Inbox('data-basic'); print(len(ib.emails()),'emails')"

# confirm offline scoring works
python3 local-server/server/score_cli.py sdk/sample_submission.json
```

Both should run without error (the score will be low/meaningless at this
point — that's expected, it's just a plumbing check).

## 5. Confirm Vertex AI Access

```python
from google.cloud import aiplatform
aiplatform.init(project="<your-project-id>", location="asia-southeast1")
# make one trivial Gemini call to confirm billing/auth is live
```

## 6. Team Coordination Setup

- [ ] Shared Discord/Slack channel (also used for #4's escalation webhook)
- [ ] Shared doc or `docs/` folder as the single source of truth for the
      schema — no one edits `shared/schemas/` without telling the team
- [ ] A shared score-tracking sheet: date/time, unit, `score_cli.py` result
      (this becomes your accuracy-over-time chart for the pitch video)

## 7. Antigravity / Stitch

- [ ] Point Antigravity at this repo and the `.md` files in `docs/` as its
      working context
- [ ] Confirm it acknowledges the **Unit 6 gate** from BUILD-ORDER.md before
      any dashboard work begins

## 8. Go/No-Go Check

Do not proceed to BUILD-ORDER.md Unit 1 until:
- [ ] Everyone can run the toolkit verification (§4) successfully
- [ ] `shared/schemas/` exists with the Pydantic models from ARCHITECTURE.md §2
- [ ] Everyone has read PRD.md and knows the exact submission schema
