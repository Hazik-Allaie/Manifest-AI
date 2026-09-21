"""
shared/config — Environment configuration for Manifest AI.

Loads values from .env via python-dotenv and exposes them as typed constants.
Every module should import from here rather than reading os.environ directly.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")

# ── GCP ─────────────────────────────────────────────────────────────────
GCP_PROJECT_ID: str = os.getenv("MANIFEST_GCP_PROJECT_ID", "")
GCP_REGION: str = os.getenv("MANIFEST_GCP_REGION", "asia-southeast1")
VERTEX_MODEL: str = os.getenv("MANIFEST_VERTEX_MODEL", "gemini-2.0-flash")

# ── Firestore / Pub/Sub ─────────────────────────────────────────────────
FIRESTORE_DB: str = os.getenv("MANIFEST_FIRESTORE_DB", "manifest-db")
PUBSUB_TOPIC: str = os.getenv("MANIFEST_PUBSUB_TOPIC", "new-email-events")

# ── Notifications ────────────────────────────────────────────────────────
DISCORD_WEBHOOK: str = os.getenv("MANIFEST_DISCORD_WEBHOOK", "")

# ── Dataset paths ────────────────────────────────────────────────────────
DATASET_PATH: Path = _PROJECT_ROOT / os.getenv("MANIFEST_DATASET_PATH", "./data-basic")
ADVANCED_DATASET_PATH: Path = _PROJECT_ROOT / os.getenv(
    "MANIFEST_ADVANCED_DATASET_PATH", "./local-server/data-advanced"
)
SELF_EVAL_SCRIPT: Path = _PROJECT_ROOT / os.getenv(
    "MANIFEST_SELF_EVAL_SCRIPT", "./local-server/server/score_cli.py"
)
