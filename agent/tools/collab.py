"""
collab.py -- File-based JSONL collaboration channel for multi-agent workflows.

Each channel is a JSONL file at COLLAB_DIR/<channel>.jsonl.
Every line is a JSON object:
    {
        "timestamp": "2025-01-01T12:00:00.000000",
        "agent_name": "scripter",
        "channel":    "vcv-script",
        "message":    "Patch 01 narration: ..."
    }

This is a self-contained replacement for adk_teams.tools.collab_post /
collab_read. No external service or credentials required.

Usage:
    from agent.tools.collab import collab_post, collab_read

    collab_post("vcv-script", "scripter", "Here is the narration: ...")
    result = collab_read("vcv-script", limit=5)
    # result["messages"] is a list of dicts, oldest first, up to limit entries
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

# Default storage directory. Tests monkeypatch this to a temp directory.
COLLAB_DIR: Path = Path(__file__).parent.parent / ".collab"


def collab_post(channel: str, agent_name: str, message: str) -> dict:
    """
    Append a message to a JSONL collaboration channel.

    Creates the channel file (and parent directory) if they do not exist.
    Thread safety: each call does a single atomic append, which is safe
    for single-process use. For multi-process safety, use a lock or a
    proper message queue.

    Args:
        channel:    Channel name, e.g. "vcv-script". Maps to <channel>.jsonl.
        agent_name: Name of the posting agent, e.g. "scripter".
        message:    Message content string.

    Returns:
        {"status": "ok", "channel": channel, "timestamp": iso_str}
        {"status": "error", "error": message}
    """
    try:
        collab_dir = COLLAB_DIR
        collab_dir.mkdir(parents=True, exist_ok=True)
        channel_file = collab_dir / f"{channel}.jsonl"

        ts = datetime.now(tz=timezone.utc).isoformat()
        record = {
            "timestamp":  ts,
            "agent_name": agent_name,
            "channel":    channel,
            "message":    message,
        }
        with channel_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")

        return {"status": "ok", "channel": channel, "timestamp": ts}

    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def collab_read(channel: str, limit: int = 20) -> dict:
    """
    Read the most recent messages from a JSONL collaboration channel.

    Returns messages in chronological order (oldest first within the window).
    If the channel file does not exist, returns an empty message list rather
    than an error -- callers can treat a missing channel as no messages yet.

    Args:
        channel: Channel name, e.g. "vcv-script".
        limit:   Maximum number of recent messages to return (default 20).

    Returns:
        {"status": "ok", "channel": channel, "messages": [list of dicts]}
        {"status": "error", "error": message}
    """
    try:
        channel_file = COLLAB_DIR / f"{channel}.jsonl"

        if not channel_file.exists():
            return {"status": "ok", "channel": channel, "messages": []}

        lines = channel_file.read_text(encoding="utf-8").strip().splitlines()
        # Parse all lines, skip malformed ones gracefully
        messages = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                pass  # Skip corrupt lines rather than aborting

        # Return the last `limit` messages, oldest first
        return {
            "status":   "ok",
            "channel":  channel,
            "messages": messages[-limit:] if limit > 0 else messages,
        }

    except Exception as exc:
        return {"status": "error", "error": str(exc)}
