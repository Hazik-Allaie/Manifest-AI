"""
extraction/text_parser.py — Plain-text SI/BL attachment parser (Unit 2).

Extracts the 7 required fields from plain-text Shipping Instruction (SI)
and draft Bill of Lading (BL) attachments:
  - shipper
  - consignee
  - notify_party
  - port_of_loading
  - port_of_discharge
  - container_count
  - gross_weight_kg

Produces a schema-valid ExtractionResult with per-field values,
confidence scores, source snippets, and doc_status.
"""

import re
import logging
from typing import Literal, Optional

from shared.schemas import ExtractedField, ExtractionResult
from matching.synonym_dict import match_field_label

logger = logging.getLogger(__name__)

# ── Canonical 7 comparison fields ─────────────────────────────────────────
FIELDS: list[Literal[
    "shipper", "consignee", "notify_party", "port_of_loading",
    "port_of_discharge", "container_count", "gross_weight_kg"
]] = [
    "shipper",
    "consignee",
    "notify_party",
    "port_of_loading",
    "port_of_discharge",
    "container_count",
    "gross_weight_kg",
]

# ── Label synonym mapping ─────────────────────────────────────────────────
# Maps lowercased, stripped labels to canonical field names
LABEL_SYNONYMS: dict[str, str] = {
    # shipper
    "shipper": "shipper",
    "shipper/exporter": "shipper",
    "shipper (principal or seller)": "shipper",
    
    # consignee
    "consignee": "consignee",
    "consignee (non-negotiable)": "consignee",
    "to the order of": "consignee",
    
    # notify_party
    "notify party": "notify_party",
    "notify": "notify_party",
    "notify party/intermediate consignee": "notify_party",
    
    # port_of_loading
    "port of loading": "port_of_loading",
    "port of loading (pol)": "port_of_loading",
    "load port": "port_of_loading",
    "pol": "port_of_loading",
    
    # port_of_discharge
    "port of discharge": "port_of_discharge",
    "port of discharge (pod)": "port_of_discharge",
    "discharge port": "port_of_discharge",
    "pod": "port_of_discharge",
    
    # container_count
    "no. of containers": "container_count",
    "total containers": "container_count",
    "no. of containers or packages": "container_count",
    "container count": "container_count",
    "containers": "container_count",
    
    # gross_weight_kg
    "gross weight (kg)": "gross_weight_kg",
    "gross wt (kgs)": "gross_weight_kg",
    "gross weight毛重(kgs)": "gross_weight_kg",
    "gross weight": "gross_weight_kg",
}

# ── Blank/placeholder tokens that signify missing values ──────────────────
BLANK_TOKENS = {"???", "_______", "TBA", "TBC", "N/A", "NA", "NONE", "NULL", ""}


def is_blank_value(val: Optional[str]) -> bool:
    """Check if an extracted value is effectively blank or a placeholder."""
    if val is None:
        return True
    s = val.strip()
    if not s or s.upper() in BLANK_TOKENS:
        return True
    # Match strings consisting solely of underscores, question marks, dashes, spaces
    if re.match(r"^[_?\- ]+$", s):
        return True
    # Match patterns like '____MT', '____MTS'
    if re.match(r"^_+MTS?$", s, re.IGNORECASE):
        return True
    return False


def detect_doc_type_and_status(
    text: str,
    declared_doc_type: Optional[Literal["SI", "BL"]] = None,
) -> tuple[Literal["SI", "BL"], Literal["ok", "missing", "unreadable", "wrong_doc_type"]]:
    """Detect document type (SI or BL) and document validity status."""
    if not text or not text.strip() or "\x00" in text:
        return declared_doc_type or "SI", "unreadable"

    upper_text = text.upper()

    # Wrong doc type indicators (e.g. Commercial Invoice, Packing List, COO)
    wrong_type_markers = [
        "COMMERCIAL INVOICE",
        "PACKING LIST",
        "CERTIFICATE OF ORIGIN",
        "NOT A SHIPPING INSTRUCTION",
        "NOT AN SI OR BL",
        "NO PORT OR VESSEL DETAILS",
    ]
    for marker in wrong_type_markers:
        if marker in upper_text:
            return declared_doc_type or "SI", "wrong_doc_type"

    # Infer doc_type if not explicitly provided
    if declared_doc_type:
        doc_type = declared_doc_type
    elif "BILL OF LADING" in upper_text or "B/L NO" in upper_text:
        doc_type = "BL"
    else:
        doc_type = "SI"

    return doc_type, "ok"


def parse_text_document(
    text: str,
    doc_type: Optional[Literal["SI", "BL"]] = None,
    email_id: str = "",
) -> ExtractionResult:
    """Parse a plain-text SI or BL document and extract all 7 canonical fields.

    Args:
        text: Raw text of the attachment.
        doc_type: Optional document type ("SI" or "BL"). Auto-detected if None.
        email_id: Associated email ID (e.g. "email_001").

    Returns:
        ExtractionResult validating against the shared Pydantic schema.
    """
    resolved_doc_type, doc_status = detect_doc_type_and_status(text, doc_type)

    extracted_dict: dict[str, tuple[Optional[str], Optional[str], float]] = {}

    if doc_status == "ok":
        lines = text.splitlines()
        for idx, line in enumerate(lines):
            # Ignore indented continuation lines and separator lines
            if not line or line.startswith(" ") or line.startswith("\t") or line.startswith("="):
                continue
            if ":" not in line:
                continue

            raw_label, raw_val = line.split(":", 1)
            field_name = match_field_label(raw_label)
            if not field_name or field_name not in FIELDS:
                continue

            val_str = raw_val.strip()
            source_snippet = line.strip()

            if is_blank_value(val_str):
                extracted_dict[field_name] = (None, source_snippet, 0.0)
            else:
                extracted_dict[field_name] = (val_str, source_snippet, 1.0)

    # Build all 7 fields in canonical order
    fields: list[ExtractedField] = []
    for f in FIELDS:
        if f in extracted_dict:
            val, snippet, conf = extracted_dict[f]
            fields.append(
                ExtractedField(
                    field_name=f,
                    value=val,
                    source_snippet=snippet,
                    confidence=conf,
                )
            )
        else:
            fields.append(
                ExtractedField(
                    field_name=f,
                    value=None,
                    source_snippet=None,
                    confidence=0.0,
                )
            )

    result = ExtractionResult(
        email_id=email_id,
        doc_type=resolved_doc_type,
        fields=fields,
        doc_status=doc_status,
    )
    return result


# ── CLI & Test Runner ────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from pathlib import Path

    sample_files = sys.argv[1:] if len(sys.argv) > 1 else [
        "data-basic/attachments/email_001_SI.txt",
        "data-basic/attachments/email_001_BL.txt",
        "data-basic/attachments/email_004_SI.txt",
        "data-basic/attachments/email_004_BL.txt",
        "data-basic/attachments/email_501_BL.txt",  # wrong doc type
        "data-basic/attachments/email_516_SI.txt",  # missing value
    ]

    print(f"\n{'='*70}")
    print(f"  TEXT PARSER TEST — {len(sample_files)} sample files")
    print(f"{'='*70}\n")

    for fpath in sample_files:
        p = Path(fpath)
        if not p.exists():
            print(f"File not found: {p}")
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        eid = p.stem.split("_")[0] + "_" + p.stem.split("_")[1] if "_" in p.stem else ""
        dtype = "BL" if "_BL" in p.name else "SI"
        res = parse_text_document(text, doc_type=dtype, email_id=eid)

        print(f"File: {p.name:<25} doc_status: {res.doc_status:<15} doc_type: {res.doc_type}")
        for f in res.fields:
            status_flag = "✓" if f.value is not None else "∅ (None)"
            val_display = (f.value[:35] + "...") if f.value and len(f.value) > 35 else str(f.value)
            print(f"  {f.field_name:<20}: {val_display:<38} conf={f.confidence:.1f} [{status_flag}]")
        print()
