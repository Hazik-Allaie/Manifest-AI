# FOLDER-MAP — Manifest AI

Reference for Antigravity and any teammate — what each folder is and is not
for.

```
Manifest-AI/
│
├── data-basic/                  Plain-text starter dataset (Basic mode).
│   ├── attachments/             SI/BL .txt pairs
│   └── inbox/                   email_XXX.json records
│
├── local-server/                Organizer delivery kit (full, incl. scoring).
│   ├── data-advanced/           520-email realistic dataset (Advanced mode).
│   │   ├── attachments/         Mixed txt/pdf/docx/xlsx SI/BL pairs
│   │   ├── generator/           Dataset-generation source — NOT used by our
│   │   │                        pipeline, reference only (edgecases.py is
│   │   │                        useful reading to understand failure modes)
│   │   ├── inbox/                500 main + 20 labeled edge cases
│   │   │                        (email_501–email_520)
│   │   ├── ground_truth.json    ⚠️ NEVER read by pipeline code. Reference/
│   │   │                        scoring only, via score_cli.py.
│   │   ├── README.md            Full dataset schema documentation
│   │   └── sample_submission.json
│   ├── server/                  FastAPI scoring engine.
│   │   ├── app.py               Serves data + /submit endpoint
│   │   ├── scoring.py           Scoring logic (shared by CLI + server)
│   │   ├── score_cli.py         ⭐ Primary dev-loop scoring tool
│   │   ├── loader.py            Same Inbox() interface as sdk/loader.py
│   │   └── make_bundle.py       Organizer tool — not needed by us
│   ├── docker-compose.yml       Only needed to test live HTTP /submit flow
│   └── README.md                Delivery-kit documentation
│
├── sdk/                         Participant toolkit (basic tier).
│   ├── loader.py                `from sdk.loader import Inbox`
│   ├── README.md                Official submission-format spec (authoritative)
│   └── sample_submission.json
│
├── shared/                      🔒 Frozen after Unit 0 — the data contract.
│   ├── schemas/                 Pydantic models (see ARCHITECTURE.md §2)
│   ├── config.py
│   └── utils.py
│
├── agents/                      Person A — #1 Orchestration
│   ├── orchestrator.py
│   └── classifier.py
│
├── extraction/                  Person B — #3 Extraction
│   ├── vision_pipeline.py
│   └── text_parser.py
│
├── matching/                    Person C — #2 Matching + #8 Ensemble
│   ├── synonym_dict.py
│   ├── embeddings.py
│   └── ensemble_voter.py
│
├── escalation/                  Person D — #4 Confidence Escalation
│   ├── confidence_router.py
│   └── notifier.py
│
├── dashboard/                   Person D + teammates — #6 (GATED, see
│   ├── frontend/                BUILD-ORDER.md Unit 6)
│   └── backend/
│
├── infra/                       Person E — #7 Real-time + #5 Feedback Loop
│   ├── pubsub_setup.py
│   ├── firestore_schema.py
│   └── cloud_functions/
│
├── tests/
│   └── synthetic_failures/      Unit 12 — Failure Simulator
│
└── docs/                        All .md files — PRD, TECHSTACK, ARCHITECTURE,
                                  DESIGN, BUILD-ORDER, SETUP, this file.
```

## Quick Decision Table

| "I need to..." | Go to |
|---|---|
| Read/understand the problem | `docs/PRD.md` |
| Pick a library or cloud service | `docs/TECHSTACK.md` |
| Know what shape data should be | `docs/ARCHITECTURE.md` §2 |
| Know what to build next | `docs/BUILD-ORDER.md` |
| Build the dashboard | `docs/DESIGN.md` (only after Unit 6 gate clears) |
| Set up my machine | `docs/SETUP.md` |
| Understand the real dataset's edge cases | `local-server/data-advanced/README.md` |
| Score my submission | `local-server/server/score_cli.py` |
