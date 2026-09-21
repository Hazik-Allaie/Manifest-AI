"""
matching/ensemble_voter.py — Field Comparator with Fuzzy Matching (Unit 4).

Takes two ExtractionResult objects (SI and BL) and compares their fields
with field-specific normalisation and fuzzy matching:
  - Shipper, Consignee, Notify Party: case-folding, entity suffix standardization, Levenshtein ratio.
  - Ports (POL, POD): port name normalization and UN/LOCODE alignment.
  - Container Count: numeric count and container type/size parsing.
  - Gross Weight: numeric weight in KG with tolerance for formatting/rounding differences.

Returns a schema-valid ComparisonResult containing per-field FieldComparison items
and an overall comparison confidence score.
"""

import re
import logging
import unicodedata
from typing import Optional
import Levenshtein

from shared.schemas import ExtractionResult, ExtractedField, FieldComparison, ComparisonResult
from matching.synonym_dict import CANONICAL_FIELDS

logger = logging.getLogger(__name__)


def clean_normalized_text(text: Optional[str]) -> str:
    """Normalize text by stripping unicode variations, trimming, and collapsing whitespace."""
    if not text:
        return ""
    norm = unicodedata.normalize("NFKC", str(text))
    # Replace non-breaking spaces and other whitespace variations with standard space
    norm = re.sub(r"[\s\u00a0\u2000-\u200b\u202f\u205f\u3000]+", " ", norm)
    return norm.strip().lower()


# ── Entity Normalization (shipper, consignee, notify_party) ───────────────

def normalize_entity(text: Optional[str]) -> str:
    """Normalize company / entity names:
    - strip and lowercase
    - normalize business suffixes (SDN BHD, PTE LTD, PTY LTD, LLC, GMBH, etc.)
    - remove punctuation and collapse extra whitespace
    """
    if not text:
        return ""
    s = text.strip().lower()
    # Normalize common business entity designations
    s = re.sub(r"\b(sdn\.?\s*bhd\.?|berhad)\b", "sdn bhd", s)
    s = re.sub(r"\b(pte\.?\s*ltd\.?|private limited)\b", "pte ltd", s)
    s = re.sub(r"\b(pty\.?\s*ltd\.?|proprietary limited)\b", "pty ltd", s)
    s = re.sub(r"\b(co\.?,?\s*ltd\.?|company limited)\b", "co ltd", s)
    s = re.sub(r"\b(llc|l\.l\.c\.)\b", "llc", s)
    s = re.sub(r"\b(fze|f\.z\.e\.)\b", "fze", s)
    s = re.sub(r"\b(gmbh)\b", "gmbh", s)
    # Remove punctuation
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def compare_entities(si_val: Optional[str], bl_val: Optional[str]) -> tuple[bool, float]:
    """Compare two entity names using normalized string equality and Levenshtein distance."""
    if si_val is None and bl_val is None:
        return True, 1.0
    if si_val is None or bl_val is None:
        return False, 0.0

    norm_si = normalize_entity(si_val)
    norm_bl = normalize_entity(bl_val)

    if norm_si == norm_bl:
        return True, 1.0

    # Substring containment check: e.g. "APRIL FINE PAPER TRADING" inside longer trading arm
    if norm_si and norm_bl and (norm_si in norm_bl or norm_bl in norm_si):
        min_len = min(len(norm_si), len(norm_bl))
        max_len = max(len(norm_si), len(norm_bl))
        if min_len / max_len >= 0.70:
            return True, round(min_len / max_len, 3)

    ratio = Levenshtein.ratio(norm_si, norm_bl)
    # Tolerance threshold for typos or minor variations
    if ratio >= 0.88:
        return True, round(ratio, 3)

    return False, round(1.0 - ratio, 3)


# ── Port Normalization (port_of_loading, port_of_discharge) ───────────────

def normalize_port(text: Optional[str]) -> tuple[str, Optional[str]]:
    """Extract (normalized_port_name, un_locode).
    e.g. 'PORT KLANG (WESTPORT), MALAYSIA (MYPKG)' -> ('port klang westport malaysia', 'MYPKG')
    """
    if not text:
        return "", None
    s = unicodedata.normalize("NFKC", str(text)).strip().upper()
    # Extract UN/LOCODE if in parentheses at the end: e.g. (MYPKG), (PECLL)
    code_match = re.search(r"\(([A-Z]{5})\)\s*$", s)
    code = code_match.group(1) if code_match else None
    if code:
        s = s[:code_match.start()].strip()
    # Remove punctuation and collapse spaces
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s, code


def compare_ports(si_val: Optional[str], bl_val: Optional[str]) -> tuple[bool, float]:
    """Compare two ports based on port name and UN/LOCODE."""
    if si_val is None and bl_val is None:
        return True, 1.0
    if si_val is None or bl_val is None:
        return False, 0.0

    # Fast-path for identical strings after unicode & whitespace normalization
    if clean_normalized_text(si_val) == clean_normalized_text(bl_val):
        return True, 1.0

    name_si, code_si = normalize_port(si_val)
    name_bl, code_bl = normalize_port(bl_val)

    if name_si == name_bl:
        return True, 1.0

    # Token overlap check: if the main city/port matches
    tokens_si = set(name_si.split())
    tokens_bl = set(name_bl.split())
    common = tokens_si & tokens_bl
    # Common ports have multiple tokens (e.g. "port klang", "nhava sheva", "singapore")
    if len(common) >= 2 or (len(common) == 1 and any(len(t) >= 6 for t in common)):
        jaccard = len(common) / len(tokens_si | tokens_bl)
        if jaccard >= 0.50:
            return True, round(jaccard, 3)

    ratio = Levenshtein.ratio(name_si, name_bl)
    if ratio >= 0.85:
        return True, round(ratio, 3)

    return False, round(1.0 - ratio, 3)


# ── Container Count Normalization (container_count) ───────────────────────

def parse_container_info(text: Optional[str]) -> tuple[Optional[int], Optional[str]]:
    """Extract (count_int, size_normalized).
    e.g. '6 x 40\\'HC' -> (6, '40HC')
    """
    if not text:
        return None, None
    s = text.strip()
    m = re.match(r"^(\d+)\s*(?:x|\*|containers? of)?\s*(.*)$", s, re.IGNORECASE)
    if m:
        count = int(m.group(1))
        size_raw = m.group(2).strip()
        size = re.sub(r"[^\w]", "", size_raw).upper() if size_raw else None
        return count, size

    m_int = re.search(r"\b(\d+)\b", s)
    if m_int:
        return int(m_int.group(1)), None

    return None, None


def compare_container_counts(si_val: Optional[str], bl_val: Optional[str]) -> tuple[bool, float]:
    """Compare container count and container specifications."""
    if si_val is None and bl_val is None:
        return True, 1.0
    if si_val is None or bl_val is None:
        return False, 0.0

    count_si, size_si = parse_container_info(si_val)
    count_bl, size_bl = parse_container_info(bl_val)

    if count_si is None or count_bl is None:
        eq = si_val.strip().lower() == bl_val.strip().lower()
        return eq, 1.0 if eq else 0.0

    if count_si != count_bl:
        return False, 0.95

    # If count matches, check size if both specify size
    if size_si and size_bl:
        if size_si == size_bl:
            return True, 1.0
        else:
            return False, 0.90

    return True, 1.0


# ── Gross Weight Normalization (gross_weight_kg) ──────────────────────────

def parse_gross_weight(text: Optional[str]) -> Optional[float]:
    """Extract numeric weight in KG as float.
    Handles commas, spaces, 'KG', 'KGS', and MT conversion if applicable.
    """
    if not text:
        return None
    s = text.replace(",", "").replace(" ", "").upper()
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    if m:
        val = float(m.group(1))
        # Handle cases where weight is given in Metric Tonnes
        if "MT" in s and "KGS" not in s and "KG" not in s:
            val = val * 1000.0
        return val
    return None


def compare_gross_weights(si_val: Optional[str], bl_val: Optional[str]) -> tuple[bool, float]:
    """Compare gross weight with tolerance for minor rounding."""
    if si_val is None and bl_val is None:
        return True, 1.0
    if si_val is None or bl_val is None:
        return False, 0.0

    w_si = parse_gross_weight(si_val)
    w_bl = parse_gross_weight(bl_val)

    if w_si is None or w_bl is None:
        eq = si_val.strip().lower() == bl_val.strip().lower()
        return eq, 1.0 if eq else 0.0

    diff = abs(w_si - w_bl)
    # Tolerant threshold: <= 5 kg or <= 0.1%
    if diff <= 5.0 or (max(w_si, w_bl) > 0 and (diff / max(w_si, w_bl)) < 0.001):
        return True, 1.0

    return False, 0.95


# ── Generic / Routing Comparison ──────────────────────────────────────────

def compare_field(field_name: str, si_val: Optional[str], bl_val: Optional[str]) -> FieldComparison:
    """Compare a single field value between SI and BL with field-specific logic."""
    # Fast path: if both values are identical after unicode normalization and whitespace collapsing
    if si_val is not None and bl_val is not None:
        if clean_normalized_text(si_val) == clean_normalized_text(bl_val):
            return FieldComparison(
                field_name=field_name,
                si_value=si_val,
                bl_value=bl_val,
                match=True,
                match_confidence=1.0,
            )

    if field_name in ("shipper", "consignee", "notify_party"):
        match, conf = compare_entities(si_val, bl_val)
    elif field_name in ("port_of_loading", "port_of_discharge"):
        match, conf = compare_ports(si_val, bl_val)
    elif field_name == "container_count":
        match, conf = compare_container_counts(si_val, bl_val)
    elif field_name == "gross_weight_kg":
        match, conf = compare_gross_weights(si_val, bl_val)
    else:
        # Fallback to normalized string comparison
        s_si = (si_val or "").strip().lower()
        s_bl = (bl_val or "").strip().lower()
        match = (s_si == s_bl)
        conf = 1.0 if match else 0.5

    return FieldComparison(
        field_name=field_name,
        si_value=si_val,
        bl_value=bl_val,
        match=match,
        match_confidence=conf,
    )


def are_values_equivalent(field_name: str, val1: Optional[str], val2: Optional[str]) -> bool:
    """Check if two values for a field are equivalent using domain normalizers."""
    return compare_field(field_name, val1, val2).match


# ── 3-Method Ensemble & Weighted Voting (Unit 9) ──────────────────────────

DEFAULT_METHOD_WEIGHTS: dict[str, float] = {
    "structure": 0.40,  # Template / structured key-value parser
    "regex": 0.35,      # Regex / token pattern parser
    "ner": 0.25,        # Named entity recognition / semantic extractor
}


def weighted_ensemble_vote(
    field_name: str,
    predictions: list[tuple[str, Optional[str], float]],
    method_weights: Optional[dict[str, float]] = None,
) -> tuple[Optional[str], float, dict]:
    """Combine field extractions from multiple methods using weighted voting.

    Args:
        field_name: Canonical field name.
        predictions: List of (method_name, extracted_value, method_confidence).
        method_weights: Optional weight dictionary (defaults to DEFAULT_METHOD_WEIGHTS).

    Returns:
        tuple (consensus_value, adjusted_confidence, audit_metadata).
        Disagreements between methods lower the confidence score.
    """
    weights = method_weights or DEFAULT_METHOD_WEIGHTS
    valid_preds = [p for p in predictions if p[1] is not None and str(p[1]).strip() != ""]

    if not valid_preds:
        return None, 0.0, {"agreement": 0.0, "status": "no_predictions"}

    # Check if all valid methods agree
    first_val = valid_preds[0][1]
    all_agree = all(are_values_equivalent(field_name, first_val, p[1]) for p in valid_preds)

    if all_agree and len(valid_preds) == len(predictions):
        mean_conf = sum(p[2] for p in valid_preds) / len(valid_preds)
        return first_val, round(mean_conf, 3), {"agreement": 1.0, "status": "unanimous"}

    # Cluster equivalent values
    clusters: list[list[tuple[str, str, float]]] = []
    for pred in valid_preds:
        m, val, conf = pred
        placed = False
        for c in clusters:
            if are_values_equivalent(field_name, c[0][1], val):
                c.append(pred)
                placed = True
                break
        if not placed:
            clusters.append([pred])

    # Score clusters by sum of (weight * confidence)
    total_weight = sum(weights.get(p[0], 0.33) for p in predictions)
    cluster_scores = []
    for c in clusters:
        score = sum(weights.get(p[0], 0.33) * p[2] for p in c)
        cluster_scores.append((score, c))

    cluster_scores.sort(key=lambda x: x[0], reverse=True)
    best_score, best_cluster = cluster_scores[0]

    # Pick candidate with highest method confidence in winning cluster
    best_candidate = max(best_cluster, key=lambda p: p[2])[1]

    # Agreement ratio determines confidence penalty
    agreement_ratio = best_score / total_weight if total_weight > 0 else 0.0
    adjusted_conf = round(min(1.0, max(0.1, agreement_ratio)), 3)

    audit = {
        "agreement": round(agreement_ratio, 3),
        "cluster_count": len(clusters),
        "winning_methods": [p[0] for p in best_cluster],
        "status": "majority" if len(best_cluster) > 1 else "disputed",
    }
    return best_candidate, adjusted_conf, audit



def compare_extractions(si_result: ExtractionResult, bl_result: ExtractionResult) -> ComparisonResult:
    """Compare two ExtractionResults (SI and BL) across all canonical fields.

    Args:
        si_result: ExtractionResult for Shipping Instruction.
        bl_result: ExtractionResult for Bill of Lading.

    Returns:
        Validated ComparisonResult with per-field comparisons and overall confidence.
    """
    si_fields = {f.field_name: f.value for f in si_result.fields}
    bl_fields = {f.field_name: f.value for f in bl_result.fields}

    field_results: list[FieldComparison] = []
    for fname in CANONICAL_FIELDS:
        fc = compare_field(fname, si_fields.get(fname), bl_fields.get(fname))
        field_results.append(fc)

    # Calculate overall confidence as mean of field match confidences
    overall_conf = round(
        sum(fc.match_confidence for fc in field_results) / len(field_results)
        if field_results else 0.0,
        3,
    )

    email_id = si_result.email_id or bl_result.email_id
    result = ComparisonResult(
        email_id=email_id,
        field_results=field_results,
        overall_confidence=overall_conf,
    )
    return result


if __name__ == "__main__":
    print("Testing field comparison helper functions...")
    print("Entity match:", compare_entities("APRIL FAR EAST (M) SDN BHD", "APRIL FAR EAST (M) SDN. BHD."))
    print("Entity mismatch:", compare_entities("EAST BRIGHT FZ-LLC", "UAB NOVAKOPA"))
    print("Port match:", compare_ports("PORT KLANG (WESTPORT), MALAYSIA (MYPKG)", "PORT KLANG, MALAYSIA"))
    print("Port mismatch:", compare_ports("MOMBASA, KENYA (KEMBA)", "TUTICORIN, INDIA (KEMBA)"))
    print("Container match:", compare_container_counts("6 x 40'HC", "6 x 40' HC"))
    print("Container mismatch:", compare_container_counts("6 x 20'GP", "5 x 20'GP"))
    print("Weight match:", compare_gross_weights("21,577 KG", "21577 kgs"))
    print("Weight mismatch:", compare_gross_weights("21,114 KG", "23,114 KG"))
