"""
agents/orchestrator.py — LangGraph Agent Pipeline Orchestration (Unit 7).

Wires Units 1–5 into a resilient agent graph:
  [START]
     │
     ▼
  classifier_node
     │
     ├── category != BL_COMPARISON ──────────────────┐
     │                                               │
     └── category == BL_COMPARISON                   │
           │                                         │
           ▼                                         │
     extractor_node                                  │
           │                                         │
           ├── unreadable / wrong_doc / missing ─────┤
           │                                         │
           └── clean SI + BL                         │
                 │                                   │
                 ▼                                   │
           comparator_node                           │
                 │                                   │
                 ▼                                   │
           router_node ◄─────────────────────────────┘
                 │
                 ▼
               [END]

Features:
  - Transient retry logic with exponential backoff
  - Error isolation: permanently failed stages escalate to NEEDS_REVIEW
  - Structured timeline event logging per email
  - Submission generation conforming to SubmissionEntry schema
"""

import time
import logging
from datetime import datetime, timezone
from typing import TypedDict, Optional, Literal, Any
from pathlib import Path
import json

from langgraph.graph import StateGraph, START, END

from shared.schemas import (
    ClassificationResult,
    ExtractionResult,
    ComparisonResult,
    SubmissionEntry,
)
from agents.classifier import classify_email
from extraction.text_parser import parse_text_document
from matching.ensemble_voter import compare_extractions
from escalation.confidence_router import (
    load_and_extract_attachment,
    route_decision,
    build_escalation_evidence_for_route,
)
from escalation.notifier import send_escalation_notification
from matching.synonym_dict import CANONICAL_FIELDS

logger = logging.getLogger(__name__)


# ── Pipeline State ────────────────────────────────────────────────────────

class PipelineState(TypedDict):
    email_id: str
    email: dict
    dataset_source: str
    classification: Optional[ClassificationResult]
    extractions: dict[str, ExtractionResult]
    comparison: Optional[ComparisonResult]
    submission_entry: Optional[SubmissionEntry]
    timeline_logs: list[dict]
    error: Optional[str]


def create_timeline_event(stage: str, status: str, details: Any = None) -> dict:
    """Create a structured timeline audit event."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "status": status,
        "details": details,
    }


# ── Graph Nodes ───────────────────────────────────────────────────────────

def classifier_node(state: PipelineState) -> dict:
    """Classify email record with retries and failure containment."""
    email = state["email"]
    email_id = state["email_id"]
    timeline = list(state.get("timeline_logs", []))
    timeline.append(create_timeline_event("classifier", "started"))

    # If classification was already injected / cached (e.g. testing)
    if state.get("classification") is not None:
        clf = state["classification"]
        timeline.append(create_timeline_event("classifier", "completed", clf.category))
        return {"classification": clf, "timeline_logs": timeline}

    # Execute with retry logic (max 2 retries)
    last_error = None
    for attempt in range(3):
        try:
            clf = classify_email(email)
            timeline.append(create_timeline_event("classifier", "completed", {
                "category": clf.category,
                "confidence": clf.confidence,
                "attempt": attempt + 1,
            }))
            return {"classification": clf, "timeline_logs": timeline}
        except Exception as e:
            last_error = e
            logger.warning("Classifier error on %s (attempt %d/3): %s", email_id, attempt + 1, e)
            time.sleep(0.5 * (attempt + 1))

    # Error recovery: fallback to GENERAL with error recorded
    logger.error("Classifier permanently failed for %s: %s", email_id, last_error)
    fallback_clf = ClassificationResult(
        email_id=email_id,
        category="GENERAL",
        evidence=[f"Classification failed permanently: {last_error}"],
        confidence=0.0,
    )
    timeline.append(create_timeline_event("classifier", "failed", str(last_error)))
    return {
        "classification": fallback_clf,
        "timeline_logs": timeline,
        "error": f"classifier_failure: {last_error}",
    }


def route_after_classifier(state: PipelineState) -> str:
    """Conditional edge after classifier_node."""
    if state.get("error") is not None:
        return "router"

    clf = state.get("classification")
    if clf and clf.category == "BL_COMPARISON":
        return "extractor"
    return "router"


def extractor_node(state: PipelineState) -> dict:
    """Extract fields from all attachments."""
    email_id = state["email_id"]
    email = state["email"]
    dataset_source = state["dataset_source"]
    timeline = list(state.get("timeline_logs", []))
    timeline.append(create_timeline_event("extractor", "started"))

    extractions: dict[str, ExtractionResult] = {}
    try:
        for att in email.get("attachments", []):
            ext = load_and_extract_attachment(dataset_source, att, email_id)
            extractions[att] = ext
            timeline.append(create_timeline_event("extractor_file", ext.doc_status, {
                "file": att,
                "doc_type": ext.doc_type,
            }))

        timeline.append(create_timeline_event("extractor", "completed", f"{len(extractions)} files processed"))
        return {"extractions": extractions, "timeline_logs": timeline}
    except Exception as e:
        logger.error("Extractor error for %s: %s", email_id, e)
        timeline.append(create_timeline_event("extractor", "failed", str(e)))
        return {
            "extractions": extractions,
            "timeline_logs": timeline,
            "error": f"extractor_failure: {e}",
        }


def route_after_extractor(state: PipelineState) -> str:
    """Conditional edge after extractor_node:
    If any document is unreadable/wrong_doc/missing or missing values, route to router.
    Only route to comparator when both SI and BL are fully present and clean.
    """
    if state.get("error") is not None:
        return "router"

    extractions = state.get("extractions", {})
    if len(extractions) < 2:
        return "router"

    # If any document is unreadable or wrong doc type, skip comparator
    for ext in extractions.values():
        if ext.doc_status in ("unreadable", "wrong_doc_type", "missing"):
            return "router"

    si_ext = next((ext for ext in extractions.values() if ext.doc_type == "SI"), None)
    bl_ext = next((ext for ext in extractions.values() if ext.doc_type == "BL"), None)
    if not si_ext or not bl_ext:
        return "router"

    # Check for missing values in required fields
    for ext in (si_ext, bl_ext):
        fmap = {f.field_name: f for f in ext.fields}
        for fname in CANONICAL_FIELDS:
            f = fmap.get(fname)
            if not f or f.value is None or f.confidence == 0.0:
                return "router"

    return "comparator"


def comparator_node(state: PipelineState) -> dict:
    """Compare extracted fields between SI and BL."""
    timeline = list(state.get("timeline_logs", []))
    timeline.append(create_timeline_event("comparator", "started"))

    extractions = state.get("extractions", {})
    si_ext = next((ext for ext in extractions.values() if ext.doc_type == "SI"), None)
    bl_ext = next((ext for ext in extractions.values() if ext.doc_type == "BL"), None)

    try:
        comparison = compare_extractions(si_ext, bl_ext)
        mismatches = [fc.field_name for fc in comparison.field_results if not fc.match]
        timeline.append(create_timeline_event("comparator", "completed", {
            "overall_confidence": comparison.overall_confidence,
            "mismatches": mismatches,
        }))
        return {"comparison": comparison, "timeline_logs": timeline}
    except Exception as e:
        logger.error("Comparator error for %s: %s", state["email_id"], e)
        timeline.append(create_timeline_event("comparator", "failed", str(e)))
        return {
            "comparison": None,
            "timeline_logs": timeline,
            "error": f"comparator_failure: {e}",
        }


def router_node(state: PipelineState) -> dict:
    """Produce final SubmissionEntry decision and dispatch escalation notification if needed."""
    timeline = list(state.get("timeline_logs", []))
    timeline.append(create_timeline_event("router", "started"))

    # If an unexpected pipeline failure occurred, escalate safely
    if state.get("error"):
        entry = SubmissionEntry(
            category="BL_COMPARISON",
            status="NEEDS_REVIEW",
            review_reason="unreadable",
            has_defect=False,
            defect_fields=[],
        )
        timeline.append(create_timeline_event("router", "escalated_due_to_error", state["error"]))
        evidence = build_escalation_evidence_for_route(
            email=state["email"],
            entry=entry,
            extractions=state.get("extractions", {}),
        )
        if evidence:
            send_escalation_notification(evidence)
            timeline.append(create_timeline_event("escalation_notified", entry.review_reason, evidence.model_dump()))
        return {"submission_entry": entry, "timeline_logs": timeline}

    entry = route_decision(
        email=state["email"],
        classification=state["classification"],
        extractions=state.get("extractions", {}),
        comparison=state.get("comparison"),
    )
    if entry.status == "NEEDS_REVIEW":
        evidence = build_escalation_evidence_for_route(
            email=state["email"],
            entry=entry,
            extractions=state.get("extractions", {}),
        )
        if evidence:
            send_escalation_notification(evidence)
            timeline.append(create_timeline_event("escalation_notified", entry.review_reason, evidence.model_dump()))

    timeline.append(create_timeline_event("router", "completed", {
        "status": entry.status,
        "review_reason": entry.review_reason,
        "has_defect": entry.has_defect,
        "defect_fields": entry.defect_fields,
    }))
    return {"submission_entry": entry, "timeline_logs": timeline}


# ── Assemble Graph ────────────────────────────────────────────────────────

def build_orchestrator_graph():
    """Build and compile the LangGraph StateGraph pipeline."""
    graph = StateGraph(PipelineState)

    graph.add_node("classifier", classifier_node)
    graph.add_node("extractor", extractor_node)
    graph.add_node("comparator", comparator_node)
    graph.add_node("router", router_node)

    graph.add_edge(START, "classifier")
    graph.add_conditional_edges(
        "classifier",
        route_after_classifier,
        {"extractor": "extractor", "router": "router"},
    )
    graph.add_conditional_edges(
        "extractor",
        route_after_extractor,
        {"comparator": "comparator", "router": "router"},
    )
    graph.add_edge("comparator", "router")
    graph.add_edge("router", END)

    return graph.compile()


# Singleton compiled graph
orchestrator = build_orchestrator_graph()


# ── Execution Helpers ─────────────────────────────────────────────────────

def run_single_email(
    email: dict,
    dataset_source: str = "data-basic",
    classification_override: Optional[ClassificationResult] = None,
) -> PipelineState:
    """Run the compiled LangGraph pipeline on one email record."""
    initial_state: PipelineState = {
        "email_id": email["email_id"],
        "email": email,
        "dataset_source": dataset_source,
        "classification": classification_override,
        "extractions": {},
        "comparison": None,
        "submission_entry": None,
        "timeline_logs": [],
        "error": None,
    }
    final_state = orchestrator.invoke(initial_state)
    return final_state


def run_pipeline(
    dataset_source: str = "data-basic",
    max_emails: Optional[int] = None,
    output_file: str = "submission.json",
    classification_cache: Optional[dict] = None,
) -> dict:
    """Run the pipeline across an inbox and write submission.json."""
    from sdk.loader import Inbox

    inbox = Inbox(dataset_source)
    emails = inbox.emails()
    if max_emails:
        emails = emails[:max_emails]

    submission: dict[str, dict] = {}
    print(f"\n{'='*70}")
    print(f"  RUNNING PIPELINE ON {len(emails)} EMAILS ({dataset_source})")
    print(f"{'='*70}\n")

    start_time = time.time()
    for idx, email in enumerate(emails):
        eid = email["email_id"]
        clf_override = None
        if classification_cache and eid in classification_cache:
            clf_override = classification_cache[eid]

        res_state = run_single_email(email, dataset_source, clf_override)
        entry: SubmissionEntry = res_state["submission_entry"]
        submission[eid] = entry.model_dump()

        if (idx + 1) % 50 == 0 or (idx + 1) == len(emails):
            elapsed = time.time() - start_time
            rate = (idx + 1) / elapsed if elapsed > 0 else 0
            print(f"  [{idx+1:3d}/{len(emails)}] processed ({rate:.1f} emails/sec)")

    Path(output_file).write_text(json.dumps(submission, indent=2))
    print(f"\nWritten {len(submission)} entries to {output_file}")
    return submission
