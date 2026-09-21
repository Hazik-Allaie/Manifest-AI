"""
matching/synonym_dict.py — Hardcoded synonym dictionary for field label matching (Unit 3).

Maps diverse raw document field labels (e.g. 'Load Port', 'Port of Loading (POL)',
'To the Order of') to canonical field names.

Unit 3 implements the dictionary tier. Embeddings fallback will be added in Unit 9.
"""

import re
from typing import Optional

# ── 7 Canonical comparison fields ─────────────────────────────────────────
CANONICAL_FIELDS: list[str] = [
    "shipper",
    "consignee",
    "notify_party",
    "port_of_loading",
    "port_of_discharge",
    "container_count",
    "gross_weight_kg",
]

# ── Synonym dictionary ────────────────────────────────────────────────────
# Maps normalized (lowercase, space-collapsed, stripped of trailing colons) labels
SYNONYM_DICT: dict[str, str] = {
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
    "gross wt": "gross_weight_kg",
    "total gross weight": "gross_weight_kg",
    "gross wt kgs": "gross_weight_kg",
    "gross weight (kgs)": "gross_weight_kg",

    # Metadata fields (common shipping document fields)
    "vessel": "vessel",
    "ocean vessel": "vessel",
    "vessel name": "vessel",
    "export carrier (vessel, voyage)": "vessel",
    "voyage": "voyage",
    "voyage no.": "voyage",
    "voy.": "voyage",
    "voy. no": "voyage",
    "commodity": "commodity",
    "description of goods": "commodity",
    "description": "commodity",
    "kinds of packages; description of goods": "commodity",
    "booking reference": "booking_no",
    "booking no.": "booking_no",
    "booking ref": "booking_no",
    "booking no": "booking_no",
    "b/l no.": "bl_no",
    "bl no.": "bl_no",
    "bill of lading no.": "bl_no",
    "b/l number": "bl_no",
}

# Known document labels that are NOT canonical fields and should not be embedded
NON_CANONICAL_METADATA_LABELS: set[str] = {
    "freight",
    "freight prepaid",
    "freight collect",
    "hs code",
    "oc no.",
    "order no.",
    "net weight",
    "payment terms",
    "incoterms",
    "invoice amount",
}


def normalize_label(label: str) -> str:
    """Normalize a raw field label:
    - strip whitespace
    - strip trailing colons
    - collapse internal whitespace
    - lowercase
    """
    if not label:
        return ""
    s = label.strip()
    if s.endswith(":"):
        s = s[:-1].strip()
    s = re.sub(r"\s+", " ", s)
    return s.lower()


def match_field_label(label: str, use_embeddings: bool = True) -> Optional[str]:
    """Map a raw field label to its canonical field name.

    Args:
        label: Raw label string (e.g. 'Load Port', 'Port of Loading (POL):', 'To the Order of').
        use_embeddings: If True, falls back to semantic embeddings (Unit 9) when
                        the label is not in the synonym dictionary.

    Returns:
        Canonical field name (e.g. 'port_of_loading'), or None if unrecognized.
    """
    if not label:
        return None
    norm = normalize_label(label)
    if norm in NON_CANONICAL_METADATA_LABELS:
        return None

    match = SYNONYM_DICT.get(norm, None)
    if match is not None:
        return match

    if use_embeddings:
        try:
            from matching.embeddings import match_field_embedding
            emb_field, score = match_field_embedding(label, threshold=0.72)
            return emb_field
        except Exception as e:
            logger.debug("Embeddings fallback error for '%s': %s", label, e)

    return None


def get_synonyms_for_field(canonical_field: str) -> list[str]:
    """Return all known raw label variants for a given canonical field."""
    return [raw for raw, canonical in SYNONYM_DICT.items() if canonical == canonical_field]


if __name__ == "__main__":
    test_labels = [
        "Load Port",
        "Port of Loading (POL):",
        "POL",
        "To the Order of",
        "Consignee (Non-Negotiable)",
        "Gross Wt (kgs):",
        "Gross Weight毛重(KGS)",
        "No. of Containers or Packages",
        "Discharge Port",
        "POD:",
        "Notify Party/Intermediate Consignee",
        "Shipper/Exporter:",
        "Unknown Label",
    ]
    print(f"{'Raw Label':<40} -> {'Canonical Field':<20}")
    print("-" * 65)
    for lbl in test_labels:
        matched = match_field_label(lbl)
        print(f"{lbl:<40} -> {str(matched):<20}")
