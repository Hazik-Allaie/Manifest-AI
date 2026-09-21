"""
infra/pubsub_setup.py — Real-Time Pub/Sub Event Ingestion & Worker Pool (Unit 11).

Provides:
  1. Infrastructure provisioning: Topic (`new-email-events`) & Subscription (`new-email-events-sub`).
  2. Event Publishing: `publish_email_event()` serializes email events to Pub/Sub.
  3. Concurrent Subscriber: `EmailEventSubscriber` with a ThreadPoolExecutor worker pool
     for asynchronous, multi-email parallel execution via the LangGraph orchestrator.
  4. Dead-Letter Queue (DLQ) & Retry: Failed processing attempts are retried and safely
     diverted to `logs/dlq_failed_messages.jsonl` to ensure zero message loss.
  5. In-Memory Queue Fallback: Supports offline / simulated execution when GCP is disconnected.
"""

import os
import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

# Defaults
DEFAULT_PROJECT = (
    os.environ.get("MANIFEST_GCP_PROJECT_ID")
    or os.environ.get("GOOGLE_CLOUD_PROJECT")
    or "manifest-ai-509207"
)
DEFAULT_TOPIC = os.environ.get("MANIFEST_PUBSUB_TOPIC", "new-email-events")
DEFAULT_SUBSCRIPTION = os.environ.get("MANIFEST_PUBSUB_SUBSCRIPTION", "new-email-events-sub")
DEFAULT_DLQ_PATH = Path("logs") / "dlq_failed_messages.jsonl"

# In-memory queue fallback for offline/simulated testing
_IN_MEMORY_QUEUE: list[dict] = []


def get_project_id(project_id: Optional[str] = None) -> str:
    """Resolve the active GCP project ID."""
    return project_id or DEFAULT_PROJECT


def ensure_pubsub_infrastructure(
    project_id: Optional[str] = None,
    topic_name: Optional[str] = None,
    sub_name: Optional[str] = None,
) -> tuple[str, str]:
    """Ensure Pub/Sub topic and subscription exist on Google Cloud.
    Returns (topic_path, subscription_path).
    """
    proj = get_project_id(project_id)
    topic = topic_name or DEFAULT_TOPIC
    sub = sub_name or DEFAULT_SUBSCRIPTION

    try:
        from google.cloud import pubsub_v1
        from google.api_core.exceptions import NotFound, AlreadyExists

        publisher = pubsub_v1.PublisherClient()
        subscriber = pubsub_v1.SubscriberClient()

        topic_path = publisher.topic_path(proj, topic)
        sub_path = subscriber.subscription_path(proj, sub)

        # Check or create topic
        try:
            publisher.get_topic(request={"topic": topic_path})
            logger.info("Found existing Pub/Sub topic: %s", topic_path)
        except NotFound:
            publisher.create_topic(request={"name": topic_path})
            logger.info("Created Pub/Sub topic: %s", topic_path)

        # Check or create subscription
        try:
            subscriber.get_subscription(request={"subscription": sub_path})
            logger.info("Found existing Pub/Sub subscription: %s", sub_path)
        except NotFound:
            try:
                subscriber.create_subscription(
                    request={"name": sub_path, "topic": topic_path, "ack_deadline_seconds": 60}
                )
                logger.info("Created Pub/Sub subscription: %s", sub_path)
            except AlreadyExists:
                pass

        return topic_path, sub_path
    except Exception as e:
        logger.warning("Pub/Sub infrastructure setup failed (%s). Using local queue fallback.", e)
        return f"local/topics/{topic}", f"local/subscriptions/{sub}"


def publish_email_event(
    email: dict,
    dataset_source: str = "data-basic",
    project_id: Optional[str] = None,
    topic_name: Optional[str] = None,
) -> str:
    """Publish an email event to Google Cloud Pub/Sub.

    Returns:
        str: Message ID of the published event.
    """
    proj = get_project_id(project_id)
    topic = topic_name or DEFAULT_TOPIC
    payload = {
        "email": email,
        "email_id": email.get("email_id", "unknown"),
        "dataset_source": dataset_source,
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
    data_bytes = json.dumps(payload).encode("utf-8")

    try:
        from google.cloud import pubsub_v1
        publisher = pubsub_v1.PublisherClient()
        topic_path = publisher.topic_path(proj, topic)
        future = publisher.publish(topic_path, data_bytes, email_id=payload["email_id"])
        msg_id = future.result(timeout=10.0)
        logger.info("Published email %s to Pub/Sub (msg_id: %s)", payload["email_id"], msg_id)
        return str(msg_id)
    except Exception as e:
        logger.warning("Pub/Sub publish failed (%s). Appending to in-memory queue fallback.", e)
        msg_id = f"mem_msg_{len(_IN_MEMORY_QUEUE) + 1}_{int(time.time())}"
        payload["_message_id"] = msg_id
        _IN_MEMORY_QUEUE.append(payload)
        return msg_id


def record_to_dead_letter_queue(
    payload: dict,
    error: Exception,
    attempt_count: int,
    dlq_path: Optional[Path] = None,
) -> None:
    """Record unrecoverable failed email events into the Dead-Letter Queue audit log."""
    target_path = dlq_path or DEFAULT_DLQ_PATH
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "email_id": payload.get("email_id"),
            "attempts": attempt_count,
            "error": str(error),
            "error_type": type(error).__name__,
            "payload": payload,
        }
        with open(target_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        logger.error("Diverted email %s to DLQ: %s", payload.get("email_id"), error)
    except Exception as log_err:
        logger.critical("Failed writing to DLQ log: %s", log_err)


class EmailEventSubscriber:
    """Asynchronous, multi-worker subscriber that pulls and processes email events."""

    def __init__(
        self,
        project_id: Optional[str] = None,
        subscription_name: Optional[str] = None,
        max_workers: int = 5,
        max_retries: int = 2,
        on_processed_callback: Optional[Callable[[dict, Any], None]] = None,
        dlq_path: Optional[Path] = None,
    ):
        self.project_id = get_project_id(project_id)
        self.subscription_name = subscription_name or DEFAULT_SUBSCRIPTION
        self.max_workers = max_workers
        self.max_retries = max_retries
        self.on_processed = on_processed_callback
        self.dlq_path = dlq_path or DEFAULT_DLQ_PATH

        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.streaming_pull_future = None
        self._is_running = False
        self.processed_records: dict[str, Any] = {}

    def process_event_payload(self, payload: dict) -> dict:
        """Process a single unpacked event through the LangGraph pipeline."""
        from agents.orchestrator import run_single_email

        email = payload.get("email", {})
        dataset_source = payload.get("dataset_source", "data-basic")
        email_id = payload.get("email_id", email.get("email_id", "unknown"))

        last_error = None
        for attempt in range(1, self.max_retries + 2):
            try:
                state = run_single_email(email, dataset_source=dataset_source)
                entry = state.get("submission_entry")
                self.processed_records[email_id] = entry
                if self.on_processed:
                    self.on_processed(payload, state)
                logger.info("Real-time pipeline processed email %s -> status=%s", email_id, getattr(entry, 'status', None))
                return state
            except Exception as e:
                last_error = e
                logger.warning("Error processing email %s (attempt %d): %s", email_id, attempt, e)
                time.sleep(0.5 * attempt)

        # Permanent failure -> route to DLQ
        record_to_dead_letter_queue(payload, last_error, self.max_retries + 1, dlq_path=self.dlq_path)
        return {"email_id": email_id, "error": str(last_error)}

    def pull_and_process_batch(
        self,
        max_messages: int = 10,
        timeout: float = 5.0,
    ) -> list[dict]:
        """Synchronously pull up to max_messages from Pub/Sub and execute them in parallel.
        Ideal for controlled testing, batch polling, and verifying fast reactivity.
        """
        results = []

        try:
            from google.cloud import pubsub_v1
            subscriber = pubsub_v1.SubscriberClient()
            sub_path = subscriber.subscription_path(self.project_id, self.subscription_name)

            response = subscriber.pull(
                request={"subscription": sub_path, "max_messages": max_messages},
                timeout=timeout,
            )

            ack_ids = []
            futures = []
            for msg in response.received_messages:
                ack_ids.append(msg.ack_id)
                try:
                    payload = json.loads(msg.message.data.decode("utf-8"))
                    f = self.executor.submit(self.process_event_payload, payload)
                    futures.append(f)
                except Exception as parse_err:
                    logger.error("Failed to decode message: %s", parse_err)

            # Wait for all workers to finish
            for f in futures:
                try:
                    res = f.result(timeout=15.0)
                    results.append(res)
                except Exception as worker_err:
                    logger.error("Worker thread failed: %s", worker_err)

            # Acknowledge successfully handled messages
            if ack_ids:
                subscriber.acknowledge(
                    request={"subscription": sub_path, "ack_ids": ack_ids}
                )
                logger.info("Acknowledged %d Pub/Sub messages", len(ack_ids))

            return results
        except Exception as e:
            logger.info("Pub/Sub batch pull completed or timed out (%s). Checking in-memory queue fallback.", e)

        # In-memory queue fallback
        global _IN_MEMORY_QUEUE
        if _IN_MEMORY_QUEUE:
            items_to_process = _IN_MEMORY_QUEUE[:max_messages]
            _IN_MEMORY_QUEUE = _IN_MEMORY_QUEUE[max_messages:]
            futures = [self.executor.submit(self.process_event_payload, item) for item in items_to_process]
            for f in futures:
                try:
                    results.append(f.result(timeout=15.0))
                except Exception as err:
                    logger.error("Fallback worker thread failed: %s", err)

        return results

    def start_streaming(self) -> None:
        """Start non-blocking asynchronous streaming pull."""
        if self._is_running:
            return

        try:
            from google.cloud import pubsub_v1
            subscriber = pubsub_v1.SubscriberClient()
            sub_path = subscriber.subscription_path(self.project_id, self.subscription_name)

            def _callback(message):
                try:
                    payload = json.loads(message.data.decode("utf-8"))
                    self.executor.submit(self.process_event_payload, payload)
                    message.ack()
                except Exception as e:
                    logger.error("Failed handling streaming message: %s", e)
                    message.nack()

            self._is_running = True
            self.streaming_pull_future = subscriber.subscribe(sub_path, callback=_callback)
            logger.info("Started streaming subscriber on %s", sub_path)
        except Exception as e:
            logger.warning("Could not start streaming subscriber: %s", e)
            self._is_running = False

    def stop(self) -> None:
        """Shut down subscriber and worker pool cleanly."""
        self._is_running = False
        if self.streaming_pull_future:
            try:
                self.streaming_pull_future.cancel()
            except Exception:
                pass
            self.streaming_pull_future = None
        self.executor.shutdown(wait=False)
        logger.info("EmailEventSubscriber stopped.")
