"""
escalation/confidence_router.py — Confidence Router & Escalation Logic (Unit 5).

Implements the strict 5-tier escalation hierarchy from ARCHITECTURE.md §3:
  1. missing_attachment — comparison request with < 2 attachments or missing SI/BL pair
  2. unreadable — 0-byte file, corrupted PDF/stream, or image-only scanned PDF without text layer
  3. wrong_doc_type — Commercial Invoice, Packing List, Certificate of Origin
  4. missing_value — required comparison field is null/blank or placeholder (e.g. '???', 'TBA', 'N/A')
  5. Clean comparison — compare normally -> OK or MISMATCH with defect_fields

Produces schema-valid SubmissionEntry objects.
"""

import logging
from pathlib import Path
from typing import Optional

from shared.schemas import (
    ClassificationResult,
    ExtractionResult,
    ComparisonResult,
    SubmissionEntry,
)
from extraction.text_parser import parse_text_document
from matching.ensemble_voter import compare_extractions
from matching.synonym_dict import CANONICAL_FIELDS

logger = logging.getLogger(__name__)


def load_and_extract_attachment(
    source_dir: str,
    att_path: str,
    email_id: str,
) -> ExtractionResult:
    """Read an attachment file and parse it into an ExtractionResult.
    Delegates to extraction.vision_pipeline.extract_document to handle plain-text,
    PDF, DOCX, XLSX, and all unreadable failure modes.
    """
    from extraction.vision_pipeline import extract_document
    expected_doc_type = "BL" if "_BL" in att_path.upper() else "SI"
    full_path = Path(source_dir) / att_path
    return extract_document(full_path, expected_doc_type, email_id)


def route_decision(
    email: dict,
    classification: ClassificationResult,
    extractions: dict[str, ExtractionResult],
    comparison: Optional[ComparisonResult] = None,
) -> SubmissionEntry:
    """Route an email to OK, MISMATCH, or NEEDS_REVIEW with the correct review_reason.

    Strict rule order:
      Rule 0: Non-comparison emails -> OK
      Rule 1: missing_attachment
      Rule 2: unreadable
      Rule 3: wrong_doc_type
      Rule 4: missing_value
      Rule 5: Compare normally -> OK or MISMATCH
    """
    category = classification.category

    # Rule 0: Non-comparison categories
    if category != "BL_COMPARISON":
        return SubmissionEntry(
            category=category,
            status="OK",
            review_reason=None,
            has_defect=False,
            defect_fields=[],
        )

    attachments = email.get("attachments", [])

    # Rule 1: missing_attachment
    if len(attachments) < 2:
        return SubmissionEntry(
            category="BL_COMPARISON",
            status="NEEDS_REVIEW",
            review_reason="missing_attachment",
            has_defect=False,
            defect_fields=[],
        )

    has_si_att = any("_SI" in a.upper() or "SHIPPING" in a.upper() for a in attachments)
    has_bl_att = any("_BL" in a.upper() or "LADING" in a.upper() for a in attachments)
    if not (has_si_att and has_bl_att):
        return SubmissionEntry(
            category="BL_COMPARISON",
            status="NEEDS_REVIEW",
            review_reason="missing_attachment",
            has_defect=False,
            defect_fields=[],
        )

    # Rule 2: unreadable
    for ext in extractions.values():
        if ext.doc_status == "unreadable":
            return SubmissionEntry(
                category="BL_COMPARISON",
                status="NEEDS_REVIEW",
                review_reason="unreadable",
                has_defect=False,
                defect_fields=[],
            )

    # Rule 3: wrong_doc_type
    for ext in extractions.values():
        if ext.doc_status == "wrong_doc_type":
            return SubmissionEntry(
                category="BL_COMPARISON",
                status="NEEDS_REVIEW",
                review_reason="wrong_doc_type",
                has_defect=False,
                defect_fields=[],
            )

    # Identify SI and BL extraction objects
    si_ext = next((ext for ext in extractions.values() if ext.doc_type == "SI"), None)
    bl_ext = next((ext for ext in extractions.values() if ext.doc_type == "BL"), None)

    if not si_ext or not bl_ext:
        return SubmissionEntry(
            category="BL_COMPARISON",
            status="NEEDS_REVIEW",
            review_reason="missing_attachment",
            has_defect=False,
            defect_fields=[],
        )

    # Rule 4: missing_value (any required field is null/blank or confidence == 0.0)
    for ext in (si_ext, bl_ext):
        fmap = {f.field_name: f for f in ext.fields}
        for fname in CANONICAL_FIELDS:
            f = fmap.get(fname)
            if not f or f.value is None or f.confidence == 0.0:
                return SubmissionEntry(
                    category="BL_COMPARISON",
                    status="NEEDS_REVIEW",
                    review_reason="missing_value",
                    has_defect=False,
                    defect_fields=[],
                )

    # Rule 5: Compare normally -> OK or MISMATCH
    if comparison is None:
        comparison = compare_extractions(si_ext, bl_ext)

    defects = [fc.field_name for fc in comparison.field_results if not fc.match]
    if defects:
        return SubmissionEntry(
            category="BL_COMPARISON",
            status="MISMATCH",
            review_reason=None,
            has_defect=True,
            defect_fields=sorted(defects),
        )
    else:
        return SubmissionEntry(
            category="BL_COMPARISON",
            status="OK",
            review_reason=None,
            has_defect=False,
            defect_fields=[],
        )


def build_escalation_evidence_for_route(
    email: dict,
    entry: SubmissionEntry,
    extractions: dict[str, ExtractionResult],
):
    """Construct a complete EscalationEvidence packet for a NEEDS_REVIEW decision per ARCHITECTURE.md §5."""
    from escalation.notifier import EscalationEvidence

    if entry.status != "NEEDS_REVIEW" or not entry.review_reason:
        return None

    email_id = email.get("email_id", "unknown")
    reason = entry.review_reason

    if reason == "missing_attachment":
        attachments = email.get("attachments", [])
        return EscalationEvidence(
            email_id=email_id,
            review_reason=reason,
            field="attachments",
            source_snippet=f"Found attachments: {attachments}. Expected paired Shipping Instruction (SI) and Bill of Lading (BL).",
            system_guess=None,
        )

    elif reason == "unreadable":
        for att_name, ext in extractions.items():
            if ext.doc_status == "unreadable":
                raw = getattr(ext, "raw_text", None)
                snippet = raw[:200] if raw else f"Attachment {att_name} is unreadable (corrupt, 0-byte, or scanned image)"
                return EscalationEvidence(
                    email_id=email_id,
                    review_reason=reason,
                    field="attachments",
                    source_snippet=snippet,
                    system_guess=None,
                )
        return EscalationEvidence(
            email_id=email_id,
            review_reason=reason,
            field="attachments",
            source_snippet="Document attachment unreadable or corrupted.",
            system_guess=None,
        )

    elif reason == "wrong_doc_type":
        for att_name, ext in extractions.items():
            if ext.doc_status == "wrong_doc_type":
                raw = getattr(ext, "raw_text", None)
                snippet = raw[:200] if raw else f"Attachment {att_name} is not SI/BL (e.g. Packing List, Invoice, Certificate)"
                return EscalationEvidence(
                    email_id=email_id,
                    review_reason=reason,
                    field="doc_type",
                    source_snippet=snippet,
                    system_guess=ext.doc_type or "OTHER",
                )
        return EscalationEvidence(
            email_id=email_id,
            review_reason=reason,
            field="doc_type",
            source_snippet="Attachment is neither Shipping Instruction nor Bill of Lading.",
            system_guess=None,
        )

    elif reason == "missing_value":
        for ext in extractions.values():
            if ext.doc_type in ("SI", "BL"):
                fmap = {f.field_name: f for f in ext.fields}
                for fname in CANONICAL_FIELDS:
                    f = fmap.get(fname)
                    if not f or f.value is None or f.confidence == 0.0:
                        snip = (
                            f.source_snippet
                            if (f and f.source_snippet)
                            else f"{ext.doc_type} missing required field '{fname}'."
                        )
                        return EscalationEvidence(
                            email_id=email_id,
                            review_reason=reason,
                            field=fname,
                            source_snippet=snip,
                            system_guess=str(f.value) if f and f.value else None,
                        )
        return EscalationEvidence(
            email_id=email_id,
            review_reason=reason,
            field=None,
            source_snippet="Required comparison field is null or unparseable.",
            system_guess=None,
        )

    return None


def process_email(
    dataset_source: str,
    email: dict,
    classification_override: Optional[ClassificationResult] = None,
) -> SubmissionEntry:
    """Run the complete pipeline on a single email record."""
    from agents.classifier import classify_email

    email_id = email["email_id"]

    # 1. Classify
    classification = classification_override or classify_email(email)

    # 2. Extract attachments if BL_COMPARISON
    extractions: dict[str, ExtractionResult] = {}
    if classification.category == "BL_COMPARISON":
        for att in email.get("attachments", []):
            ext = load_and_extract_attachment(dataset_source, att, email_id)
            extractions[att] = ext

    # 3. Route decision
    entry = route_decision(email, classification, extractions)
    return entry
