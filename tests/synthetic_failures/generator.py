"""
tests/synthetic_failures/generator.py — Synthetic Test Case & Fixture Generator (Unit 12).

Materializes deterministic test fixtures (inbox JSONs and attachment files)
for the 9 synthetic failure scenarios into tests/synthetic_failures/fixtures/.
"""

import json
import sys
from pathlib import Path
from typing import Optional

# Ensure workspace root is in sys.path
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from tests.synthetic_failures.scenarios import SCENARIOS, SyntheticScenario

DEFAULT_FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def ensure_fixtures(fixtures_dir: Optional[Path] = None) -> Path:
    """Generate all synthetic test fixtures on disk if not already present."""
    root = fixtures_dir or DEFAULT_FIXTURES_DIR
    inbox_dir = root / "inbox"
    attachments_dir = root / "attachments"

    inbox_dir.mkdir(parents=True, exist_ok=True)
    attachments_dir.mkdir(parents=True, exist_ok=True)

    for scenario_id, sc in SCENARIOS.items():
        email_id = f"synth_{scenario_id}"
        att_list = [sc.si_filename]
        if sc.bl_filename:
            att_list.append(sc.bl_filename)

        email_data = {
            "email_id": email_id,
            "subject": sc.email_subject,
            "sender": "operations@pacific-logistics.com",
            "body": sc.email_body,
            "attachments": att_list,
        }

        # Write inbox email JSON
        email_path = inbox_dir / f"{email_id}.json"
        email_path.write_text(json.dumps(email_data, indent=2), encoding="utf-8")

        # Write SI attachment
        si_path = root / sc.si_filename
        si_path.parent.mkdir(parents=True, exist_ok=True)
        si_path.write_text(sc.si_text, encoding="utf-8")

        # Write BL attachment if applicable
        if sc.bl_filename:
            bl_path = root / sc.bl_filename
            bl_path.parent.mkdir(parents=True, exist_ok=True)
            if sc.bl_bytes is not None:
                bl_path.write_bytes(sc.bl_bytes)
            elif sc.bl_text is not None:
                bl_path.write_text(sc.bl_text, encoding="utf-8")

    return root


def get_scenario_email(scenario_id: str, fixtures_dir: Optional[Path] = None) -> dict:
    """Retrieve the email dictionary for a scenario, ensuring fixtures exist."""
    root = ensure_fixtures(fixtures_dir)
    email_id = f"synth_{scenario_id}"
    email_path = root / "inbox" / f"{email_id}.json"
    if not email_path.exists():
        raise KeyError(f"Synthetic scenario '{scenario_id}' not found.")
    return json.loads(email_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    path = ensure_fixtures()
    print(f"Generated {len(SCENARIOS)} synthetic failure fixtures at: {path}")
