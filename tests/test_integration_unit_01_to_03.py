"""
tests/test_integration_unit_01_to_03.py — End-to-end integration test across Units 1, 2, and 3.

Pipeline flow tested:
  Email JSON record (Inbox)
        │
        ▼
  [Unit 1] classify_email()  ───► ClassificationResult (BL_COMPARISON, SI_REQUEST, etc.)
        │
        ▼ (if BL_COMPARISON with attachments)
  [Unit 2] parse_text_document() on each attachment
        │
        ▼ (internal label resolution)
  [Unit 3] match_field_label() resolves raw labels to 7 canonical fields
        │
        ▼
  Validated ExtractionResults (SI + BL) with fields, snippets, confidence, doc_status
"""

import json
import sys
from pathlib import Path
import pytest

# Ensure repo root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from sdk.loader import Inbox
from agents.classifier import classify_email
from extraction.text_parser import parse_text_document
from matching.synonym_dict import match_field_label, CANONICAL_FIELDS
from shared.schemas import ClassificationResult, ExtractionResult, ExtractedField


def run_pipeline_on_email(inbox: Inbox, email: dict) -> dict:
    """Run the integrated Units 1-3 pipeline on a single email record."""
    email_id = email["email_id"]
    
    # ── Step 1: Unit 1 Classifier ──────────────────────────────────────
    classification = classify_email(email)
    assert isinstance(classification, ClassificationResult)
    classification.model_validate(classification.model_dump())
    
    result = {
        "email_id": email_id,
        "classification": classification,
        "extractions": {},
    }
    
    # ── Step 2: If BL_COMPARISON with attachments, run Unit 2 + Unit 3 ─
    if classification.category == "BL_COMPARISON" and email.get("attachments"):
        for att_path in email["attachments"]:
            if not att_path.endswith(".txt"):
                continue  # plain-text scope for Unit 2
            
            raw_text = inbox.read_text(att_path)
            doc_type = "BL" if "_BL" in att_path else "SI"
            
            # Unit 2 Parser (which internally uses Unit 3 match_field_label)
            extraction = parse_text_document(raw_text, doc_type=doc_type, email_id=email_id)
            assert isinstance(extraction, ExtractionResult)
            extraction.model_validate(extraction.model_dump())
            
            result["extractions"][att_path] = extraction
            
    return result


def test_integrated_pipeline_diverse_sample():
    """Test integrated flow on a diverse set of emails across categories."""
    inbox = Inbox("data-basic")
    
    # Select representative emails:
    # email_001: BL_COMPARISON (clean SI+BL)
    # email_002: INVOICE_QUERY (no attachments)
    # email_003: SI_REQUEST (no attachments)
    # email_004: BL_COMPARISON (mismatched consignee/notify)
    # email_011: GENERAL (ops update)
    # email_015: SPAM (phishing)
    target_ids = ["email_001", "email_002", "email_003", "email_004", "email_011", "email_015"]
    
    print(f"\n{'='*75}")
    print("  INTEGRATED PIPELINE TEST -- UNITS 1 -> 2 -> 3")
    print(f"{'='*75}")
    
    for eid in target_ids:
        email = inbox.get(eid)
        pipeline_out = run_pipeline_on_email(inbox, email)
        
        clf = pipeline_out["classification"]
        print(f"\n[Email: {eid}]")
        print(f"  Category: {clf.category} (conf={clf.confidence:.2f})")
        print(f"  Evidence: {clf.evidence[:2]}")
        
        if clf.category == "BL_COMPARISON":
            exts = pipeline_out["extractions"]
            print(f"  Attachments Extracted: {len(exts)}")
            for att_path, ext in exts.items():
                print(f"    - {att_path} [status={ext.doc_status}, type={ext.doc_type}]")
                assert ext.doc_status == "ok"
                assert len(ext.fields) == 7
                # Verify all canonical fields are present and extracted
                for field in ext.fields:
                    assert field.field_name in CANONICAL_FIELDS
                    assert field.value is not None, f"Field {field.field_name} in {att_path} should have a value"
                    assert field.source_snippet is not None
                    # Verify Unit 3 mapping matches the field
                    assert field.field_name == match_field_label(field.source_snippet.split(':', 1)[0])
            print("  All 7 canonical fields aligned and validated against schema [OK]")
        else:
            print("  Non-comparison email successfully bypassed extraction [OK]")
            
    print(f"\n{'='*75}")
    print("  INTEGRATED TEST COMPLETED SUCCESSFULLY!")
    print(f"{'='*75}\n")


if __name__ == "__main__":
    test_integrated_pipeline_diverse_sample()
