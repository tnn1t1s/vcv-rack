"""
agent/experiment.py -- substrait wiring for VCV Rack agent pipeline.

Reads experiment identity from environment variables, builds a FactStore
and Manifest, and exposes a wrap() function that instruments any tool.

Environment variables:
    SUBSTRAIT_EXPERIMENT_ID  -- run identifier (e.g. "run-2026-04-10-rings")
                                 defaults to a timestamp-based ID
    SUBSTRAIT_PROBLEM_ID     -- which patch is being processed (e.g. "patch-04")
                                 optional; set per-problem in the pipeline script
    SUBSTRAIT_DB             -- path to the SQLite fact store
                                 defaults to agent/runs/<experiment_id>.db

Usage (in agent.py):
    from agent.experiment import wrap
    tools = [wrap(build_patch), wrap(collab_post), wrap(file_read)]
    root_agent = Agent(..., tools=tools)
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from substrait import FactStore, Manifest, instrument

_ROOT = Path(__file__).parent.parent

# ------------------------------------------------------------------
# Experiment identity from environment
# ------------------------------------------------------------------

def _default_experiment_id() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%S")
    return f"run-{ts}"


EXPERIMENT_ID = os.environ.get("SUBSTRAIT_EXPERIMENT_ID") or _default_experiment_id()
PROBLEM_ID    = os.environ.get("SUBSTRAIT_PROBLEM_ID")    or None

_db_default = _ROOT / "agent" / "runs" / f"{EXPERIMENT_ID}.db"
DB_PATH = Path(os.environ.get("SUBSTRAIT_DB") or _db_default)

# ------------------------------------------------------------------
# Manifest: hash the tool files and agent config for this agent.
# Populated lazily so importing this module has no side effects.
# ------------------------------------------------------------------

_store: FactStore | None = None
_manifest: Manifest | None = None


def _get_store() -> FactStore:
    global _store
    if _store is None:
        _store = FactStore(DB_PATH)
    return _store


def _get_manifest(agent_config: Path, tool_files: list[Path]) -> Manifest:
    global _manifest
    if _manifest is None:
        paths = [p for p in [agent_config] + tool_files if p.exists()]
        _manifest = Manifest.from_paths(
            paths,
            extra={"experiment_id": EXPERIMENT_ID},
        )
        _manifest.save(_get_store())
    return _manifest


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def wrap(
    tool_fn: Callable,
    agent_config: Path | None = None,
    tool_files: list[Path] | None = None,
) -> Callable:
    """Instrument a tool function with substrait fact recording.

    Args:
        tool_fn:      The tool function to wrap.
        agent_config: Path to this agent's config.yaml (for manifest hashing).
        tool_files:   Additional tool source files to include in the manifest.

    Returns:
        Instrumented version of tool_fn -- transparent to ADK.
    """
    config = agent_config or Path(__file__).parent / "patch_builder" / "config.yaml"
    files  = tool_files  or []

    manifest = _get_manifest(config, files)
    store    = _get_store()

    return instrument(
        tool_fn,
        store=store,
        experiment_id=EXPERIMENT_ID,
        manifest_id=manifest.manifest_id,
        problem_id=PROBLEM_ID,
    )


def store() -> FactStore:
    """Return the shared FactStore for this experiment (e.g. for semantic facts)."""
    return _get_store()
