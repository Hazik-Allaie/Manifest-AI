"""
tests/test_unit_04.py — Test suite for Unit 4: Comparator + Fuzzy Match.
"""

from pathlib import Path
import pytest

from extraction.text_parser import parse_text_document
from matching.ensemble_voter import (
    compare_extractions,
    compare_entities,
    compare_ports,
    compare_container_counts,
    compare_gross_weights,
)
from shared.schemas import ComparisonResult, FieldComparison

# 10 pairs with known injected defects (identified manually)
KNOWN_DEFECT_CASES = {
    "email_004": {"consignee", "notify_party"},
    "email_013": {"port_of_discharge"},
    "email_025": {"container_count", "port_of_discharge"},
    "email_031": {"container_count", "gross_weight_kg"},
    "email_043": {"container_count"},
    "email_046": {"notify_party"},
    "email_065": {"notify_party", "port_of_discharge"},
    "email_119": {"port_of_loading"},
    "email_121": {"gross_weight_kg"},
    "email_145": {"shipper"},
}

CLEAN_CASES = [
    "email_001",
    "email_009",
    "email_032",
    "email_034",
    "email_040",
]


def test_10_known_defect_cases():
    """Verify that all injected defects are caught accurately across the 10 defect test pairs."""
    att_dir = Path("data-basic/attachments")

    for eid, expected_defects in KNOWN_DEFECT_CASES.items():
        si_path = att_dir / f"{eid}_SI.txt"
        bl_path = att_dir / f"{eid}_BL.txt"

        assert si_path.exists(), f"Missing SI file: {si_path}"
        assert bl_path.exists(), f"Missing BL file: {bl_path}"

        si_res = parse_text_document(si_path.read_text(encoding="utf-8"), doc_type="SI", email_id=eid)
        bl_res = parse_text_document(bl_path.read_text(encoding="utf-8"), doc_type="BL", email_id=eid)

        cmp_res = compare_extractions(si_res, bl_res)

        # 1. Output schema validation
        assert isinstance(cmp_res, ComparisonResult)
        cmp_res.model_validate(cmp_res.model_dump())
        assert cmp_res.email_id == eid
        assert len(cmp_res.field_results) == 7

        # 2. Extract flagged mismatch fields
        flagged_mismatches = {fc.field_name for fc in cmp_res.field_results if not fc.match}

        # 3. Assert exact match with expected defect fields
        assert flagged_mismatches == expected_defects, (
            f"Defect mismatch for {eid}: expected {expected_defects}, got {flagged_mismatches}"
        )


def test_zero_false_positives_on_clean_pairs():
    """Verify zero false-positive mismatches on clean SI/BL pairs."""
    att_dir = Path("data-basic/attachments")

    for eid in CLEAN_CASES:
        si_path = att_dir / f"{eid}_SI.txt"
        bl_path = att_dir / f"{eid}_BL.txt"

        si_res = parse_text_document(si_path.read_text(encoding="utf-8"), doc_type="SI", email_id=eid)
        bl_res = parse_text_document(bl_path.read_text(encoding="utf-8"), doc_type="BL", email_id=eid)

        cmp_res = compare_extractions(si_res, bl_res)
        cmp_res.model_validate(cmp_res.model_dump())

        # No fields should be flagged as mismatch
        mismatches = [fc.field_name for fc in cmp_res.field_results if not fc.match]
        assert len(mismatches) == 0, f"False positive mismatches in {eid}: {mismatches}"
        assert cmp_res.overall_confidence >= 0.90


def test_fuzzy_matching_units():
    """Test normalization and fuzzy logic directly on unit string cases."""
    # Entities: formatting and punctuation should match
    m, c = compare_entities("MOORIM SP CO., LTD", "Moorim SP Co Ltd")
    assert m is True and c >= 0.90

    m, c = compare_entities("APRIL FAR EAST (M) SDN BHD", "april far east m sdn. bhd.")
    assert m is True and c >= 0.90

    # Entities: different companies should mismatch
    m, c = compare_entities("EAST BRIGHT FZ-LLC", "UAB NOVAKOPA")
    assert m is False

    # Ports: matching ports with/without code
    m, c = compare_ports("PORT KLANG (WESTPORT), MALAYSIA (MYPKG)", "PORT KLANG, MALAYSIA")
    assert m is True and c >= 0.50

    # Ports: different ports should mismatch
    m, c = compare_ports("MOMBASA, KENYA (KEMBA)", "TUTICORIN, INDIA (KEMBA)")
    assert m is False

    # Container count: spacing and case formatting
    m, c = compare_container_counts("6 x 40'HC", "6 x 40' HC")
    assert m is True and c == 1.0

    # Container count: differing quantities should mismatch
    m, c = compare_container_counts("6 x 20'GP", "5 x 20'GP")
    assert m is False

    # Gross weight: formatting and spacing
    m, c = compare_gross_weights("21,577 KG", "21577 kgs")
    assert m is True and c == 1.0

    # Gross weight: large delta should mismatch
    m, c = compare_gross_weights("21,114 KG", "23,114 KG")
    assert m is False


if __name__ == "__main__":
    test_10_known_defect_cases()
    print("test_10_known_defect_cases passed!")
    test_zero_false_positives_on_clean_pairs()
    print("test_zero_false_positives_on_clean_pairs passed!")
    test_fuzzy_matching_units()
    print("test_fuzzy_matching_units passed!")
    print("\nALL UNIT 4 TESTS PASSED!")
