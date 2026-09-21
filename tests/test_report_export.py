"""
tests/test_report_export.py — Unit and integration tests for PDF Report Export.

Conforms to docs/Report-Export-Backend.md:
  - Validates PDF generation for OK, MISMATCH, and NEEDS_REVIEW shipments.
  - Confirms PDF integrity (valid PDF header, pypdf parsing, zero corruptions).
  - Tests API endpoints (/api/shipments/{email_id}/report.pdf and /api/email/{email_id}/report.pdf).
  - Tests 404 error handling on nonexistent shipment IDs.
"""

import io
import pytest
import pypdf
from fastapi.testclient import TestClient

from dashboard.server import app
from dashboard.backend.report_export import generate_shipment_report_pdf
from dashboard.report_export import generate_shipment_report_pdf as reexported_func


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_reexport_import():
    """Verify top-level module re-export from dashboard.report_export works identically."""
    assert generate_shipment_report_pdf is reexported_func


def test_generate_pdf_ok_status():
    """Verify PDF generation for an auto-cleared clean shipment (email_001)."""
    pdf_bytes = generate_shipment_report_pdf("email_001")
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF-")

    # Parse with pypdf to verify structural validity
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1

    extracted_text = ""
    for page in reader.pages:
        extracted_text += page.extract_text() or ""

    assert "MANIFEST AI" in extracted_text
    assert "email_001" in extracted_text
    assert "AUTO-CLEARED (OK)" in extracted_text
    assert "FIELD-BY-FIELD CROSS-EXAMINATION" in extracted_text
    assert "VERIFICATION PIPELINE AUDIT TIMELINE" in extracted_text


def test_generate_pdf_mismatch_status():
    """Verify PDF generation for a discrepancy shipment (email_043)."""
    pdf_bytes = generate_shipment_report_pdf("email_043")
    assert pdf_bytes.startswith(b"%PDF-")

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1

    extracted_text = ""
    for page in reader.pages:
        extracted_text += page.extract_text() or ""

    assert "email_043" in extracted_text
    assert "ACTION REQUIRED" in extracted_text
    assert "MISMATCH" in extracted_text
    assert "Container Count" in extracted_text


def test_generate_pdf_si_request_intake():
    """Verify PDF generation for an SI_REQUEST with zero attachments (email_322)."""
    pdf_bytes = generate_shipment_report_pdf("email_322")
    assert pdf_bytes.startswith(b"%PDF-")

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1

    extracted_text = ""
    for page in reader.pages:
        extracted_text += page.extract_text() or ""

    assert "email_322" in extracted_text
    assert "AUTO-CLEARED (OK)" in extracted_text
    assert "Aprilasia" in extracted_text
    assert "MATCH" in extracted_text
    # Ensure there are no broken placeholder MISMATCH or empty tables
    assert "MISMATCH" not in extracted_text


def test_generate_pdf_human_corrections_section():
    """Verify PDF generation includes recorded operator feedback when present (email_004)."""
    from infra.firestore_schema import save_correction, HumanCorrection
    c = HumanCorrection(
        email_id="email_004",
        field_name="consignee",
        original_value="Verified Consignee",
        corrected_value="Global Freight Co Ltd (Verified by Lead Dispatcher)",
        reason="Operator verified clean"
    )
    save_correction(c)

    pdf_bytes = generate_shipment_report_pdf("email_004")
    assert pdf_bytes.startswith(b"%PDF-")

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1

    extracted_text = ""
    for page in reader.pages:
        extracted_text += page.extract_text() or ""

    assert "email_004" in extracted_text
    assert "RECORDED OPERATOR CORRECTIONS" in extracted_text



def test_generate_pdf_needs_review_wrong_doc_type():
    """Verify PDF generation for a wrong_doc_type escalation (email_501)."""
    pdf_bytes = generate_shipment_report_pdf("email_501")
    assert pdf_bytes.startswith(b"%PDF-")

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1

    extracted_text = ""
    for page in reader.pages:
        extracted_text += page.extract_text() or ""

    assert "email_501" in extracted_text
    assert "HUMAN REVIEW REQUIRED" in extracted_text
    assert "wrong_doc_type" in extracted_text


def test_generate_pdf_needs_review_missing_value():
    """Verify PDF generation for a missing_value escalation (email_516)."""
    pdf_bytes = generate_shipment_report_pdf("email_516")
    assert pdf_bytes.startswith(b"%PDF-")

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1

    extracted_text = ""
    for page in reader.pages:
        extracted_text += page.extract_text() or ""

    assert "email_516" in extracted_text
    assert "missing_value" in extracted_text


def test_api_shipment_report_endpoint(client):
    """Test GET /api/shipments/{email_id}/report.pdf returns 200 with attachment header."""
    res = client.get("/api/shipments/email_001/report.pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert 'attachment; filename="shipment_email_001_report.pdf"' in res.headers["content-disposition"]
    assert res.content.startswith(b"%PDF-")


def test_api_email_alias_endpoint(client):
    """Test GET /api/email/{email_id}/report.pdf returns identical 200 PDF stream."""
    res = client.get("/api/email/email_004/report.pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert 'attachment; filename="shipment_email_004_report.pdf"' in res.headers["content-disposition"]
    assert res.content.startswith(b"%PDF-")


def test_api_nonexistent_shipment_returns_404(client):
    """Test GET /api/shipments/{nonexistent_id}/report.pdf returns 404."""
    res = client.get("/api/shipments/nonexistent_xyz_999/report.pdf")
    assert res.status_code == 404
    assert "not found" in res.json().get("detail", "").lower()


def test_pdf_footer_and_page_numbering():
    """Test that two-pass NumberedCanvas correctly draws page numbering and confidential footer."""
    pdf_bytes = generate_shipment_report_pdf("email_004")
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    num_pages = len(reader.pages)

    # Check footer text on last page
    last_page_text = reader.pages[-1].extract_text() or ""
    assert "Manifest AI Verification Desk" in last_page_text
    assert f"Page {num_pages} of {num_pages}" in last_page_text
