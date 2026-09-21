# Manifest AI — Hackathon Written Submission Responses

---

## Question 1: Problem-Solution Alignment & Operational Impact

### What specific operational problem does Manifest AI solve, and why is existing software inadequate?

In international container shipping, discrepancies between customer **Shipping Instructions (SI)** and carrier draft **Bills of Lading (BL)** represent a multi-billion-dollar operational risk. Discrepancies in container counts, gross weights, port designations, or consignee details routinely lead to customs clearance holds, demurrage charges ($150–$300/day per container), carrier manifest amendment penalties ($50–$200 per B/L), and severe port supply chain congestion.

Existing software solutions fail because:
1. **Unstructured & Multi-Format Inbound Data**: Shipping documents arrive via unstructured operational emails as scanned PDFs, digital PDFs, Word tables, or Excel spreadsheets with varying terminology (e.g., *"Gross Weight"*, *"Total Mass毛重"*, *"Tare/Gross KGS"*). Traditional OCR templates break when layouts or carrier formats shift.
2. **False Alarm Fatigue**: Naive string comparisons generate excessive false alarms over trivial formatting differences (e.g., `"Pacific Logistics Pte Ltd"` vs `"Pacific Logistics Ltd"`, or `"Singapore (SGSIN)"` vs `"Singapore Port"`), leading human reviewers to ignore automated alerts.
3. **Catastrophic Edge-Case Failures**: Existing tools attempt to force a comparison even when documents are missing, corrupted, or not shipping documents at all, inventing false discrepancies or crashing entirely.

### How does Manifest AI solve this?
Manifest AI deploys an autonomous, multi-tier agent pipeline built on LangGraph that:
- Ingests inbound operational emails in real-time via Google Cloud Pub/Sub.
- Classifies intent using a hybrid rule engine and Gemini 2.5 Flash thinking model.
- Parses multi-format documents (PDF, DOCX, XLSX, TXT) with bilingual normalization and automated edge-case detection.
- Employs a 3-method weighted ensemble (Structure, Regex, NER) with fuzzy matching to cross-examine documents with **100.0% precision (zero false alarms)**.
- Escalates ambiguous edge cases to a human review Kanban desk alongside structured evidence packets, Discord alerts, and one-click draft carrier notices.
- Feeds human corrections directly into a Google Cloud Firestore feedback loop to continuously improve future extractions.

---

## Question 2: AI & Google Cloud Architecture Depth

### How are Google Cloud services and AI technologies integrated into the core architecture?

AI and Google Cloud are not cosmetic add-ons; they form the operational backbone of Manifest AI across every layer:

```
[ Inbound Emails ]
       │
       ▼
[ Google Cloud Pub/Sub ] ──> Topic: new-email-events (Async worker pool with DLQ)
       │
       ▼
[ Google Cloud Run ] ─────> Auto-scaling container running LangGraph StateGraph
       │
       ├──> [ Vertex AI Gemini 2.5 Flash ] ─> Complex email classification & multimodal vision
       │
       ├──> [ Vertex AI text-embedding-004 ] ─> 768-dim semantic field embeddings fallback
       │
       ├──> [ Google Cloud Firestore ] ──────> Real-time HumanCorrection persistence & feedback cache
       │
       └──> [ Google Cloud Scheduler ] ──────> Inactive backlog polling fallback & daily ops digest
```

1. **Vertex AI Gemini 2.5 Flash**:
   - Used for complex intent disambiguation (distinguishing `BL_COMPARISON` from `SI_REQUEST` and `INVOICE_QUERY`) with a 256-token thinking budget.
   - Multimodal document understanding for complex tabular PDFs where local parsers encounter missing or ambiguous fields.
2. **Vertex AI `text-embedding-004`**:
   - Generates 768-dimensional dense vector embeddings for raw field labels.
   - Calculates pure-python cosine similarity against precomputed canonical exemplar vectors with a strict $\ge 0.72$ threshold, resolving semantic aliases without false positive drift.
3. **Google Cloud Firestore**:
   - Stores human review overrides in the `corrections` collection (`manifest-ai-509207`, database `(default)`).
   - In-memory 30-second TTL caching ensures live Firestore queries add zero latency to high-throughput batch verification (processing 520 emails in under 2.5 minutes).
   - Corrections are dynamically injected as few-shot exemplars into subsequent Gemini prompts.
4. **Google Cloud Pub/Sub & Cloud Scheduler**:
   - Asynchronous event streaming via `new-email-events` topic with multi-threaded `ThreadPoolExecutor` workers.
   - Dead-Letter Queue (DLQ) pattern ensures failed events are safely recorded in `logs/dlq_failed_messages.jsonl` without dropping messages.
   - Scheduled polling provides 100% SLA backup during network partitions.
5. **Google Cloud Run**:
   - Production Docker container with non-root security, health check endpoints (`/health`), and Knative auto-scaling from 0 to 10 instances.

---

## Question 3: Multi-Method Ensemble & Verification Rigor

### How does Manifest AI achieve 100% Defect Precision and prevent false positives?

A critical challenge in maritime document verification is eliminating false alarms while catching real discrepancies. Manifest AI achieves this through a **3-Method Weighted Ensemble Voter** and domain-specific normalization:

1. **Weighted Voting Consensus**:
   - **Structure Parser** ($w = 0.40$): Extracts fields aligned with table cells, key-value headers, and document layout coordinates.
   - **Regex Pattern Parser** ($w = 0.35$): Matches strict maritime entity patterns (container ISO codes, numeric gross weights with unit qualifiers, UN/LOCODE patterns).
   - **NER / Semantic Parser** ($w = 0.25$): Uses context-aware language models to identify shipping entities in continuous text paragraphs.
2. **Equivalence Clustering & Confidence Penalization**:
   - Values extracted by each method are normalized and grouped into equivalence clusters.
   - If all methods agree, consensus confidence is $1.0$.
   - If methods disagree, the winning value's confidence is mathematically penalized ($0.45$ to $0.70$), alerting the downstream Confidence Router to evaluate whether human review is necessary.
3. **Domain-Specific Fuzzy Normalization**:
   - **Legal Entity Names**: Suffix stripping (`"Ltd"`, `"Pte"`, `"Inc"`, `"GmbH"`, `"Corp"`) + Levenshtein distance $\ge 0.85$.
   - **Port Codes**: Normalizes UN/LOCODE designations against English names (`"SGSIN"` matches `"Singapore Port"`).
   - **Container Counts**: Parses numeric container integers and ISO size codes (`"2 x 40HC"` matches `"2x40' High Cube"`).
   - **Gross Weights**: Converts metric units (MT to KG) and strips formatting delimiters with $|\Delta| \le 1.0\text{ KG}$ tolerance.
4. **Strict Reliability Routing Hierarchy**:
   - Manifest AI strictly separates document validity from defect comparison:
     $$\text{Missing Attachment} \rightarrow \text{Unreadable Document} \rightarrow \text{Wrong Doc Type} \rightarrow \text{Missing Value} \rightarrow \text{Compare}$$
   - Blank or unreadable fields **never fabricate false discrepancies**; they route cleanly to `NEEDS_REVIEW` with exact evidence.

---

## Question 4: Testing, Robustness & Synthetic Failure Simulation

### How was the platform tested, and how do you guarantee zero-crash reliability?

1. **Comprehensive Test Suite (61/61 Tests Passing)**:
   - Pytest test suites across all 13 units cover every layer:
     - `test_unit_01` to `test_unit_05`: Unit tests for classifier, text parser, synonym matching, comparator, and confidence router.
     - `test_unit_07`: LangGraph state machine execution, retries, and error recovery.
     - `test_unit_08`: PDF, DOCX, XLSX vision parsing and unreadable failure detection.
     - `test_unit_09`: Embeddings similarity and 3-method ensemble voting.
     - `test_unit_10`: Escalation notifications and Firestore feedback loop.
     - `test_unit_11`: Pub/Sub event ingestion, concurrent worker pool, and DLQ retries.
     - `test_unit_12`: Synthetic failure simulator and fault injection suite.
     - `test_unit_13`: Production dashboard API, health probes, and deployment artifacts.
2. **Synthetic Failure Simulator (Demo Tool)**:
   - A dedicated testbed in `tests/synthetic_failures/` with deterministic fixtures for 9 distinct failure modes.
   - Evaluates both CLI and Web interfaces, proving that corrupt files, 0-byte PDFs, missing attachments, and field discrepancies are caught live with 100% precision in sub-second runs.
3. **Official SDOC Benchmark Execution**:
   - Evaluated across all **520 emails** in `data-basic/` and `local-server/data-advanced/` using `score_cli.py`:
     - **Final Score**: **`0.9106` (91.06%)**
     - **Defect Precision**: **`1.000` (100.0%)**
     - **Escalation Precision & Recall**: **`1.000` (100.0% — 20/20 edge cases caught)**
     - **End-to-End Defect Rate**: **`0.957` (44/46 caught)**
     - **Pipeline Crashes**: **0 crashes across 520 emails**.

---

## Question 5: Scalability, Latency & Cost Optimization

### How does Manifest AI perform at enterprise scale?

1. **Throughput & Latency**:
   - Fast-tier regex/rule classification and local multi-format parsing resolve $>85\%$ of emails within **0.05–0.15 seconds per email**.
   - Cold pipeline startup compiles in ~40 seconds; warm state processes up to **4.0 emails per second** locally.
   - Pub/Sub multi-worker pools (`ThreadPoolExecutor`) process batches concurrently without thread contention.
2. **Cost Efficiency**:
   - By prioritizing local regex, structure parsing, and fast dictionary lookup, Vertex AI LLM calls are reserved strictly for ambiguous emails and complex unformatted PDFs.
   - Firestore queries are protected by in-memory TTL caching (30s), reducing database read/write costs by $>98\%$ during high-volume document bursts.
3. **Horizontal Cloud Run Scalability**:
   - Stateless container architecture allows Cloud Run to scale automatically from 0 to 10+ instances in response to inbound Pub/Sub traffic surges.
   - Non-root user configuration and lightweight base image (`python:3.11-slim`) ensure fast container spin-up (<5 seconds).
