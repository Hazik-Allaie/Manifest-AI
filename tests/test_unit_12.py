"""
tests/test_unit_12.py — Failure Simulator Test Suite (Unit 12).

Validates:
  1. Synthetic fixture generation and schema integrity
  2. Mismatch fault injections (wrong container count, wrong weight, shipper, port of discharge)
  3. Escalation fault injections (missing BL, unreadable doc, wrong doc type, missing value)
  4. Semantic synonym alignment (different field names resolve cleanly without false alarms)
  5. Full simulator suite execution with 100% pass rate
"""

import pytest
from pathlib import Path

from tests.synthetic_failures.scenarios import SCENARIOS
from tests.synthetic_failures.generator import ensure_fixtures, get_scenario_email
from tests.synthetic_failures.simulator import run_scenario, run_all_scenarios
from agents.orchestrator import run_single_email
from shared.schemas import SubmissionEntry


@pytest.fixture(scope="module")
def fixtures_dir():
    """Ensure fixtures are generated and return directory path."""
    return ensure_fixtures()


def test_synthetic_fixtures_generation(fixtures_dir):
    """Test that all 9 synthetic scenarios generate valid inbox files and attachments."""
    inbox_dir = fixtures_dir / "inbox"
    attachments_dir = fixtures_dir / "attachments"

    assert inbox_dir.exists(), "Inbox directory must exist"
    assert attachments_dir.exists(), "Attachments directory must exist"

    for sid, sc in SCENARIOS.items():
        email = get_scenario_email(sid, fixtures_dir)
        assert email["email_id"] == f"synth_{sid}"
        assert len(email["attachments"]) >= 1

        # Verify SI attachment exists
        si_file = fixtures_dir / sc.si_filename
        assert si_file.exists(), f"SI file {sc.si_filename} must exist on disk"

        # Verify BL attachment if applicable
        if sc.bl_filename:
            bl_file = fixtures_dir / sc.bl_filename
            assert bl_file.exists(), f"BL file {sc.bl_filename} must exist on disk"


@pytest.mark.parametrize("scenario_id, expected_defects", [
    ("wrong_container_count", ["container_count"]),
    ("wrong_weight", ["gross_weight_kg"]),
    ("wrong_shipment_id", ["shipper"]),
    ("unit_mismatch", ["port_of_discharge"]),
])
def test_mismatch_failure_injections(fixtures_dir, scenario_id, expected_defects):
    """Test that discrepancy failures produce MISMATCH and correct defect_fields."""
    res = run_scenario(scenario_id, fixtures_dir)

    assert res["passed"] is True, f"Scenario {scenario_id} should pass validation"
    assert res["actual_status"] == "MISMATCH"
    assert res["actual_review_reason"] is None
    assert sorted(res["actual_defect_fields"]) == sorted(expected_defects)


@pytest.mark.parametrize("scenario_id, expected_reason", [
    ("missing_bl", "missing_attachment"),
    ("unreadable_document", "unreadable"),
    ("wrong_doc_type", "wrong_doc_type"),
    ("missing_value", "missing_value"),
])
def test_escalation_failure_injections(fixtures_dir, scenario_id, expected_reason):
    """Test that edge-case failures produce NEEDS_REVIEW and exact review_reason."""
    res = run_scenario(scenario_id, fixtures_dir)

    assert res["passed"] is True, f"Scenario {scenario_id} should pass validation"
    assert res["actual_status"] == "NEEDS_REVIEW"
    assert res["actual_review_reason"] == expected_reason
    assert res["actual_defect_fields"] == []


def test_semantic_synonyms_no_false_positive(fixtures_dir):
    """Test that alternate carrier terminology matches via synonym dictionary without false alarm."""
    res = run_scenario("different_field_names", fixtures_dir)

    assert res["passed"] is True
    assert res["actual_status"] == "OK"
    assert res["actual_review_reason"] is None
    assert res["actual_defect_fields"] == []


def test_full_simulator_suite_run(fixtures_dir):
    """Test that run_all_scenarios executes all 9 scenarios with a 100% pass rate."""
    results = run_all_scenarios(fixtures_dir, verbose=False)

    assert len(results) == 9
    for r in results:
        assert r["passed"] is True, f"Scenario '{r['scenario_id']}' failed: actual {r['actual_status']}"
