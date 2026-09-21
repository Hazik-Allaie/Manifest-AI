"""
escalation/feedback_loop.py — Dynamic Few-Shot Prompt Injection & Human Feedback Loop (Unit 10).

Connects human operator feedback from the Firestore `corrections` collection back into
the extraction and comparison pipelines:
  1. Retrieves recent verified corrections from Firestore.
  2. Formats them into explicit few-shot instruction blocks for Gemini/LLM prompts.
  3. Provides deterministic fast-path overrides for known recurring errors.
  4. Delivers measurable behavior changes in extraction prompts based on human corrections.
"""

import logging
from typing import Optional, List
from shared.schemas import ExtractedField
from infra.firestore_schema import (
    HumanCorrection,
    get_recent_corrections,
    save_correction,
)

logger = logging.getLogger(__name__)


def submit_human_correction(
    email_id: str,
    field_name: str,
    corrected_value: str,
    original_value: Optional[str] = None,
    review_reason: Optional[str] = None,
    reason: Optional[str] = None,
) -> HumanCorrection:
    """Convenience helper to record a human correction and persist it to Firestore."""
    correction = HumanCorrection(
        email_id=email_id,
        field_name=field_name,
        original_value=original_value,
        corrected_value=corrected_value,
        review_reason=review_reason,
        reason=reason,
    )
    doc_id = save_correction(correction)
    logger.info("Human correction registered [%s]: %s -> %s", doc_id, field_name, corrected_value)
    return correction


def build_few_shot_guidance(
    relevant_fields: Optional[List[str]] = None,
    limit: int = 5,
    corrections: Optional[List[HumanCorrection]] = None,
) -> str:
    """Retrieve recent human corrections and format them into a few-shot prompt injection block.

    Args:
        relevant_fields: Optional list of field names to filter on.
        limit: Max corrections to include.
        corrections: Optional explicit list of corrections (bypasses Firestore query, useful for testing).

    Returns:
        str: Formatted markdown prompt section, or empty string if no corrections.
    """
    if corrections is None:
        try:
            corrections = get_recent_corrections(limit=limit * 2)
        except Exception as e:
            logger.warning("Failed to fetch recent corrections for few-shot injection: %s", e)
            corrections = []

    # Filter by relevant fields if specified
    if relevant_fields:
        relevant_set = set(relevant_fields)
        corrections = [c for c in corrections if c.field_name in relevant_set]

    corrections = corrections[:limit]
    if not corrections:
        return ""

    lines = [
        "",
        "### HUMAN OPERATOR CORRECTION EXAMPLES (PRIORITIZE THESE RULES):",
        "The following real human corrections override default interpretations:",
    ]
    for c in corrections:
        orig = f"'{c.original_value}'" if c.original_value else "missing/unparsed value"
        reason_str = f" [Reason: {c.reason}]" if c.reason else ""
        lines.append(
            f"- For field `{c.field_name}`: when raw text implies {orig}, the correct extracted value must be `{c.corrected_value}`{reason_str}."
        )
    lines.append("")
    return "\n".join(lines)


def inject_few_shot_into_extraction_prompt(
    base_prompt: str,
    relevant_fields: Optional[List[str]] = None,
    limit: int = 5,
    corrections: Optional[List[HumanCorrection]] = None,
) -> str:
    """Inject dynamic few-shot human correction guidance into an extraction prompt."""
    guidance = build_few_shot_guidance(
        relevant_fields=relevant_fields,
        limit=limit,
        corrections=corrections,
    )
    if not guidance:
        return base_prompt

    # Append guidance right before final instructions/JSON format directive
    return f"{base_prompt}\n{guidance}"


def apply_correction_overrides(
    fields: List[ExtractedField],
    corrections: Optional[List[HumanCorrection]] = None,
) -> List[ExtractedField]:
    """Fast-path deterministic feedback: if an extracted field value matches a known
    faulty pattern from human corrections, apply the human fix directly.

    Returns updated list of ExtractedField objects.
    """
    if corrections is None:
        try:
            corrections = get_recent_corrections(limit=20)
        except Exception:
            corrections = []

    if not corrections:
        return fields

    # Build mapping from (field_name, original_value) -> corrected_value
    override_map: dict[tuple[str, str], str] = {}
    for c in corrections:
        if c.original_value:
            override_map[(c.field_name, c.original_value.strip().lower())] = c.corrected_value

    updated: List[ExtractedField] = []
    for f in fields:
        val_str = str(f.value).strip().lower() if f.value is not None else ""
        key = (f.field_name, val_str)
        if key in override_map:
            corrected_val = override_map[key]
            logger.info(
                "Applied human correction override on %s: %s -> %s",
                f.field_name,
                f.value,
                corrected_val,
            )
            updated.append(
                ExtractedField(
                    field_name=f.field_name,
                    value=corrected_val,
                    source_snippet=f.source_snippet,
                    confidence=1.0,  # Human verified
                )
            )
        else:
            updated.append(f)

    return updated
