"""
tests/test_unit_05.py — Test suite for Unit 5: Confidence Router & Escalation Logic.
"""

import json
from pathlib import Path
import pytest

from sdk.loader import Inbox
from shared.schemas import ClassificationResult, SubmissionEntry
from escalation.confidence_router import process_email, route_decision, load_and_extract_attachment


def test_20_labeled_edge_cases():
    """Verify that all 20 edge cases route to NEEDS_REVIEW with the correct review_reason."""
    dataset_source = "data-basic"
    inbox = Inbox(dataset_source)

    expected_reasons = {}
    for i in range(501, 506):
        expected_reasons[f"email_{i}"] = "wrong_doc_type"
    for i in range(506, 511):
        expected_reasons[f"email_{i}"] = "missing_attachment"
    for i in range(511, 516):
        expected_reasons[f"email_{i}"] = "unreadable"
    for i in range(516, 521):
        expected_reasons[f"email_{i}"] = "missing_value"

    print(f"\n{'='*75}")
    print("  UNIT 5 TEST — 20 LABELED EDGE CASES (email_501 to email_520)")
    print(f"{'='*75}\n")

    for eid, expected_reason in expected_reasons.items():
        email = inbox.get(eid)
        
        # Override classification as BL_COMPARISON to evaluate routing logic independently of live LLM call
        clf_override = ClassificationResult(
            email_id=eid,
            category="BL_COMPARISON",
            evidence=["edge_case_eval"],
            confidence=1.0,
        )

        entry = process_email(dataset_source, email, classification_override=clf_override)

        # 1. Schema validation
        assert isinstance(entry, SubmissionEntry)
        entry.model_validate(entry.model_dump())

        # 2. Strict correctness rules
        assert entry.category == "BL_COMPARISON"
        assert entry.status == "NEEDS_REVIEW", f"{eid} should be NEEDS_REVIEW, got {entry.status}"
        assert entry.review_reason == expected_reason, (
            f"{eid}: expected review_reason '{expected_reason}', got '{entry.review_reason}'"
        )
        assert entry.has_defect is False, f"{eid} must have has_defect=False (not a mismatch!)"
        assert entry.defect_fields == [], f"{eid} must have defect_fields=[]"

        print(f"  {eid:<12}: status={entry.status:<14} reason={entry.review_reason:<20} [PASS]")


def test_normal_and_mismatch_routing():
    """Verify clean and defective documents route to OK and MISMATCH without review_reason."""
    dataset_source = "data-basic"
    inbox = Inbox(dataset_source)

    # email_001 is clean -> OK
    e1 = inbox.get("email_001")
    clf1 = ClassificationResult(email_id="email_001", category="BL_COMPARISON", evidence=[], confidence=1.0)
    entry1 = process_email(dataset_source, e1, classification_override=clf1)
    assert entry1.status == "OK"
    assert entry1.review_reason is None
    assert entry1.has_defect is False
    assert entry1.defect_fields == []

    # email_004 has consignee/notify mismatch -> MISMATCH
    e4 = inbox.get("email_004")
    clf4 = ClassificationResult(email_id="email_004", category="BL_COMPARISON", evidence=[], confidence=1.0)
    entry4 = process_email(dataset_source, e4, classification_override=clf4)
    assert entry4.status == "MISMATCH"
    assert entry4.review_reason is None
    assert entry4.has_defect is True
    assert "consignee" in entry4.defect_fields

    # email_002 is INVOICE_QUERY -> OK
    e2 = inbox.get("email_002")
    clf2 = ClassificationResult(email_id="email_002", category="INVOICE_QUERY", evidence=[], confidence=1.0)
    entry2 = process_email(dataset_source, e2, classification_override=clf2)
    assert entry2.status == "OK"
    assert entry2.category == "INVOICE_QUERY"
    assert entry2.review_reason is None


if __name__ == "__main__":
    test_20_labeled_edge_cases()
    test_normal_and_mismatch_routing()
    print("\nALL UNIT 5 TESTS PASSED!")
