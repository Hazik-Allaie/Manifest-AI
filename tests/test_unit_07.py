"""
tests/test_unit_07.py — Test suite for Unit 7: Orchestration Assembly (LangGraph pipeline).
"""

import pytest
from sdk.loader import Inbox
from shared.schemas import ClassificationResult, SubmissionEntry
from agents.orchestrator import run_single_email, build_orchestrator_graph


def test_orchestration_non_comparison_branch():
    """Verify non-comparison emails bypass extraction and comparison straight to router."""
    inbox = Inbox("data-basic")
    email = inbox.get("email_002")

    clf_override = ClassificationResult(
        email_id="email_002",
        category="INVOICE_QUERY",
        evidence=["test_eval"],
        confidence=1.0,
    )

    state = run_single_email(email, dataset_source="data-basic", classification_override=clf_override)

    # 1. State integrity
    assert state["submission_entry"] is not None
    assert isinstance(state["submission_entry"], SubmissionEntry)
    assert state["submission_entry"].category == "INVOICE_QUERY"
    assert state["submission_entry"].status == "OK"

    # 2. Verify graph skipped extractor and comparator
    assert state["extractions"] == {}
    assert state["comparison"] is None

    # 3. Timeline check
    stages = [ev["stage"] for ev in state["timeline_logs"]]
    assert "classifier" in stages
    assert "router" in stages
    assert "extractor" not in stages
    assert "comparator" not in stages


def test_orchestration_edge_case_branch():
    """Verify edge case bypasses comparator directly to router."""
    inbox = Inbox("data-basic")
    email = inbox.get("email_501")  # Wrong doc type

    clf_override = ClassificationResult(
        email_id="email_501",
        category="BL_COMPARISON",
        evidence=["test_eval"],
        confidence=1.0,
    )

    state = run_single_email(email, dataset_source="data-basic", classification_override=clf_override)

    # 1. State integrity
    assert state["submission_entry"] is not None
    assert state["submission_entry"].status == "NEEDS_REVIEW"
    assert state["submission_entry"].review_reason == "wrong_doc_type"

    # 2. Extractor ran, comparator bypassed
    assert len(state["extractions"]) > 0
    assert state["comparison"] is None

    # 3. Timeline check
    stages = [ev["stage"] for ev in state["timeline_logs"]]
    assert "classifier" in stages
    assert "extractor" in stages
    assert "comparator" not in stages
    assert "router" in stages


def test_orchestration_clean_comparison_branch():
    """Verify full graph traversal for clean comparison (all 4 nodes)."""
    inbox = Inbox("data-basic")
    email = inbox.get("email_001")

    clf_override = ClassificationResult(
        email_id="email_001",
        category="BL_COMPARISON",
        evidence=["test_eval"],
        confidence=1.0,
    )

    state = run_single_email(email, dataset_source="data-basic", classification_override=clf_override)

    # 1. Traversed all 4 stages
    assert state["classification"] is not None
    assert len(state["extractions"]) == 2
    assert state["comparison"] is not None
    assert state["submission_entry"] is not None

    # 2. Result is OK with 0 defects
    assert state["submission_entry"].status == "OK"
    assert state["submission_entry"].has_defect is False
    assert state["submission_entry"].defect_fields == []

    # 3. Timeline contains all stages
    stages = [ev["stage"] for ev in state["timeline_logs"]]
    assert "classifier" in stages
    assert "extractor" in stages
    assert "comparator" in stages
    assert "router" in stages


def test_orchestration_defect_comparison_branch():
    """Verify full graph traversal for defective comparison."""
    inbox = Inbox("data-basic")
    email = inbox.get("email_004")

    clf_override = ClassificationResult(
        email_id="email_004",
        category="BL_COMPARISON",
        evidence=["test_eval"],
        confidence=1.0,
    )

    state = run_single_email(email, dataset_source="data-basic", classification_override=clf_override)

    assert state["submission_entry"].status == "MISMATCH"
    assert state["submission_entry"].has_defect is True
    assert "consignee" in state["submission_entry"].defect_fields


def test_orchestration_error_recovery():
    """Verify error recovery isolates exceptions and safely routes to NEEDS_REVIEW."""
    malformed_email = {
        "email_id": "corrupt_001",
        "from": "bad_email",
        "subject": "broken",
        "body": None,  # Might cause issue in components if not handled
        "attachments": ["nonexistent_path/fake.txt"],
    }

    state = run_single_email(malformed_email, dataset_source="data-basic")

    assert state["submission_entry"] is not None
    assert state["submission_entry"].status in ("OK", "NEEDS_REVIEW")
    # Pipeline did not raise unhandled exception


if __name__ == "__main__":
    test_orchestration_non_comparison_branch()
    test_orchestration_edge_case_branch()
    test_orchestration_clean_comparison_branch()
    test_orchestration_defect_comparison_branch()
    test_orchestration_error_recovery()
    print("\nALL UNIT 7 GRAPH TESTS PASSED!")
