"""
infra/firestore_schema.py — Firestore Schema & Client for Human Feedback Loop (Unit 10).

Manages human operator corrections in the `corrections` collection:
  - HumanCorrection: Pydantic data model
  - save_correction(): Writes verified correction to Firestore
  - get_recent_corrections(): Retrieves latest corrections with in-memory TTL caching
  - clear_test_corrections(): Purges test documents
  - Graceful fallback: If Firestore is unavailable/offline, maintains an in-memory cache
"""

import os
import time
import logging
from datetime import datetime, timezone
from typing import Optional, Any
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

# Collection name per Unit 10 spec
CORRECTIONS_COLLECTION = "corrections"

# In-memory fallback and high-throughput TTL caching
_MEMORY_CORRECTIONS: list[dict] = []
_FIRESTORE_CLIENT: Optional[Any] = None
_CORRECTIONS_CACHE: Optional[list] = None
_CACHE_TIMESTAMP: float = 0.0
CACHE_TTL_SECONDS: float = 30.0


class HumanCorrection(BaseModel):
    """Schema for a verified human operator correction."""
    email_id: str
    field_name: str
    original_value: Optional[str] = None
    corrected_value: str
    review_reason: Optional[str] = None
    reason: Optional[str] = None
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


def get_firestore_client(force_refresh: bool = False) -> Optional[Any]:
    """Obtain or instantiate the Google Cloud Firestore client.
    Returns None if google-cloud-firestore is unavailable or credentials fail.
    """
    global _FIRESTORE_CLIENT
    if _FIRESTORE_CLIENT is not None and not force_refresh:
        return _FIRESTORE_CLIENT

    try:
        from google.cloud import firestore
        project = (
            os.environ.get("MANIFEST_GCP_PROJECT_ID")
            or os.environ.get("GOOGLE_CLOUD_PROJECT")
            or "manifest-ai-509207"
        )
        database = os.environ.get("MANIFEST_FIRESTORE_DB", "(default)")
        _FIRESTORE_CLIENT = firestore.Client(project=project, database=database)
        logger.info("Connected to Firestore project: %s (db: %s)", project, database)
        return _FIRESTORE_CLIENT
    except Exception as e:
        logger.warning("Unable to initialize live Firestore client: %s. Using in-memory fallback.", e)
        _FIRESTORE_CLIENT = None
        return None


def invalidate_corrections_cache() -> None:
    """Clear cached Firestore corrections."""
    global _CORRECTIONS_CACHE, _CACHE_TIMESTAMP
    _CORRECTIONS_CACHE = None
    _CACHE_TIMESTAMP = 0.0


def save_correction(
    correction: HumanCorrection,
    collection_name: str = CORRECTIONS_COLLECTION,
    client: Optional[Any] = None,
) -> str:
    """Save a human correction to Firestore (or in-memory fallback).
    Uses deterministic document ID {email_id}_{field_name} with .set() to cleanly overwrite
    previous corrections for the same email and field, preventing duplicates and stale values.

    Returns:
        str: The document ID of the saved correction.
    """
    global _MEMORY_CORRECTIONS
    invalidate_corrections_cache()
    data = correction.model_dump()
    fs_client = client or get_firestore_client()
    doc_id = f"{correction.email_id}_{correction.field_name}"

    if fs_client is not None:
        try:
            coll_ref = fs_client.collection(collection_name)
            doc_ref = coll_ref.document(doc_id)
            doc_ref.set(data)
            logger.info("Saved correction to Firestore [%s]: %s", doc_id, data)

            # Clean up any legacy random-ID documents for this email_id + field_name
            try:
                legacy_docs = list(
                    coll_ref.where("email_id", "==", correction.email_id)
                    .where("field_name", "==", correction.field_name)
                    .stream()
                )
                for ld in legacy_docs:
                    if ld.id != doc_id:
                        ld.reference.delete()
            except Exception as e_del:
                logger.debug("Legacy cleanup skipped: %s", e_del)

            return doc_id
        except Exception as e:
            logger.warning("Firestore save failed (%s), recording in memory fallback", e)

    # In-memory fallback: replace existing item if matching email_id + field_name
    _MEMORY_CORRECTIONS = [
        c for c in _MEMORY_CORRECTIONS
        if not (c.get("email_id") == correction.email_id and c.get("field_name") == correction.field_name)
    ]
    data_with_id = dict(data)
    data_with_id["_doc_id"] = doc_id
    _MEMORY_CORRECTIONS.append(data_with_id)
    return doc_id


def get_all_corrections_map(
    collection_name: str = CORRECTIONS_COLLECTION,
    client: Optional[Any] = None,
) -> dict[str, dict[str, dict]]:
    """Retrieve all human corrections from Firestore (or in-memory fallback),
    mapped by email_id -> field_name -> correction_dict.
    When multiple records exist for the same (email_id, field_name),
    the record with the most recent timestamp takes precedence.
    """
    fs_client = client or get_firestore_client()
    raw_list: list[dict] = []

    if fs_client is not None:
        try:
            coll_ref = fs_client.collection(collection_name)
            docs = list(coll_ref.stream())
            for doc in docs:
                d = doc.to_dict()
                if isinstance(d, dict) and "email_id" in d and "field_name" in d:
                    d["_doc_id"] = doc.id
                    raw_list.append(d)
        except Exception as e:
            logger.warning("Firestore get_all_corrections_map failed (%s), using memory", e)

    if not raw_list:
        raw_list = list(_MEMORY_CORRECTIONS)

    # Sort ascending by timestamp so later timestamps cleanly overwrite earlier ones
    raw_list.sort(key=lambda x: str(x.get("timestamp") or ""))

    result: dict[str, dict[str, dict]] = {}
    for item in raw_list:
        eid = item.get("email_id")
        fn = item.get("field_name")
        if not eid or not fn:
            continue
        if eid not in result:
            result[eid] = {}
        result[eid][fn] = item

    return result


def get_corrections_for_email(
    email_id: str,
    collection_name: str = CORRECTIONS_COLLECTION,
    client: Optional[Any] = None,
) -> dict[str, dict]:
    """Retrieve all active corrections for a specific email_id, mapped by field_name."""
    all_map = get_all_corrections_map(collection_name=collection_name, client=client)
    return all_map.get(email_id, {})


def get_recent_corrections(
    field_name: Optional[str] = None,
    limit: int = 5,
    collection_name: str = CORRECTIONS_COLLECTION,
    client: Optional[Any] = None,
    use_cache: bool = True,
) -> list[HumanCorrection]:
    """Fetch the most recent human corrections with in-memory TTL caching.

    Args:
        field_name: If specified, filters corrections to this canonical field name.
        limit: Maximum number of corrections to return.
        collection_name: Target collection.
        client: Optional explicit Firestore client.
        use_cache: Whether to leverage short-lived in-memory cache for high throughput.

    Returns:
        list[HumanCorrection]: Ordered from most recent to oldest.
    """
    global _CORRECTIONS_CACHE, _CACHE_TIMESTAMP

    now = time.time()
    if use_cache and _CORRECTIONS_CACHE is not None and (now - _CACHE_TIMESTAMP) < CACHE_TTL_SECONDS:
        cached = _CORRECTIONS_CACHE
        if field_name:
            cached = [c for c in cached if c.field_name == field_name]
        return cached[:limit]

    fs_client = client or get_firestore_client()
    results: list[HumanCorrection] = []

    if fs_client is not None:
        try:
            coll_ref = fs_client.collection(collection_name)
            docs = list(coll_ref.stream())
            for doc in docs:
                d = doc.to_dict()
                try:
                    results.append(HumanCorrection(**d))
                except Exception:
                    continue

            results.sort(key=lambda x: x.timestamp, reverse=True)
            _CORRECTIONS_CACHE = results
            _CACHE_TIMESTAMP = now

            filtered = results
            if field_name:
                filtered = [c for c in filtered if c.field_name == field_name]
            return filtered[:limit]
        except Exception as e:
            logger.warning("Firestore query failed (%s), querying memory fallback", e)

    # In-memory fallback
    mem_results = [HumanCorrection(**c) for c in _MEMORY_CORRECTIONS]
    mem_results.sort(key=lambda x: x.timestamp, reverse=True)
    _CORRECTIONS_CACHE = mem_results
    _CACHE_TIMESTAMP = now

    filtered = mem_results
    if field_name:
        filtered = [c for c in filtered if c.field_name == field_name]
    return filtered[:limit]


def clear_test_corrections(
    email_prefix: str = "test_",
    collection_name: str = CORRECTIONS_COLLECTION,
    client: Optional[Any] = None,
) -> int:
    """Purge test corrections matching email_prefix from Firestore and memory."""
    global _MEMORY_CORRECTIONS
    invalidate_corrections_cache()
    deleted_count = 0

    # Clean memory
    before_len = len(_MEMORY_CORRECTIONS)
    _MEMORY_CORRECTIONS = [
        c for c in _MEMORY_CORRECTIONS
        if not c.get("email_id", "").startswith(email_prefix)
    ]
    deleted_count += (before_len - len(_MEMORY_CORRECTIONS))

    # Clean Firestore
    fs_client = client or get_firestore_client()
    if fs_client is not None:
        try:
            coll_ref = fs_client.collection(collection_name)
            docs = list(coll_ref.stream())
            for doc in docs:
                d = doc.to_dict()
                if d.get("email_id", "").startswith(email_prefix):
                    doc.reference.delete()
                    deleted_count += 1
        except Exception as e:
            logger.warning("Failed to clean test records from Firestore: %s", e)

    return deleted_count
