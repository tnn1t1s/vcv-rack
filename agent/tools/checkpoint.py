"""
checkpoint.py -- lightweight stage markers for agent progress.

This tool is intentionally small. It lets an agent emit a concise progress
record at major stage boundaries without turning the whole run into narration.

Records are appended to agent/.collab/checkpoints.jsonl as JSON lines:
    {
        "timestamp": "2026-04-17T17:00:00.000000+00:00",
        "agent_name": "patch_builder",
        "stage": "inspection_complete",
        "note": "Inspected VCO, Ladder, Saphire, AudioInterface2"
    }
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


CHECKPOINT_DIR: Path = Path(__file__).parent.parent / ".collab"


def checkpoint(stage: str, note: str, agent_name: str = "patch_builder") -> dict:
    """
    Record a concise stage checkpoint for debugging expensive agent runs.

    Use this only at major boundaries such as:
    - plan complete
    - inspection complete
    - code draft complete
    - build attempt complete
    - repair decision

    Args:
        stage: Short machine-readable stage label.
        note: Concise human-readable status note.
        agent_name: Name of the reporting agent.

    Returns:
        {"status": "ok", "stage": stage, "timestamp": iso_str}
        {"status": "error", "error": message}
    """
    try:
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        path = CHECKPOINT_DIR / "checkpoints.jsonl"
        ts = datetime.now(tz=timezone.utc).isoformat()
        record = {
            "timestamp": ts,
            "agent_name": agent_name,
            "stage": stage,
            "note": note,
        }
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
        return {"status": "ok", "stage": stage, "timestamp": ts}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
