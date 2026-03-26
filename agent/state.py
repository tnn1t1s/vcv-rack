"""
Per-session state for the VCV Rack patch agent.

Stores PatchBuilder instances keyed by session_id so they survive across
multiple tool calls within one session without JSON serialization.
"""

from __future__ import annotations
from vcvpatch.builder import PatchBuilder

_sessions: dict[str, dict] = {}


def get(session_id: str) -> dict:
    """Return (creating if needed) the session state dict for session_id.

    State dict keys:
      "pb"              -- PatchBuilder instance
      "modules"         -- dict[str, ModuleHandle], friendly names assigned by the agent
      "rack_connection" -- RackConnection | None, active connection to running Rack
    """
    if session_id not in _sessions:
        _sessions[session_id] = {"pb": PatchBuilder(), "modules": {}, "rack_connection": None}
    return _sessions[session_id]


def reset(session_id: str) -> None:
    """Discard and recreate session state (fresh PatchBuilder, empty module map).

    Disconnects any active Rack connection before clearing.
    """
    old = _sessions.get(session_id, {})
    conn = old.get("rack_connection")
    if conn is not None:
        try:
            conn.disconnect()
        except Exception:
            pass
    _sessions[session_id] = {"pb": PatchBuilder(), "modules": {}, "rack_connection": None}
