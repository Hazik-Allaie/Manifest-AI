"""
shared/schemas — Frozen data contract for Manifest AI.

These Pydantic models define the exact shapes that every module in the
pipeline reads and writes.  This file was created during Unit 0 and must
NOT be changed casually once other units depend on it.  Any proposed
change must be flagged to the team first (see docs/ANTIGRAVITY.md §2).

Source of truth: docs/ARCHITECTURE.md §2
"""

from pydantic import BaseModel
from typing import Literal, Optional


class ClassificationResult(BaseModel):
    email_id: str
    category: Literal["BL_COMPARISON", "SI_REQUEST", "INVOICE_QUERY", "GENERAL", "SPAM"]
    evidence: list[str]
    confidence: float


class ExtractedField(BaseModel):
    field_name: Literal[
        "shipper", "consignee", "notify_party", "port_of_loading",
        "port_of_discharge", "container_count", "gross_weight_kg"
    ]
    value: Optional[str]
    source_snippet: Optional[str]
    confidence: float


class ExtractionResult(BaseModel):
    email_id: str
    doc_type: Literal["SI", "BL"]
    fields: list[ExtractedField]
    doc_status: Literal["ok", "missing", "unreadable", "wrong_doc_type"] = "ok"


class FieldComparison(BaseModel):
    field_name: str
    si_value: Optional[str]
    bl_value: Optional[str]
    match: bool
    match_confidence: float


class ComparisonResult(BaseModel):
    email_id: str
    field_results: list[FieldComparison]
    overall_confidence: float


class SubmissionEntry(BaseModel):
    category: Literal["BL_COMPARISON", "SI_REQUEST", "INVOICE_QUERY", "GENERAL", "SPAM"]
    status: Optional[Literal["OK", "MISMATCH", "NEEDS_REVIEW"]] = None
    review_reason: Optional[Literal[
        "wrong_doc_type", "missing_attachment", "unreadable", "missing_value"
    ]] = None
    has_defect: bool = False
    defect_fields: list[str] = []
