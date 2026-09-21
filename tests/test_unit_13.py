"""
tests/test_unit_13.py — Final Integration & Dashboard Test Suite (Unit 13).

Validates:
  1. Dashboard server health check & HTML frontend liveness
  2. Analytics KPI aggregation & daily digest data
  3. Email triage listing & search filtering
  4. Side-by-side comparison inspector with 7 canonical fields
  5. One-click draft discrepancy notice generation
  6. Operator human correction persistence loop
  7. Cloud Run deployment artifacts integrity (Dockerfile, service.yaml, scripts)
"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from dashboard.server import app

_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_dashboard_liveness_health(client):
    """Test Cloud Run health check endpoint."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["service"] == "manifest-ai-dashboard"


def test_dashboard_home_page(client):
    """Test frontend HTML delivery."""
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "Manifest AI" in res.text
    assert "Triage Command Center" in res.text


def test_dashboard_analytics_kpi(client):
    """Test KPI analytics endpoint."""
    res = client.get("/api/analytics")
    assert res.status_code == 200
    data = res.json()
    assert data["total_emails"] == 520
    assert "MISMATCH" in data["status_distribution"]
    assert "NEEDS_REVIEW" in data["status_distribution"]
    assert "OK" in data["status_distribution"]
    assert data["benchmark_score"] >= 0.90


def test_dashboard_email_listing_and_filtering(client):
    """Test email triage listing with status filter."""
    res = client.get("/api/emails?limit=20")
    assert res.status_code == 200
    data = res.json()
    assert len(data["emails"]) == 20

    # Filter by MISMATCH
    res_mismatch = client.get("/api/emails?status=MISMATCH&limit=50")
    assert res_mismatch.status_code == 200
    m_data = res_mismatch.json()
    assert all(e["status"] == "MISMATCH" for e in m_data["emails"])


def test_dashboard_email_detail_side_by_side(client):
    """Test full audit detail with 7 canonical field comparisons."""
    res = client.get("/api/email/email_004")
    assert res.status_code == 200
    data = res.json()
    assert data["email_id"] == "email_004"
    assert len(data["field_comparisons"]) == 7
    assert len(data["timeline"]) >= 3


def test_dashboard_draft_correction_email(client):
    """Test one-click draft discrepancy notice."""
    res = client.post("/api/draft_email", json={"email_id": "email_004"})
    assert res.status_code == 200
    data = res.json()
    assert "draft_body" in data
    assert "Discrepancy Notice" in data["draft_body"]
    assert "email_004" in data["draft_body"]


def test_dashboard_operator_correction(client):
    """Test operator correction persistence."""
    res = client.post("/api/correct", json={
        "email_id": "email_004",
        "field_name": "container_count",
        "operator_value": "4 x 40HC",
        "notes": "Verified by lead dispatcher"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "doc_id" in data


def test_cloud_run_deployment_artifacts():
    """Verify presence and validity of all deployment artifacts."""
    dockerfile = _ROOT / "Dockerfile"
    dockerignore = _ROOT / ".dockerignore"
    deploy_sh = _ROOT / "deploy_cloud_run.sh"
    deploy_ps1 = _ROOT / "deploy_cloud_run.ps1"
    service_yaml = _ROOT / "service.yaml"

    assert dockerfile.exists() and "uvicorn" in dockerfile.read_text(encoding="utf-8")
    assert dockerignore.exists()
    assert deploy_sh.exists() and "gcloud run deploy" in deploy_sh.read_text(encoding="utf-8")
    assert deploy_ps1.exists() and "gcloud run deploy" in deploy_ps1.read_text(encoding="utf-8")
    assert service_yaml.exists() and "manifest-ai-509207" in service_yaml.read_text(encoding="utf-8")
