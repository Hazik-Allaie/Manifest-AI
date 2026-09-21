"""
tests/test_unit_02.py — Test suite for Unit 2: Plain-Text Extraction.
"""

from pathlib import Path
import pytest
from pydantic import ValidationError

from extraction.text_parser import parse_text_document, FIELDS
from shared.schemas import ExtractionResult, ExtractedField


PAIRS = [
    "email_001",
    "email_004",
    "email_009",
    "email_013",
    "email_025",
    "email_031",
    "email_032",
    "email_034",
    "email_040",
    "email_043",
]


def test_10_plain_text_pairs():
    """Verify that all 10 plain-text SI/BL pairs extract all 7 fields cleanly."""
    att_dir = Path("data-basic/attachments")

    for eid in PAIRS:
        for dtype in ["SI", "BL"]:
            fpath = att_dir / f"{eid}_{dtype}.txt"
            assert fpath.exists(), f"File missing: {fpath}"

            text = fpath.read_text(encoding="utf-8", errors="replace")
            res = parse_text_document(text, doc_type=dtype, email_id=eid)

            # 1. Output validates against schema
            assert isinstance(res, ExtractionResult)
            res.model_validate(res.model_dump())

            # 2. Metadata matches
            assert res.email_id == eid
            assert res.doc_type == dtype
            assert res.doc_status == "ok"

            # 3. All 7 fields present with non-empty values and snippets
            field_dict = {f.field_name: f for f in res.fields}
            assert len(field_dict) == 7
            for fname in FIELDS:
                assert fname in field_dict, f"Missing field {fname} in {fpath.name}"
                field = field_dict[fname]
                assert field.value is not None, f"Field {fname} extracted None in {fpath.name}"
                assert len(field.value.strip()) > 0
                assert field.confidence == 1.0
                assert field.source_snippet is not None
                assert len(field.source_snippet.strip()) > 0


def test_edge_cases():
    """Verify wrong_doc_type, unreadable, and missing_value handling."""
    att_dir = Path("data-basic/attachments")

    # Commercial Invoice -> wrong_doc_type
    p_ci = att_dir / "email_501_BL.txt"
    if p_ci.exists():
        t = p_ci.read_text(encoding="utf-8")
        res = parse_text_document(t, doc_type="BL", email_id="email_501")
        assert res.doc_status == "wrong_doc_type"

    # Packing List -> wrong_doc_type
    p_pl = att_dir / "email_502_BL.txt"
    if p_pl.exists():
        t = p_pl.read_text(encoding="utf-8")
        res = parse_text_document(t, doc_type="BL", email_id="email_502")
        assert res.doc_status == "wrong_doc_type"

    # Certificate of Origin -> wrong_doc_type
    p_coo = att_dir / "email_503_BL.txt"
    if p_coo.exists():
        t = p_coo.read_text(encoding="utf-8")
        res = parse_text_document(t, doc_type="BL", email_id="email_503")
        assert res.doc_status == "wrong_doc_type"

    # Missing value -> value=None, confidence=0.0
    p_mv = att_dir / "email_516_SI.txt"
    if p_mv.exists():
        t = p_mv.read_text(encoding="utf-8")
        res = parse_text_document(t, doc_type="SI", email_id="email_516")
        assert res.doc_status == "ok"
        fdict = {f.field_name: f for f in res.fields}
        # Gross weight in email_516_SI is 'N/A'
        assert fdict["gross_weight_kg"].value is None
        assert fdict["gross_weight_kg"].confidence == 0.0

    # Unreadable -> doc_status == unreadable
    res_empty = parse_text_document("", doc_type="SI", email_id="empty_test")
    assert res_empty.doc_status == "unreadable"

    res_garbled = parse_text_document("abc\x00def", doc_type="SI", email_id="garbled_test")
    assert res_garbled.doc_status == "unreadable"


if __name__ == "__main__":
    test_10_plain_text_pairs()
    print("test_10_plain_text_pairs passed!")
    test_edge_cases()
    print("test_edge_cases passed!")
    print("\nALL UNIT 2 TESTS PASSED!")
