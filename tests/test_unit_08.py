"""
tests/test_unit_08.py — Test suite for Unit 8: Vision & Multi-format Extraction.
"""

from pathlib import Path
import pytest

from shared.schemas import ExtractionResult, ExtractedField, SubmissionEntry
from extraction.vision_pipeline import extract_document
from matching.synonym_dict import CANONICAL_FIELDS
from agents.orchestrator import run_single_email
from sdk.loader import Inbox

ATTACHMENTS_DIR = Path("data-basic/attachments")


def test_extract_docx():
    """Verify extraction of fields from DOCX document."""
    p = ATTACHMENTS_DIR / "email_055_BL.docx"
    res = extract_document(p, doc_type="BL", email_id="email_055")

    assert isinstance(res, ExtractionResult)
    res.model_validate(res.model_dump())
    assert res.doc_status == "ok"
    assert res.doc_type == "BL"

    fmap = {f.field_name: f for f in res.fields}
    for c in CANONICAL_FIELDS:
        assert c in fmap
        assert fmap[c].value is not None, f"Field {c} should be extracted"
        assert fmap[c].confidence > 0.0

    assert "VITAL SOLUTIONS" in fmap["shipper"].value or "APRIL" in fmap["shipper"].value
    assert "AL GURG" in fmap["consignee"].value


def test_extract_xlsx():
    """Verify extraction of fields from XLSX document."""
    p = ATTACHMENTS_DIR / "email_005_BL.xlsx"
    res = extract_document(p, doc_type="BL", email_id="email_005")

    assert isinstance(res, ExtractionResult)
    res.model_validate(res.model_dump())
    assert res.doc_status == "ok"
    assert res.doc_type == "BL"

    fmap = {f.field_name: f for f in res.fields}
    for c in CANONICAL_FIELDS:
        assert c in fmap
        assert fmap[c].value is not None, f"Field {c} should be extracted"

    assert "ASIA PACIFIC" in fmap["shipper"].value
    assert "BALL & DOGGETT" in fmap["consignee"].value


def test_extract_digital_pdf():
    """Verify extraction of fields from digital PDF document."""
    p = ATTACHMENTS_DIR / "email_059_BL.pdf"
    res = extract_document(p, doc_type="BL", email_id="email_059")

    assert isinstance(res, ExtractionResult)
    res.model_validate(res.model_dump())
    assert res.doc_status == "ok"
    assert res.doc_type == "BL"

    fmap = {f.field_name: f for f in res.fields}
    for c in CANONICAL_FIELDS:
        assert c in fmap
        assert fmap[c].value is not None, f"Field {c} should be extracted from PDF"

    assert "APRIL FINE PAPER" in fmap["shipper"].value
    assert "FREMANTLE" in fmap["port_of_discharge"].value


def test_unreadable_three_failure_modes(tmp_path):
    """Verify explicit detection of all 3 unreadable failure modes:
    1. 0-byte file
    2. Truncated/corrupted PDF
    3. Scanned image-only PDF with no text layer
    """
    # 1. Empty 0-byte file
    empty_file = tmp_path / "empty_doc.pdf"
    empty_file.write_bytes(b"")
    res_empty = extract_document(empty_file, doc_type="BL", email_id="test_0")
    assert res_empty.doc_status == "unreadable"
    assert res_empty.fields == []

    # 2. Corrupt / truncated PDF
    corrupt_pdf = ATTACHMENTS_DIR / "email_511_BL.pdf"
    res_corrupt = extract_document(corrupt_pdf, doc_type="BL", email_id="email_511")
    assert res_corrupt.doc_status == "unreadable"

    # 3. Scanned image-only PDF
    scanned_pdf = ATTACHMENTS_DIR / "email_512_BL.pdf"
    res_scanned = extract_document(scanned_pdf, doc_type="BL", email_id="email_512")
    assert res_scanned.doc_status == "unreadable"


def test_wrong_doc_type():
    """Verify wrong document types are correctly marked."""
    p = ATTACHMENTS_DIR / "email_501_BL.txt"  # Commercial invoice
    res = extract_document(p, doc_type="BL", email_id="email_501")
    assert res.doc_status == "wrong_doc_type"


def test_orchestration_with_binary_docs():
    """Verify end-to-end LangGraph pipeline processes binary document emails."""
    inbox = Inbox("data-basic")

    # email_005 has XLSX attachments
    e5 = inbox.get("email_005")
    s5 = run_single_email(e5, dataset_source="data-basic")
    assert s5["submission_entry"] is not None
    assert isinstance(s5["submission_entry"], SubmissionEntry)
    assert s5["submission_entry"].status in ("OK", "MISMATCH")

    # email_059 has PDF attachments
    e59 = inbox.get("email_059")
    s59 = run_single_email(e59, dataset_source="data-basic")
    assert s59["submission_entry"] is not None
    assert isinstance(s59["submission_entry"], SubmissionEntry)
    assert s59["submission_entry"].status in ("OK", "MISMATCH")
