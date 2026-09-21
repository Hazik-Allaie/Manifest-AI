"""
matching/embeddings.py — Semantic Field Matching via Vertex AI Embeddings (Unit 9).

Provides fallback semantic similarity matching using text-embedding-004 when
the hardcoded synonym dictionary (Unit 3) does not recognize a field label.
"""

import math
import logging
from typing import Optional
from google import genai

from shared.config import GCP_PROJECT_ID
from matching.synonym_dict import CANONICAL_FIELDS

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "text-embedding-004"

# Exemplar phrases representing each canonical field
CANONICAL_FIELD_EXEMPLARS: dict[str, list[str]] = {
    "shipper": [
        "shipper",
        "shipper/exporter",
        "shipper (principal or seller)",
        "consignor",
        "seller",
        "exporter",
        "loading party",
        "supplier",
    ],
    "consignee": [
        "consignee",
        "consignee (non-negotiable)",
        "to the order of",
        "buyer",
        "receiver",
        "recipient",
        "delivered to",
        "receiver of goods",
    ],
    "notify_party": [
        "notify party",
        "notify party/intermediate consignee",
        "notify",
        "intermediate consignee",
        "secondary notify",
        "also notify",
    ],
    "port_of_loading": [
        "port of loading",
        "port of loading (pol)",
        "load port",
        "pol",
        "departure port",
        "place of receipt",
        "origin port",
        "place of departure",
    ],
    "port_of_discharge": [
        "port of discharge",
        "port of discharge (pod)",
        "discharge port",
        "pod",
        "destination port",
        "port of delivery",
        "arrival port",
        "target destination harbor",
    ],
    "container_count": [
        "container count",
        "no. of containers",
        "total containers",
        "no. of containers or packages",
        "equipment count",
        "total units",
        "boxes",
    ],
    "gross_weight_kg": [
        "gross weight",
        "gross weight (kg)",
        "gross wt (kgs)",
        "gross weight (kgs)",
        "total gross weight",
        "weight in kilograms",
        "cargo weight",
        "weight of cargo in kg",
    ],
}

# ── Math Utilities (Pure Python, Zero Dependency) ─────────────────────────

def dot_product(v1: list[float], v2: list[float]) -> float:
    """Calculate dot product of two vectors."""
    return sum(a * b for a, b in zip(v1, v2))


def vector_norm(v: list[float]) -> float:
    """Calculate Euclidean norm of a vector."""
    return math.sqrt(sum(a * a for a in v))


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    n1 = vector_norm(v1)
    n2 = vector_norm(v2)
    if n1 == 0.0 or n2 == 0.0:
        return 0.0
    return dot_product(v1, v2) / (n1 * n2)


# ── Embedding Client & Cache ──────────────────────────────────────────────

_client: Optional[genai.Client] = None
_embedding_cache: dict[str, list[float]] = {}
_canonical_vectors: Optional[dict[str, list[list[float]]]] = None


def get_genai_client() -> genai.Client:
    """Lazily initialize Vertex AI genai client."""
    global _client
    if _client is None:
        _client = genai.Client(
            vertexai=True,
            project=GCP_PROJECT_ID,
            location="us-central1",
        )
    return _client


def embed_text(text: str) -> list[float]:
    """Generate embedding vector using Vertex AI text-embedding-004 with caching."""
    cleaned = text.strip().lower()
    if cleaned in _embedding_cache:
        return _embedding_cache[cleaned]

    client = get_genai_client()
    try:
        res = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=cleaned,
        )
        vec = res.embeddings[0].values
        _embedding_cache[cleaned] = vec
        return vec
    except Exception as e:
        logger.error("Failed to generate embedding for '%s': %s", text, e)
        return []


def get_canonical_vectors() -> dict[str, list[list[float]]]:
    """Compute or return cached exemplar vectors for all canonical fields."""
    global _canonical_vectors
    if _canonical_vectors is None:
        _canonical_vectors = {}
        for field, exemplars in CANONICAL_FIELD_EXEMPLARS.items():
            vecs = []
            for ex in exemplars:
                v = embed_text(ex)
                if v:
                    vecs.append(v)
            _canonical_vectors[field] = vecs
    return _canonical_vectors


def match_field_embedding(
    raw_label: str,
    threshold: float = 0.72,
) -> tuple[Optional[str], float]:
    """Match an unrecognized label to a canonical field using semantic embeddings.

    Args:
        raw_label: The unrecognized document field label.
        threshold: Minimum cosine similarity score to accept a match (default: 0.72).

    Returns:
        tuple (canonical_field_name, similarity_score).
        canonical_field_name is None if max similarity is below threshold.
    """
    if not raw_label or not raw_label.strip():
        return None, 0.0

    q_vec = embed_text(raw_label)
    if not q_vec:
        return None, 0.0

    canonical_vecs = get_canonical_vectors()
    best_field = None
    best_sim = -1.0

    for field, vecs in canonical_vecs.items():
        if not vecs:
            continue
        field_sim = max(cosine_similarity(q_vec, cv) for cv in vecs)
        if field_sim > best_sim:
            best_sim = field_sim
            best_field = field

    if best_sim >= threshold and best_field is not None:
        logger.info("Semantic match: '%s' -> %s (similarity=%.3f)", raw_label, best_field, best_sim)
        return best_field, round(best_sim, 3)

    logger.debug("Label '%s' below threshold (best: %s @ %.3f < %.2f)", raw_label, best_field, best_sim, threshold)
    return None, round(best_sim, 3)
