"""
tests/test_unit_09.py — Test suite for Unit 9: Ensemble Voting & Semantic Embeddings.
"""

import pytest
from matching.synonym_dict import match_field_label
from matching.embeddings import match_field_embedding
from matching.ensemble_voter import weighted_ensemble_vote, are_values_equivalent


def test_embeddings_fallback_on_unseen_labels():
    """Verify semantic embeddings fallback maps novel, unseen synonym labels."""
    test_cases = [
        ("Place of Departure", "port_of_loading"),
        ("Receiver of Goods", "consignee"),
        ("Weight of Cargo in KG", "gross_weight_kg"),
        ("Completely Unrelated Gibberish 98765", None),
    ]

    for label, expected in test_cases:
        matched = match_field_label(label, use_embeddings=True)
        assert matched == expected, f"Label '{label}' expected {expected}, got {matched}"


def test_synonym_dict_preserves_fast_dictionary():
    """Verify known dictionary entries resolve via dictionary without embeddings."""
    assert match_field_label("Load Port", use_embeddings=False) == "port_of_loading"
    assert match_field_label("Shipper/Exporter", use_embeddings=False) == "shipper"
    assert match_field_label("Gross Wt (kgs)", use_embeddings=False) == "gross_weight_kg"
    assert match_field_label("To the Order of", use_embeddings=False) == "consignee"
    assert match_field_label("Unknown Nonexistent", use_embeddings=False) is None


def test_weighted_ensemble_vote_unanimous():
    """Verify weighted voting when all 3 extraction methods agree."""
    predictions = [
        ("structure", "PORT KLANG, MALAYSIA", 1.0),
        ("regex", "PORT KLANG (WESTPORT), MALAYSIA (MYPKG)", 1.0),
        ("ner", "Port Klang", 1.0),
    ]

    val, conf, audit = weighted_ensemble_vote("port_of_loading", predictions)
    assert val is not None
    assert "port klang" in val.lower()
    assert conf == 1.0
    assert audit["status"] == "unanimous"
    assert audit["agreement"] == 1.0


def test_weighted_ensemble_vote_with_disagreement():
    """Verify weighted voting selects majority consensus and penalizes confidence on disagreement."""
    predictions = [
        ("structure", "EAST BRIGHT FZ-LLC", 1.0),  # Weight 0.40
        ("regex", "EAST BRIGHT FZ-LLC", 1.0),      # Weight 0.35
        ("ner", "UAB NOVAKOPA", 0.9),              # Weight 0.25 (disagrees!)
    ]

    val, conf, audit = weighted_ensemble_vote("shipper", predictions)
    assert val == "EAST BRIGHT FZ-LLC"
    # 0.75 agreement -> confidence penalized from 1.0 to 0.75
    assert conf == 0.75
    assert audit["status"] == "majority"
    assert "structure" in audit["winning_methods"]
    assert "regex" in audit["winning_methods"]
    assert "ner" not in audit["winning_methods"]


def test_weighted_ensemble_vote_complete_disagreement():
    """Verify weighted voting when all methods disagree drastically lowers confidence."""
    predictions = [
        ("structure", "Company Alpha", 1.0),  # Weight 0.40
        ("regex", "Company Beta", 1.0),       # Weight 0.35
        ("ner", "Company Gamma", 1.0),        # Weight 0.25
    ]

    val, conf, audit = weighted_ensemble_vote("shipper", predictions)
    assert val == "Company Alpha"  # Structure has highest single weight (0.40)
    assert conf == 0.40            # Penalized heavily below 0.50
    assert audit["status"] == "disputed"


def test_are_values_equivalent():
    """Verify domain-specific equivalence checking across field types."""
    assert are_values_equivalent("container_count", "6 x 40'HC", "6 x 40' HC") is True
    assert are_values_equivalent("container_count", "6 x 40'HC", "5 x 40'HC") is False
    assert are_values_equivalent("gross_weight_kg", "21,577 KG", "21577 kgs") is True
    assert are_values_equivalent("gross_weight_kg", "21,577 KG", "30,000 KG") is False
    assert are_values_equivalent("port_of_loading", "SINGAPORE (SGSIN)", "SINGAPORE") is True
