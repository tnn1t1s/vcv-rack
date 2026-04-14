"""
Tests for agent/tools/collab.py -- file-based JSONL collaboration platform.

Tests:
  - collab_post writes a message to a JSONL file
  - collab_read returns messages in chronological order
  - messages have required fields: timestamp, agent_name, channel, message
  - collab_read respects the limit parameter
  - multiple channels are stored separately
  - collab_read returns empty list if no messages exist
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ---------------------------------------------------------------------------
# We patch the collab module's COLLAB_DIR before importing
# ---------------------------------------------------------------------------

@pytest.fixture()
def collab_dir(tmp_path, monkeypatch):
    """Redirect collab storage to a temp directory for test isolation."""
    import agent.tools.collab as collab_mod
    monkeypatch.setattr(collab_mod, "COLLAB_DIR", tmp_path)
    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_post_creates_file(collab_dir):
    """collab_post creates a JSONL file in the collab directory."""
    from agent.tools.collab import collab_post
    result = collab_post("test-channel", "agent1", "hello world")
    assert result["status"] == "ok"

    channel_file = collab_dir / "test-channel.jsonl"
    assert channel_file.exists()


def test_post_writes_valid_json(collab_dir):
    """Each posted message is a valid JSON line."""
    from agent.tools.collab import collab_post
    collab_post("ch1", "agentA", "message text")

    lines = (collab_dir / "ch1.jsonl").read_text().strip().splitlines()
    assert len(lines) == 1
    msg = json.loads(lines[0])
    assert msg["channel"] == "ch1"
    assert msg["agent_name"] == "agentA"
    assert msg["message"] == "message text"
    assert "timestamp" in msg


def test_post_appends(collab_dir):
    """Subsequent posts are appended, not overwritten."""
    from agent.tools.collab import collab_post
    collab_post("ch", "a", "first")
    collab_post("ch", "b", "second")

    lines = (collab_dir / "ch.jsonl").read_text().strip().splitlines()
    assert len(lines) == 2


def test_read_returns_messages(collab_dir):
    """collab_read returns posted messages."""
    from agent.tools.collab import collab_post, collab_read
    collab_post("ch", "agent1", "alpha")
    collab_post("ch", "agent2", "beta")

    result = collab_read("ch")
    assert result["status"] == "ok"
    messages = result["messages"]
    assert len(messages) == 2
    assert messages[0]["message"] == "alpha"
    assert messages[1]["message"] == "beta"


def test_read_limit(collab_dir):
    """collab_read respects the limit parameter (returns last N messages)."""
    from agent.tools.collab import collab_post, collab_read
    for i in range(10):
        collab_post("ch", "a", f"msg{i}")

    result = collab_read("ch", limit=3)
    assert result["status"] == "ok"
    msgs = result["messages"]
    assert len(msgs) == 3
    # Should be the last 3
    assert msgs[-1]["message"] == "msg9"
    assert msgs[0]["message"] == "msg7"


def test_read_empty_channel(collab_dir):
    """collab_read returns an empty list if no messages exist."""
    from agent.tools.collab import collab_read
    result = collab_read("nonexistent-channel")
    assert result["status"] == "ok"
    assert result["messages"] == []


def test_separate_channels(collab_dir):
    """Messages are stored per-channel without cross-contamination."""
    from agent.tools.collab import collab_post, collab_read
    collab_post("ch-a", "x", "channel A message")
    collab_post("ch-b", "x", "channel B message")

    result_a = collab_read("ch-a")
    result_b = collab_read("ch-b")

    assert len(result_a["messages"]) == 1
    assert result_a["messages"][0]["message"] == "channel A message"
    assert len(result_b["messages"]) == 1
    assert result_b["messages"][0]["message"] == "channel B message"


def test_message_has_all_fields(collab_dir):
    """Every message has timestamp, agent_name, channel, and message fields."""
    from agent.tools.collab import collab_post, collab_read
    collab_post("ch", "myagent", "test")

    result = collab_read("ch")
    msg = result["messages"][0]
    assert "timestamp" in msg
    assert "agent_name" in msg
    assert "channel" in msg
    assert "message" in msg
