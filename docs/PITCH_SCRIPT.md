# Manifest AI — 5-Minute Pitch Video Script & Demo Guide

> ⏱️ **Target Duration**: 4 minutes 30 seconds (Hard maximum: 5:00 — going over costs 1 point per 30s).  
> 🖥️ **Screen Setup**:  
> - Browser Window 1: Manifest AI Production Dashboard (`http://localhost:8080`)  
> - Browser Window 2 / Terminal: Synthetic Failure Simulator (`http://localhost:8085` or CLI)  
> - Discord Window (optional): Real-time escalation webhook channel  

---

## Video Timeline & Script

### 0:00 – 0:45 | Introduction & The Multi-Billion Dollar Maritime Problem
- **Visual**: Presenter on camera or title slide with Manifest AI logo.
- **Narration**:
  > *"Every day, global container shipping moves trillions of dollars in cargo. Yet the entire industry relies on manual comparison of customer Shipping Instructions against carrier draft Bills of Lading arriving via messy operational emails.  
  > When a container count says 4 on the SI but 2 on the BL, or a gross weight differs by a few thousand kilograms, the result is customs holds, demurrage charges costing hundreds of dollars a day per container, and expensive manifest amendment penalties.  
  > Traditional OCR breaks across carrier formats, and basic matching tools overwhelm operators with false alarms.  
  > We built **Manifest AI**: an autonomous, enterprise-grade shipping document verification engine powered by Google Cloud and LangGraph that auto-clears clean shipments, catches discrepancies with 100% precision, and escalates true edge cases with explainable audit evidence."*

---

### 0:45 – 1:45 | Live Triage Command Center & Automated Processing
- **Visual**: Switch screen to Manifest AI Dashboard (`http://localhost:8080`). Show KPI bar and 3-column Kanban board (`Auto-Cleared`, `Discrepancy Found`, `Needs Review`).
- **Narration**:
  > *"Here is the Manifest AI Triage Command Center, running live. It has ingested 520 operational emails spanning digital PDFs, scanned documents, Word tables, and Excel sheets.  
  > Notice our headline metrics: an official benchmark score of **91.06%**, with **100.0% defect precision** — meaning zero false alarms.  
  > Out of 520 shipments, 454 were auto-cleared touchlessly — an 87% automation rate.  
  > Exactly 46 shipments were flagged with verified discrepancies in our middle column, and 20 ambiguous edge cases were escalated to human reviewers in our right column.  
  > Let's look at how the AI handles a real discrepancy."*

---

### 1:45 – 2:45 | Side-by-Side Discrepancy Inspection & One-Click Carrier Notice
- **Visual**: Click on `email_004` in the `Discrepancy Found` column. Show the side-by-side comparison drawer, highlighting the `consignee` difference in amber/yellow with source snippets. Show the shipment timeline.
- **Narration**:
  > *"Clicking into email_004, our inspector displays the extracted canonical fields side-by-side.  
  > Our 3-method ensemble voter cross-examined the document using table structure parsing, regex patterns, and Gemini multimodal vision. Notice how it immediately flags the discrepancy: the SI consignee is declared as 'Vital Solutions Singapore', but the draft BL manifests 'Vital Solutions Malaysia'.  
  > Every field includes explainable source snippets from the raw documents, and the shipment audit trail traces the lifecycle from email receipt to triage routing.  
  > Best of all, with one click on 'Draft Correction Email', Manifest AI automatically generates a complete, polite discrepancy notice citing the exact difference, ready for the reviewer to copy and dispatch to the carrier before vessel cut-off."*
- **Visual**: Click `Draft Correction Email`, show the formatted text, click `Copy to Clipboard`.

---

### 2:45 – 3:45 | Synthetic Failure Simulator (Proving Reliability Live)
- **Visual**: Switch to Failure Simulator Web Panel (`http://localhost:8085`) or terminal (`python -m tests.synthetic_failures.simulator`).
- **Narration**:
  > *"Judges often wonder: does the system really handle edge cases, or did it just get lucky on sample data?  
  > To prove reliability live, we built the **Synthetic Failure Simulator** — a demo testbed that injects any known failure on demand.  
  > Let's inject a corrupted, unreadable document. Clicking 'Inject Fault & Run Pipeline Live'..."*
- **Visual**: Click `Unreadable / Corrupted Document`, then click `Inject Fault & Run Pipeline Live`. Show the live pipeline executing through Classifier $\rightarrow$ Extractor $\rightarrow$ Router. Show the crimson `NEEDS_REVIEW` badge with `review_reason: unreadable` and `✓ TEST PASSED`.
- **Narration**:
  > *"In under 0.02 seconds, the pipeline intercepts the corrupt file, safely routes to `NEEDS_REVIEW` with the exact review reason 'unreadable', and logs an audit trail without crashing the pipeline.  
  > We can toggle wrong document types like Commercial Invoices, missing values, or container count mismatches. Our automated test runner verifies all 9 failure modes with a 100% pass rate."*

---

### 3:45 – 4:30 | Self-Improving Feedback Loop & Google Cloud Integration
- **Visual**: Switch back to Dashboard inspector. Show the `Operator Correction` modal. Enter a corrected value and click `Save to Firestore`.
- **Narration**:
  > *"Manifest AI is self-improving. When a reviewer corrects a field, the correction is saved directly to **Google Cloud Firestore**.  
  > With our high-throughput TTL cache, these verified corrections are dynamically injected as few-shot guidance into future Gemini 2.5 Flash extraction prompts, continuously adapting the model to new carrier quirks without expensive fine-tuning.  
  > In the background, real-time emails are streamed via **Google Cloud Pub/Sub** with an asynchronous worker pool and Dead-Letter Queues, backed by **Google Cloud Scheduler** for daily analytics digests."*

---

### 4:30 – 5:00 | Cloud Run Architecture & Summary
- **Visual**: Show `Dockerfile` and terminal showing `gcloud run services describe manifest-ai`, or the deployed Cloud Run URL.
- **Narration**:
  > *"The entire platform is containerized and deployed to **Google Cloud Run** in `asia-southeast1`, providing auto-scaling from 0 to 10 instances with sub-second response times and non-root security.  
  > To summarize:  
  > - **91.06% benchmark score** on 520 emails  
  > - **100% defect precision** — zero false alarms  
  > - **100% edge-case recall** — 20 out of 20 exceptions caught  
  > - **61 out of 61 pytest tests passing**  
  > Manifest AI turns a chaotic, manual maritime vulnerability into an automated, explainable, self-improving competitive advantage. Thank you!"*

---

## Pitch Checklist
- [ ] Ensure local dashboard is running (`python -m dashboard.server`)
- [ ] Ensure synthetic failure simulator is running (`python -m tests.synthetic_failures.simulator --web`)
- [ ] Check microphone audio levels
- [ ] Keep browser zoom at 100% or 110% for crisp legibility
- [ ] Rehearse to ensure timing stays within **4:30 – 4:50**
