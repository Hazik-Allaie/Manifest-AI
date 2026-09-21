"""
tests/test_unit_11.py — Real-Time Architecture, Pub/Sub Ingestion & Scheduler Tests (Unit 11).

Verifies:
  1. Pub/Sub infrastructure provisioning (topic & subscription).
  2. Publishing 3 test messages to Pub/Sub and verifying real-time automatic pipeline ingestion within seconds.
  3. Asynchronous concurrent processing across worker threads.
  4. Dead-Letter Queue (DLQ) retry and error preservation.
  5. Cloud Scheduler polling fallback detecting backlog emails.
  6. Daily operational digest generation conforming to docs/DESIGN.md §2.8.
"""

import time
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from shared.schemas import ClassificationResult, SubmissionEntry
from infra.pubsub_setup import (
    ensure_pubsub_infrastructure,
    publish_email_event,
    record_to_dead_letter_queue,
    EmailEventSubscriber,
    _IN_MEMORY_QUEUE,
)
from infra.scheduler import (
    run_scheduler_polling_fallback,
    generate_daily_digest,
)


# ── Test 1: Infrastructure Provisioning ──────────────────────────────────────

def test_pubsub_infrastructure_provisioning():
    """Verify topic and subscription resolution on GCP or fallback."""
    topic_path, sub_path = ensure_pubsub_infrastructure()
    assert "topics/new-email-events" in topic_path or "local" in topic_path
    assert "subscriptions/new-email-events-sub" in sub_path or "local" in sub_path


# ── Test 2: Publish 3 Test Messages & Confirm Automatic Processing ──────────

def test_publish_and_subscribe_3_test_messages():
    """Publish 3 test messages and confirm subscriber processes them within seconds without manual triggers."""
    run_id = int(time.time())
    eid1 = f"test_rt_email_001_{run_id}"
    eid2 = f"test_rt_email_002_{run_id}"
    eid3 = f"test_rt_email_003_{run_id}"
    target_eids = {eid1, eid2, eid3}

    emails = [
        {
            "email_id": eid1,
            "subject": "Invoice Query - Ref INV-9901",
            "body": "Could you please clarify invoice line item 4? Attached is invoice query.",
            "attachments": [],
        },
        {
            "email_id": eid2,
            "subject": "Shipping Instruction Request for Booking BK-551",
            "body": "Kindly provide shipping instructions for container shipment scheduled next week.",
            "attachments": [],
        },
        {
            "email_id": eid3,
            "subject": "Spam Promotion - Unclaimed prize",
            "body": "Congratulations! Click here to claim your reward immediately.",
            "attachments": [],
        },
    ]

    start_time = time.time()

    # Step 1: Publish 3 test events
    published_ids = []
    for email in emails:
        msg_id = publish_email_event(email, dataset_source="data-basic")
        assert msg_id
        published_ids.append(msg_id)

    assert len(published_ids) == 3

    # Step 2: Initialize subscriber and process batch
    subscriber = EmailEventSubscriber(max_workers=3)
    results = []
    processed_eids = set()
    deadline = time.time() + 25.0
    while not target_eids.issubset(processed_eids) and time.time() < deadline:
        batch = subscriber.pull_and_process_batch(max_messages=5, timeout=3.0)
        for r in batch:
            eid = r.get("email_id")
            if eid in target_eids and eid not in processed_eids:
                processed_eids.add(eid)
                results.append(r)
        if not target_eids.issubset(processed_eids):
            time.sleep(0.5)

    elapsed = time.time() - start_time
    subscriber.stop()

    # Exit criteria: Pipeline reacts to published event within seconds, not minutes
    assert elapsed < 35.0, f"Processing took {elapsed:.2f}s, exceeding SLA"

    # Confirm all 3 processed
    assert target_eids.issubset(processed_eids)
    assert len(results) == 3

    for r in results:
        entry = r.get("submission_entry")
        assert entry is not None
        assert entry.status == "OK"
        assert entry.category in ("INVOICE_QUERY", "SI_REQUEST", "SPAM", "GENERAL")


# ── Test 3: Asynchronous Concurrent Worker Pool ──────────────────────────────

def test_async_concurrent_processing():
    """Verify multiple emails are processed simultaneously by the ThreadPoolExecutor worker pool."""
    active_threads = set()

    def tracking_worker(payload):
        import threading
        t_id = threading.get_ident()
        active_threads.add(t_id)
        time.sleep(0.1)  # Simulate brief processing latency
        return {"email_id": payload.get("email_id"), "thread": t_id}

    subscriber = EmailEventSubscriber(max_workers=4)
    # Monkey-patch process_event_payload to isolate concurrency mechanics
    with patch.object(subscriber, "process_event_payload", side_effect=tracking_worker):
        test_payloads = [{"email_id": f"test_concurrent_{i}"} for i in range(4)]
        futures = [subscriber.executor.submit(subscriber.process_event_payload, p) for p in test_payloads]
        done_results = [f.result(timeout=5.0) for f in futures]

    subscriber.stop()
    assert len(done_results) == 4
    # Multi-worker execution: more than 1 distinct worker thread engaged
    assert len(active_threads) >= 2


# ── Test 4: Dead-Letter Queue (DLQ) on Error ─────────────────────────────────

def test_dead_letter_queue_on_permanent_error(tmp_path):
    """Confirm failed processing attempts are retried and safely recorded to DLQ without data loss."""
    test_dlq_log = tmp_path / "test_dlq.jsonl"

    failing_payload = {
        "email_id": "test_dlq_fail_01",
        "email": {"email_id": "test_dlq_fail_01", "corrupt_data": True},
    }

    subscriber = EmailEventSubscriber(max_workers=1, max_retries=1, dlq_path=test_dlq_log)

    def raise_catastrophic_error(*args, **kwargs):
        raise RuntimeError("Catastrophic database / parsing error")

    with patch("agents.orchestrator.run_single_email", side_effect=raise_catastrophic_error):
        res = subscriber.process_event_payload(failing_payload)

    subscriber.stop()
    assert "error" in res
    assert "Catastrophic" in res["error"]

    # Verify DLQ audit log
    assert test_dlq_log.exists()
    lines = test_dlq_log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1
    dlq_record = json.loads(lines[-1])
    assert dlq_record["email_id"] == "test_dlq_fail_01"
    assert dlq_record["attempts"] == 2  # Initial + 1 retry
    assert dlq_record["error_type"] == "RuntimeError"


# ── Test 5: Scheduler Polling Fallback ────────────────────────────────────────

def test_scheduler_polling_fallback():
    """Verify scheduler polling finds unhandled backlog emails."""
    # Simulate an inbox where email_001, email_004, email_005 have already been processed
    already_processed = {"email_001", "email_004", "email_005"}

    results = run_scheduler_polling_fallback(
        dataset_source="data-basic",
        processed_ids=already_processed,
        max_emails_to_poll=2,
        publish_to_pubsub=False,
    )

    assert len(results) == 2
    polled_ids = [r["email_id"] for r in results]
    # Polling should have picked email_002 and email_003
    assert "email_001" not in polled_ids
    assert "email_002" in polled_ids or "email_003" in polled_ids


# ── Test 6: Daily Operations Digest Generator ────────────────────────────────

def test_daily_digest_generation(tmp_path):
    """Verify generate_daily_digest computes correct operational metrics per docs/DESIGN.md §2.8."""
    test_digest_file = tmp_path / "test_digest.json"

    sample_processed = {
        "email_101": SubmissionEntry(
            category="BL_COMPARISON",
            status="OK",
            has_defect=False,
        ),
        "email_102": SubmissionEntry(
            category="BL_COMPARISON",
            status="MISMATCH",
            has_defect=True,
            defect_fields=["container_count", "gross_weight_kg"],
        ),
        "email_103": SubmissionEntry(
            category="BL_COMPARISON",
            status="NEEDS_REVIEW",
            review_reason="missing_value",
        ),
        "email_104": SubmissionEntry(
            category="SI_REQUEST",
            status="OK",
        ),
        "email_105": SubmissionEntry(
            category="INVOICE_QUERY",
            status="OK",
        ),
    }

    digest = generate_daily_digest(
        processed_records=sample_processed,
        date_str="2026-09-20",
        output_path=test_digest_file,
    )

    assert digest["report_date"] == "2026-09-20"
    assert digest["total_emails_processed"] == 5
    assert digest["category_breakdown"]["BL_COMPARISON"] == 3
    assert digest["category_breakdown"]["SI_REQUEST"] == 1
    assert digest["category_breakdown"]["INVOICE_QUERY"] == 1
    assert digest["status_breakdown"]["OK"] == 3
    assert digest["status_breakdown"]["MISMATCH"] == 1
    assert digest["status_breakdown"]["NEEDS_REVIEW"] == 1
    assert digest["defects_detected_total"] == 1
    assert digest["defect_fields_breakdown"]["container_count"] == 1
    assert digest["defect_fields_breakdown"]["gross_weight_kg"] == 1
    assert digest["escalations_by_reason"]["missing_value"] == 1

    # Verify JSON file written to disk
    assert test_digest_file.exists()
    file_data = json.loads(test_digest_file.read_text(encoding="utf-8"))
    assert file_data["total_emails_processed"] == 5
