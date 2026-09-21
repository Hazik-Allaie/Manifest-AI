"""
infra/scheduler.py — Cloud Scheduler Fallback & Daily Digest Generator (Unit 11).

Provides:
  1. Polling Fallback: `run_scheduler_polling_fallback()` checks inbox for emails not yet
     ingested via Pub/Sub and processes or publishes them to maintain 100% SLA.
  2. Daily Operations Digest: `generate_daily_digest()` computes operational metrics
     (category volume, defect counts, escalation reasons) and outputs a structured summary
     for the dashboard analytics panel (docs/DESIGN.md §2.8).
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any, Set, List

from shared.schemas import SubmissionEntry

logger = logging.getLogger(__name__)

DEFAULT_DIGEST_PATH = Path("logs") / "daily_digest.json"


def run_scheduler_polling_fallback(
    dataset_source: str = "data-basic",
    processed_ids: Optional[Set[str]] = None,
    max_emails_to_poll: int = 5,
    publish_to_pubsub: bool = False,
) -> List[Any]:
    """Scan inbox for unhandled emails that may have bypassed the Pub/Sub event stream.

    Args:
        dataset_source: Directory with inbox dataset.
        processed_ids: Set of email_ids already processed.
        max_emails_to_poll: Maximum backlog emails to ingest.
        publish_to_pubsub: If True, publishes to Pub/Sub; if False, runs pipeline directly.

    Returns:
        List of processed pipeline states or published message IDs.
    """
    from sdk.loader import Inbox
    from agents.orchestrator import run_single_email
    from infra.pubsub_setup import publish_email_event

    inbox = Inbox(dataset_source)
    known = processed_ids or set()
    unhandled = [e for e in inbox.emails() if e.get("email_id") not in known]

    if not unhandled:
        logger.info("Scheduler polling check: all emails in %s already processed.", dataset_source)
        return []

    targets = unhandled[:max_emails_to_poll]
    logger.info("Scheduler polling detected %d unhandled emails. Ingesting backlog...", len(targets))

    results = []
    for email in targets:
        eid = email.get("email_id")
        if publish_to_pubsub:
            msg_id = publish_email_event(email, dataset_source=dataset_source)
            results.append({"email_id": eid, "action": "published", "msg_id": msg_id})
        else:
            state = run_single_email(email, dataset_source=dataset_source)
            results.append(state)

    return results


def generate_daily_digest(
    processed_records: dict[str, Any],
    date_str: Optional[str] = None,
    output_path: Path = DEFAULT_DIGEST_PATH,
) -> dict:
    """Generate structured daily digest summary for operational oversight.

    Args:
        processed_records: Mapping of email_id -> SubmissionEntry (or dict).
        date_str: Optional date string (defaults to today UTC: YYYY-MM-DD).
        output_path: Destination JSON file.

    Returns:
        dict: Complete daily analytics digest.
    """
    today = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    total_emails = len(processed_records)
    categories: dict[str, int] = {}
    statuses: dict[str, int] = {}
    defects_count = 0
    defect_fields_tally: dict[str, int] = {}
    escalation_reasons: dict[str, int] = {}

    for eid, record in processed_records.items():
        if isinstance(record, SubmissionEntry):
            d = record.model_dump()
        elif hasattr(record, "submission_entry") and record["submission_entry"]:
            entry = record["submission_entry"]
            d = entry.model_dump() if hasattr(entry, "model_dump") else dict(entry)
        elif isinstance(record, dict):
            d = record
        else:
            continue

        cat = d.get("category", "UNKNOWN")
        categories[cat] = categories.get(cat, 0) + 1

        stat = d.get("status")
        if stat:
            statuses[stat] = statuses.get(stat, 0) + 1

        if d.get("has_defect"):
            defects_count += 1
            for f in d.get("defect_fields", []):
                defect_fields_tally[f] = defect_fields_tally.get(f, 0) + 1

        reason = d.get("review_reason")
        if reason:
            escalation_reasons[reason] = escalation_reasons.get(reason, 0) + 1

    digest = {
        "report_date": today,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_emails_processed": total_emails,
        "category_breakdown": categories,
        "status_breakdown": statuses,
        "defects_detected_total": defects_count,
        "defect_fields_breakdown": defect_fields_tally,
        "escalations_by_reason": escalation_reasons,
    }

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(digest, indent=2), encoding="utf-8")
        logger.info("Saved daily digest to %s", output_path)
    except Exception as e:
        logger.warning("Failed writing daily digest file: %s", e)

    return digest
