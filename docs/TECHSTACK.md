# TECHSTACK — Manifest AI

## 1. Cloud Platform

| Service | Purpose |
|---|---|
| Vertex AI (Gemini 2.0 Flash / 1.5 Pro) | Classification, extraction (text + vision), reasoning agents |
| Vertex AI `text-embedding-004` | Semantic field-label matching |
| Vertex AI Vector Search | Shipping-terminology vector store |
| Cloud Pub/Sub | Event-driven "new email" triggering |
| Cloud Firestore | Results, corrections log, escalation records, analytics data |
| Cloud Run | Hosting the dashboard backend/frontend + API |
| Cloud Scheduler | Polling fallback / daily digest trigger |
| Cloud Storage | SI/BL attachment storage (if not read from local `data-*` folders) |

**Region**: pick one and use everywhere (e.g. `asia-southeast1`).

## 2. Languages & Frameworks

- **Python 3.11+** — pipeline, agents, extraction, matching, scoring integration
- **LangGraph** (preferred) or **CrewAI** — agent orchestration (#1)
- **FastAPI** — dashboard backend API, if not using the organizer's `server/app.py` pattern
- **React + Tailwind** (or plain HTML/JS via Antigravity/Stitch) — dashboard frontend
- **Pydantic** — the shared data contract (schemas), used everywhere

## 3. Key Python Libraries

```
google-cloud-aiplatform
google-cloud-firestore
google-cloud-pubsub
google-cloud-storage
langgraph
pydantic
python-docx
openpyxl
pypdf
pdfplumber
python-Levenshtein
fastapi
uvicorn
```

## 4. Extraction Method Stack (feeds #8 Ensemble Voting)

| Method | Tooling |
|---|---|
| Rule-based / regex | Python `re`, custom label patterns from `pools.py` (organizer dataset) as reference |
| OCR + NER | `pdfplumber`/`pytesseract` for OCR, spaCy or a lightweight NER model |
| LLM-based | Gemini (text or vision) with structured JSON output prompting |

## 5. Repo Layout (already established, see FOLDER-MAP.md)

```
Manifest-AI/
├── data-basic/
├── local-server/
│   ├── data-advanced/
│   └── server/
├── sdk/
├── shared/            (schemas, config, utils — NEW, to be created)
├── agents/            (NEW)
├── extraction/        (NEW)
├── matching/          (NEW)
├── escalation/         (NEW)
├── dashboard/          (NEW — held for teammates, see BUILD-ORDER.md)
├── infra/              (NEW)
├── tests/              (NEW)
└── docs/               (this file lives here)
```

## 6. Environment Variables (`.env`)

```
MANIFEST_GCP_PROJECT_ID=
MANIFEST_GCP_REGION=asia-southeast1
MANIFEST_VERTEX_MODEL=gemini-2.0-flash
MANIFEST_FIRESTORE_DB=manifest-db
MANIFEST_PUBSUB_TOPIC=new-email-events
MANIFEST_DISCORD_WEBHOOK=
MANIFEST_DATASET_PATH=./data-basic
MANIFEST_ADVANCED_DATASET_PATH=./local-server/data-advanced
MANIFEST_SELF_EVAL_SCRIPT=./local-server/server/score_cli.py
```

## 7. Why These Choices

- **LangGraph over a hand-rolled loop**: gives retry/state-handoff for free,
  and it's a genuine "agentic AI" architecture judges can see in the code.
- **Gemini for both text and vision**: one model family handles clean text,
  PDFs, and scanned images — avoids stitching together 3 separate OCR/NLP
  systems under time pressure.
- **Firestore over a SQL DB**: schema-flexible, zero-setup, integrates
  natively with Cloud Functions/Pub-Sub, fast enough for hackathon scale.
- **score_cli.py as primary dev-loop tool**: instant offline scoring beats
  spinning up Docker every iteration; Docker server is reserved for testing
  the real-time/HTTP flow only.
