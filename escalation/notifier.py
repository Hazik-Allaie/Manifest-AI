"""
escalation/notifier.py — Human Escalation Notifier & Evidence Packet (Unit 10).

Responsible for:
  1. Constructing structured EscalationEvidence packets conforming to ARCHITECTURE.md §5:
     - email_id
     - review_reason
     - field
     - source_snippet
     - system_guess
     - timestamp
  2. Formatting rich Discord embeds for human reviewers.
  3. Dispatching webhook notifications (Discord / Slack / webhook) with resilient error handling.
  4. Persisting audit records to a durable local log (logs/escalations.jsonl).
"""

import os
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

# Default audit log location
DEFAULT_LOG_PATH = Path("logs") / "escalations.jsonl"


class EscalationEvidence(BaseModel):
    """Structured escalation packet defined in ARCHITECTURE.md §5."""
    email_id: str
    review_reason: str
    field: Optional[str] = None
    source_snippet: Optional[str] = None
    system_guess: Optional[str] = None
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


def build_escalation_evidence(
    email_id: str,
    review_reason: str,
    field: Optional[str] = None,
    source_snippet: Optional[str] = None,
    system_guess: Optional[str] = None,
) -> EscalationEvidence:
    """Convenience factory for EscalationEvidence."""
    return EscalationEvidence(
        email_id=email_id,
        review_reason=review_reason,
        field=field,
        source_snippet=source_snippet,
        system_guess=system_guess,
    )


def format_discord_payload(evidence: EscalationEvidence) -> dict:
    """Format an EscalationEvidence packet as a Discord webhook embed."""
    reason_colors = {
        "missing_attachment": 16753920,  # Orange (0xFFA500)
        "unreadable": 15158332,          # Red (0xE74C3C)
        "wrong_doc_type": 10181046,      # Purple (0x9B59B6)
        "missing_value": 3447003,        # Blue (0x3498DB)
    }
    color = reason_colors.get(evidence.review_reason, 15158332)

    fields = [
        {"name": "Email ID", "value": f"`{evidence.email_id}`", "inline": True},
        {"name": "Review Reason", "value": f"`{evidence.review_reason}`", "inline": True},
        {"name": "Field", "value": f"`{evidence.field}`" if evidence.field else "*N/A*", "inline": True},
        {"name": "System Guess", "value": f"`{evidence.system_guess}`" if evidence.system_guess is not None else "*None*", "inline": True},
    ]

    if evidence.source_snippet:
        snippet_text = evidence.source_snippet[:800]
        fields.append({
            "name": "Source Snippet",
            "value": f"```text\n{snippet_text}\n```",
            "inline": False,
        })

    embed = {
        "title": f"🚨 Manifest AI Escalation: {evidence.review_reason}",
        "description": f"Human review required for email `{evidence.email_id}`.",
        "color": color,
        "fields": fields,
        "footer": {
            "text": f"Manifest AI Pipeline • {evidence.timestamp}"
        },
    }

    return {
        "username": "Manifest AI Dispatcher",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/10336/10336582.png",
        "embeds": [embed],
    }


def record_escalation_audit(
    evidence: EscalationEvidence,
    log_path: Path = DEFAULT_LOG_PATH,
) -> None:
    """Append the escalation evidence record to a durable JSONL audit log."""
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(evidence.model_dump()) + "\n")
    except Exception as e:
        logger.warning("Failed to record escalation audit log: %s", e)


def send_escalation_notification(
    evidence: EscalationEvidence,
    webhook_url: Optional[str] = None,
    log_path: Path = DEFAULT_LOG_PATH,
    timeout_seconds: float = 5.0,
) -> bool:
    """Dispatch an escalation notification and record audit log.

    1. Always writes to durable audit log `logs/escalations.jsonl`.
    2. If webhook_url (or env var DISCORD_WEBHOOK) is available, posts to Discord.
    3. Resilient: network/webhook failures never raise exceptions in the pipeline.

    Returns:
        bool: True if audit was logged and (if webhook provided) delivered.
    """
    # Step 1: Durable audit logging
    record_escalation_audit(evidence, log_path)

    # Step 2: Webhook dispatch
    target_url = (
        webhook_url
        or os.environ.get("MANIFEST_DISCORD_WEBHOOK")
        or os.environ.get("DISCORD_WEBHOOK")
    )
    if not target_url or not target_url.strip():
        logger.info(
            "Escalation recorded for %s (%s). No webhook URL configured.",
            evidence.email_id,
            evidence.review_reason,
        )
        return True

    payload = format_discord_payload(evidence)
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            target_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Manifest-AI-Notifier/1.0",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            status_code = resp.status
            if 200 <= status_code < 300:
                logger.info(
                    "Escalation notification dispatched for %s (status %d)",
                    evidence.email_id,
                    status_code,
                )
                return True
            else:
                logger.warning(
                    "Webhook returned non-2xx status code: %d",
                    status_code,
                )
                return False
    except Exception as e:
        logger.warning(
            "Failed to send webhook notification for %s: %s",
            evidence.email_id,
            e,
        )
        return False
