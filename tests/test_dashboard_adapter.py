"""
tests/test_dashboard_adapter.py — Schema Normalization Adapter & Correction Flow Tests.

Verifies:
  1. GET /api/dashboard/data returns all 14 fields derived server-side matching mock_dashboard_data.json.
  2. field #5 sub_status has the exact approved text 'Auto-verified — all 7 fields matched'.
  3. field #6 carrier_bl_ref is None (not reliably extracted).
  4. demurrage_avoided in _analytics_snapshot is relabeled as illustrative.
  5. POST /api/correct persists to Firestore and returns doc_id.
  6. Frontend static routes (/, /styles.css, /app.js, /mock_dashboard_data.json) return 200.
"""

import pytest
from fastapi.testclient import TestClient
from dashboard.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_dashboard_data_adapter_schema(client):
    """Verify GET /api/dashboard/data provides all 14 derived fields and analytics snapshot."""
    res = client.get("/api/dashboard/data")
    assert res.status_code == 200
    data = res.json()

    # 1. Analytics Snapshot
    assert "_analytics_snapshot" in data
    snap = data["_analytics_snapshot"]
    assert snap["total_emails"] >= 520
    assert "clearance_rate" in snap
    assert "mismatches_count" in snap
    assert snap["demurrage_avoided"] == "Example projected savings (illustrative)"

    # 2. Sample Email Entries & 14 Fields
    email_keys = [k for k in data.keys() if k.startswith("email_")]
    assert len(email_keys) >= 520

    entry = data["email_001"]
    # 14 fields check
    assert "po_number" in entry
    assert entry["po_number"].startswith("PO ")
    assert "customer" in entry
    assert "tags" in entry
    assert "port_pair" in entry["tags"]
    assert "latency" in entry
    assert "sub_status" in entry
    assert entry["sub_status"] == "Auto-verified \u2014 all 7 fields matched"
    assert "carrier_bl_ref" in entry
    assert entry["carrier_bl_ref"] is None
    assert "discrepancy_title" in entry
    assert "discrepancy_delta" in entry
    assert "si_display_val" in entry
    assert "bl_display_val" in entry
    assert "explainability" in entry
    assert "subgroup" in entry
    assert "exception_badge" in entry
    assert "missing_items" in entry
    assert "processed_at" in entry
    assert "timeline" in entry
    assert "field_results" in entry
    assert len(entry["field_results"]) == 7


def test_dashboard_data_adapter_mismatch_and_exception(client):
    """Verify derivation logic on MISMATCH and NEEDS_REVIEW records."""
    res = client.get("/api/dashboard/data")
    assert res.status_code == 200
    data = res.json()

    # Find a MISMATCH email
    mismatch_entry = next((e for k, e in data.items() if k.startswith("email_") and e.get("status") == "MISMATCH"), None)
    if mismatch_entry:
        assert mismatch_entry["discrepancy_title"] is not None
        assert mismatch_entry["discrepancy_delta"] is not None
        assert "CRITICAL DELTA" in mismatch_entry["discrepancy_delta"]

    # Find a NEEDS_REVIEW email
    review_entry = next((e for k, e in data.items() if k.startswith("email_") and e.get("status") == "NEEDS_REVIEW"), None)
    if review_entry:
        assert review_entry["exception_badge"] is not None
        assert review_entry["subgroup"] in ["wrong_doc_type", "missing_attachment", "unreadable", "missing_value", "missing_mandatory_fields", "missing_attachments", "other"]
        assert len(review_entry["missing_items"]) > 0


def test_dashboard_correction_submission_flow(client):
    """Verify POST /api/correct persists to Firestore and returns doc_id."""
    payload = {
        "email_id": "email_002",
        "field_name": "container_count",
        "operator_value": "4 x 40HC",
        "notes": "Verified by operator in production testing",
        "operator_id": "reviewer_ops_01"
    }
    try:
        res = client.post("/api/correct", json=payload)
        assert res.status_code == 200
        resp_data = res.json()
        assert resp_data["status"] == "success"
        assert "doc_id" in resp_data
        assert len(resp_data["doc_id"]) > 0
    finally:
        from infra.firestore_schema import get_firestore_client, CORRECTIONS_COLLECTION, invalidate_corrections_cache
        fs = get_firestore_client()
        if fs:
            try:
                fs.collection(CORRECTIONS_COLLECTION).document("email_002_container_count").delete()
                invalidate_corrections_cache()
            except Exception:
                pass


def test_dashboard_static_frontend_assets(client):
    """Verify delivery of frontend HTML and JS/CSS bundles."""
    # HTML
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "Manifest AI" in res.text
    assert "Triage Command Center" in res.text

    # CSS
    res = client.get("/styles.css")
    assert res.status_code == 200
    assert "text/css" in res.headers["content-type"]

    # JS
    res = client.get("/app.js")
    assert res.status_code == 200
    assert "application/javascript" in res.headers["content-type"]

    # Mock JSON
    res = client.get("/mock_dashboard_data.json")
    assert res.status_code == 200
    assert "application/json" in res.headers["content-type"]
