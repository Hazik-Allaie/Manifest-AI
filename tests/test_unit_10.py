"""
tests/test_unit_10.py — Escalation Notifications & Human Feedback Loop Tests (Unit 10).

Verifies:
  1. EscalationEvidence conforms strictly to ARCHITECTURE.md §5.
  2. Discord webhook embed formatting and notification delivery / durable audit logging.
  3. End-to-end escalation triggering for 3 distinct failure modes (missing_attachment, wrong_doc_type, missing_value).
  4. Firestore persistence of 3 human corrections and retrieval.
  5. Dynamic few-shot prompt injection producing measurable behavior change.
  6. Feedback loop overrides correcting faulty extractions.
  7. Orchestrator router integration recording escalation events in timeline logs.
"""

import os
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from shared.schemas import (
    ClassificationResult,
    ExtractionResult,
    ExtractedField,
    SubmissionEntry,
)
from escalation.notifier import (
    EscalationEvidence,
    build_escalation_evidence,
    format_discord_payload,
    send_escalation_notification,
    record_escalation_audit,
)
from escalation.confidence_router import (
    route_decision,
    build_escalation_evidence_for_route,
)
from infra.firestore_schema import (
    HumanCorrection,
    save_correction,
    get_recent_corrections,
    clear_test_corrections,
)
from escalation.feedback_loop import (
    build_few_shot_guidance,
    inject_few_shot_into_extraction_prompt,
    apply_correction_overrides,
    submit_human_correction,
)
from agents.orchestrator import run_single_email


# ── Test 1: Escalation Evidence Schema & Discord Payload ─────────────────────

def test_escalation_evidence_packet_structure():
    """Verify EscalationEvidence conforms strictly to ARCHITECTURE.md §5."""
    evidence = build_escalation_evidence(
        email_id="email_045",
        review_reason="missing_value",
        field="gross_weight_kg",
        source_snippet="GROSS WEIGHT: ???",
        system_guess=None,
    )

    data = evidence.model_dump()
    assert data["email_id"] == "email_045"
    assert data["review_reason"] == "missing_value"
    assert data["field"] == "gross_weight_kg"
    assert data["source_snippet"] == "GROSS WEIGHT: ???"
    assert data["system_guess"] is None
    assert "timestamp" in data

    # Test Discord payload structure
    payload = format_discord_payload(evidence)
    assert "embeds" in payload
    embed = payload["embeds"][0]
    assert "🚨 Manifest AI Escalation: missing_value" in embed["title"]
    field_names = [f["name"] for f in embed["fields"]]
    assert "Email ID" in field_names
    assert "Review Reason" in field_names
    assert "Field" in field_names
    assert "System Guess" in field_names
    assert "Source Snippet" in field_names


# ── Test 2: Trigger 3 Distinct Escalations End-to-End ─────────────────────────

def test_escalation_three_distinct_reasons(tmp_path):
    """Trigger 3 distinct escalations and confirm notification dispatch and audit logging."""
    test_log = tmp_path / "test_escalations.jsonl"
    dispatched_payloads = []

    def mock_urlopen(req, timeout=5.0):
        body = json.loads(req.data.decode("utf-8"))
        dispatched_payloads.append(body)
        mock_resp = MagicMock()
        mock_resp.status = 204
        mock_resp.__enter__.return_value = mock_resp
        mock_resp.__exit__.return_value = None
        return mock_resp

    # Case A: missing_attachment
    email_a = {"email_id": "test_esc_001", "attachments": ["invoice.pdf"]}
    clf_a = ClassificationResult(email_id="test_esc_001", category="BL_COMPARISON", evidence=[], confidence=1.0)
    entry_a = route_decision(email_a, clf_a, {})
    assert entry_a.status == "NEEDS_REVIEW"
    assert entry_a.review_reason == "missing_attachment"
    evidence_a = build_escalation_evidence_for_route(email_a, entry_a, {})
    assert evidence_a is not None
    assert evidence_a.field == "attachments"

    # Case B: wrong_doc_type
    email_b = {"email_id": "test_esc_002", "attachments": ["att_SI.txt", "att_BL.txt"]}
    clf_b = ClassificationResult(email_id="test_esc_002", category="BL_COMPARISON", evidence=[], confidence=1.0)
    exts_b = {
        "att_SI.txt": ExtractionResult(email_id="test_esc_002", doc_type="SI", fields=[], doc_status="ok"),
        "att_BL.txt": ExtractionResult(email_id="test_esc_002", doc_type="BL", fields=[], doc_status="wrong_doc_type", raw_text="PACKING LIST REF #123"),
    }
    entry_b = route_decision(email_b, clf_b, exts_b)
    assert entry_b.status == "NEEDS_REVIEW"
    assert entry_b.review_reason == "wrong_doc_type"
    evidence_b = build_escalation_evidence_for_route(email_b, entry_b, exts_b)
    assert evidence_b is not None
    assert evidence_b.field == "doc_type"
    assert "packing list" in (evidence_b.source_snippet or "").lower()

    # Case C: missing_value (all fields present except gross_weight_kg)
    sample_fields = {
        "shipper": "ACME CORP",
        "consignee": "GLOBAL LOGISTICS",
        "notify_party": "SAME AS CONSIGNEE",
        "port_of_loading": "SINGAPORE",
        "port_of_discharge": "ROTTERDAM",
        "container_count": "2 x 40'HC",
    }
    si_fields = [
        ExtractedField(field_name=k, value=v, source_snippet=f"{k}: {v}", confidence=1.0)
        for k, v in sample_fields.items()
    ]
    si_fields.append(
        ExtractedField(field_name="gross_weight_kg", value=None, source_snippet=None, confidence=0.0)
    )

    bl_fields = [
        ExtractedField(field_name=k, value=v, source_snippet=f"{k}: {v}", confidence=1.0)
        for k, v in sample_fields.items()
    ]
    bl_fields.append(
        ExtractedField(field_name="gross_weight_kg", value="10,000", source_snippet="Weight: 10000", confidence=1.0)
    )

    email_c = {"email_id": "test_esc_003", "attachments": ["att_SI.txt", "att_BL.txt"]}
    clf_c = ClassificationResult(email_id="test_esc_003", category="BL_COMPARISON", evidence=[], confidence=1.0)
    exts_c = {
        "att_SI.txt": ExtractionResult(email_id="test_esc_003", doc_type="SI", fields=si_fields, doc_status="ok"),
        "att_BL.txt": ExtractionResult(email_id="test_esc_003", doc_type="BL", fields=bl_fields, doc_status="ok"),
    }
    entry_c = route_decision(email_c, clf_c, exts_c)
    assert entry_c.status == "NEEDS_REVIEW"
    assert entry_c.review_reason == "missing_value"
    evidence_c = build_escalation_evidence_for_route(email_c, entry_c, exts_c)
    assert evidence_c is not None
    assert evidence_c.field == "gross_weight_kg"

    # Now verify notifications fire for all 3 with webhook and audit log
    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        for ev in (evidence_a, evidence_b, evidence_c):
            success = send_escalation_notification(
                evidence=ev,
                webhook_url="https://discord.com/api/webhooks/mock/test",
                log_path=test_log,
            )
            assert success is True

    # Confirm 3 notifications dispatched
    assert len(dispatched_payloads) == 3
    reasons = [p["embeds"][0]["title"] for p in dispatched_payloads]
    assert any("missing_attachment" in r for r in reasons)
    assert any("wrong_doc_type" in r for r in reasons)
    assert any("missing_value" in r for r in reasons)

    # Confirm 3 records written to durable JSONL audit log
    lines = test_log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
    records = [json.loads(line) for line in lines]
    assert records[0]["email_id"] == "test_esc_001"
    assert records[1]["email_id"] == "test_esc_002"
    assert records[2]["email_id"] == "test_esc_003"


# ── Test 3: Firestore Human Corrections CRUD ─────────────────────────────────

def test_firestore_human_corrections_crud():
    """Submit 3 fake corrections to Firestore, confirm persistence and retrieval."""
    test_prefix = "test_crud_unit10_"

    c1 = HumanCorrection(
        email_id=f"{test_prefix}001",
        field_name="gross_weight_kg",
        original_value="25,000 LBS",
        corrected_value="11339.8",
        reason="Unit conversion from imperial lbs to metric kg",
    )
    c2 = HumanCorrection(
        email_id=f"{test_prefix}002",
        field_name="port_of_loading",
        original_value="PKG",
        corrected_value="Port Klang",
        reason="Expanded 3-letter port abbreviation",
    )
    c3 = HumanCorrection(
        email_id=f"{test_prefix}003",
        field_name="container_count",
        original_value="3 UNITS",
        corrected_value="3 x 40'HC",
        reason="Resolved container equipment specification",
    )

    try:
        # Save all 3
        id1 = save_correction(c1)
        id2 = save_correction(c2)
        id3 = save_correction(c3)
        assert id1 and id2 and id3

        # Retrieve recent corrections
        recent = get_recent_corrections(limit=10)
        found_ids = {c.email_id for c in recent}
        assert f"{test_prefix}001" in found_ids
        assert f"{test_prefix}002" in found_ids
        assert f"{test_prefix}003" in found_ids

        # Retrieve filtered by field_name
        filtered = get_recent_corrections(field_name="port_of_loading", limit=5)
        assert any(c.corrected_value == "Port Klang" for c in filtered)

    finally:
        # Clean up test records
        deleted = clear_test_corrections(email_prefix=test_prefix)
        assert deleted >= 3


# ── Test 4: Dynamic Few-Shot Prompt Injection ────────────────────────────────

def test_few_shot_prompt_injection_observable_change():
    """Verify dynamic few-shot prompt injection causes an observable change in the extraction prompt."""
    base_prompt = "You are a shipping document parser. Extract fields: shipper, consignee, gross_weight_kg."

    fake_corrections = [
        HumanCorrection(
            email_id="test_fs_01",
            field_name="gross_weight_kg",
            original_value="TOTAL WT: 20 TONS",
            corrected_value="20000.0",
            reason="Converted tons to kg",
        ),
        HumanCorrection(
            email_id="test_fs_02",
            field_name="shipper",
            original_value="SAME AS CONSIGNEE",
            corrected_value="N/A - EXPLICIT SELLER NEEDED",
            reason="Ambiguous relative reference flagged",
        ),
    ]

    # Without corrections
    unmodified_prompt = inject_few_shot_into_extraction_prompt(base_prompt, corrections=[])
    assert unmodified_prompt == base_prompt

    # With corrections
    enhanced_prompt = inject_few_shot_into_extraction_prompt(
        base_prompt,
        corrections=fake_corrections,
    )

    # Observable behavior change
    assert len(enhanced_prompt) > len(base_prompt)
    assert "### HUMAN OPERATOR CORRECTION EXAMPLES" in enhanced_prompt
    assert "gross_weight_kg" in enhanced_prompt
    assert "TOTAL WT: 20 TONS" in enhanced_prompt
    assert "20000.0" in enhanced_prompt
    assert "Converted tons to kg" in enhanced_prompt
    assert "SAME AS CONSIGNEE" in enhanced_prompt


# ── Test 5: Deterministic Feedback Loop Overrides ────────────────────────────

def test_feedback_loop_override_applied():
    """Verify that apply_correction_overrides fixes known faulty values and elevates confidence."""
    corrections = [
        HumanCorrection(
            email_id="test_override_01",
            field_name="gross_weight_kg",
            original_value="12000 lbs",
            corrected_value="5443.11",
            reason="Converted lbs to kg",
        )
    ]

    extracted_fields = [
        ExtractedField(field_name="shipper", value="ACME CORP", source_snippet="ACME CORP", confidence=0.9),
        ExtractedField(field_name="gross_weight_kg", value="12000 lbs", source_snippet="12000 lbs", confidence=0.7),
    ]

    corrected_fields = apply_correction_overrides(extracted_fields, corrections=corrections)
    fmap = {f.field_name: f for f in corrected_fields}

    # Shipper remains unchanged
    assert fmap["shipper"].value == "ACME CORP"
    assert fmap["shipper"].confidence == 0.9

    # gross_weight_kg is corrected to metric kg and confidence elevated to 1.0
    assert fmap["gross_weight_kg"].value == "5443.11"
    assert fmap["gross_weight_kg"].confidence == 1.0


# ── Test 6: Orchestrator Integration with Escalation Logging ─────────────────

def test_orchestrator_integration_escalation_event(tmp_path):
    """Run an email with missing attachments through orchestrator and verify timeline event."""
    test_log = tmp_path / "orch_escalations.jsonl"

    fake_email = {
        "email_id": "test_orch_esc_099",
        "subject": "BL Comparison Request - Vessel 123",
        "body": "Please find attached document for comparison.",
        "attachments": ["single_attachment_SI.txt"],  # Only 1 attachment -> triggers missing_attachment
    }

    with patch("escalation.notifier.DEFAULT_LOG_PATH", test_log):
        res_state = run_single_email(
            email=fake_email,
            dataset_source="data-basic",
            classification_override=ClassificationResult(
                email_id="test_orch_esc_099",
                category="BL_COMPARISON",
                evidence=["Explicit comparison request"],
                confidence=1.0,
            ),
        )

    entry = res_state["submission_entry"]
    assert entry.status == "NEEDS_REVIEW"
    assert entry.review_reason == "missing_attachment"

    timeline_stages = [ev["stage"] for ev in res_state["timeline_logs"]]
    assert "escalation_notified" in timeline_stages
    esc_event = next(ev for ev in res_state["timeline_logs"] if ev["stage"] == "escalation_notified")
    assert esc_event["details"]["email_id"] == "test_orch_esc_099"
    assert esc_event["details"]["review_reason"] == "missing_attachment"
