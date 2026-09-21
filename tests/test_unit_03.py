"""
tests/test_unit_03.py — Test suite for Unit 3: Semantic Field Matching.
"""

import pytest
from matching.synonym_dict import match_field_label, normalize_label, CANONICAL_FIELDS, get_synonyms_for_field

# 15+ known synonym pairs from dataset README / generator pools
KNOWN_SYNONYM_PAIRS = [
    # port_of_loading
    ("Load Port", "port_of_loading"),
    ("Port of Loading", "port_of_loading"),
    ("Port of Loading (POL)", "port_of_loading"),
    ("POL", "port_of_loading"),
    ("PORT OF LOADING", "port_of_loading"),
    # port_of_discharge
    ("Discharge Port", "port_of_discharge"),
    ("Port of Discharge", "port_of_discharge"),
    ("Port of Discharge (POD)", "port_of_discharge"),
    ("POD", "port_of_discharge"),
    ("PORT OF DISCHARGE", "port_of_discharge"),
    # consignee
    ("Consignee", "consignee"),
    ("Consignee (Non-Negotiable)", "consignee"),
    ("CONSIGNEE", "consignee"),
    ("To the Order of", "consignee"),
    # shipper
    ("Shipper", "shipper"),
    ("Shipper/Exporter", "shipper"),
    ("Shipper (Principal or Seller)", "shipper"),
    ("SHIPPER", "shipper"),
    # notify_party
    ("Notify Party", "notify_party"),
    ("Notify", "notify_party"),
    ("Notify Party/Intermediate Consignee", "notify_party"),
    ("NOTIFY PARTY", "notify_party"),
    # container_count
    ("Container Count", "container_count"),
    ("No. of Containers", "container_count"),
    ("No. of Containers or Packages", "container_count"),
    ("Total Containers", "container_count"),
    ("Containers", "container_count"),
    # gross_weight_kg
    ("Gross Weight (KG)", "gross_weight_kg"),
    ("Gross Wt (kgs)", "gross_weight_kg"),
    ("Gross Weight毛重(KGS)", "gross_weight_kg"),
    ("GROSS WEIGHT", "gross_weight_kg"),
    ("Gross Weight", "gross_weight_kg"),
]


def test_known_synonym_pairs():
    """Verify that all 32 documented synonym pairs resolve to the exact canonical field."""
    for raw_label, expected_canonical in KNOWN_SYNONYM_PAIRS:
        resolved = match_field_label(raw_label)
        assert resolved == expected_canonical, (
            f"Failed on '{raw_label}': expected '{expected_canonical}', got '{resolved}'"
        )


def test_normalization_and_formatting_variants():
    """Verify resilience to trailing colons, whitespace, and mixed casing."""
    variants = [
        ("  Load Port:  ", "port_of_loading"),
        ("load port", "port_of_loading"),
        ("LOAD PORT:", "port_of_loading"),
        ("Port   of   Loading  (POL):", "port_of_loading"),
        ("TO THE ORDER OF:", "consignee"),
        ("gross wt (kgs):", "gross_weight_kg"),
        ("Gross Weight毛重(KGS):", "gross_weight_kg"),
        ("NO. OF CONTAINERS OR PACKAGES:", "container_count"),
        ("pod:", "port_of_discharge"),
        ("Shipper/Exporter:", "shipper"),
    ]
    for raw_label, expected_canonical in variants:
        assert match_field_label(raw_label) == expected_canonical


def test_metadata_fields():
    """Verify common shipping document metadata fields resolve appropriately."""
    metadata_pairs = [
        ("Vessel", "vessel"),
        ("Ocean Vessel", "vessel"),
        ("Voyage No.", "voyage"),
        ("Commodity", "commodity"),
        ("Description of Goods", "commodity"),
        ("Booking Ref", "booking_no"),
        ("Bill of Lading No.", "bl_no"),
    ]
    for raw_label, expected in metadata_pairs:
        assert match_field_label(raw_label) == expected


def test_unrecognized_labels():
    """Verify unrecognized or empty labels return None without raising errors."""
    unrecognized = [
        "Invoice Amount",
        "Payment Terms",
        "Random Header",
        "HS Code",
        "",
        None,
    ]
    for raw_label in unrecognized:
        assert match_field_label(raw_label) is None


def test_canonical_fields_complete():
    """Verify all 7 canonical fields have at least one synonym defined."""
    for cf in CANONICAL_FIELDS:
        synonyms = get_synonyms_for_field(cf)
        assert len(synonyms) >= 3, f"Field '{cf}' has fewer than 3 synonyms: {synonyms}"


if __name__ == "__main__":
    test_known_synonym_pairs()
    print("test_known_synonym_pairs passed!")
    test_normalization_and_formatting_variants()
    print("test_normalization_and_formatting_variants passed!")
    test_metadata_fields()
    print("test_metadata_fields passed!")
    test_unrecognized_labels()
    print("test_unrecognized_labels passed!")
    test_canonical_fields_complete()
    print("test_canonical_fields_complete passed!")
    print("\nALL UNIT 3 TESTS PASSED!")
