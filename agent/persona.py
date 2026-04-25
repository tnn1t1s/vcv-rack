"""
persona.py -- Build a system prompt string from a YAML persona config.

This is a self-contained replacement for adk_teams.build_persona_prompt.
It walks all values in the 'persona' section of the config, collecting
string values recursively, and assembles them into a structured system prompt.

YAML config structure (all keys optional):

    persona:
      identity:
        title:     str       -- "You are a <title>."
        seniority: str       -- "You are <seniority>"
        ...                  -- other identity fields appended verbatim
      project_context: str   -- included under ## Project Context
      work:
        description: str     -- included under ## Your Work
        daily_activities: [] -- bullet list
        typical_project: str -- included as paragraph
      module_knowledge:      -- arbitrary nested; all leaf strings included
        ModuleName: str
      values:
        optimizes_for: str   -- included under ## What You Value
        avoids: str
      frustrations: []       -- bullet list under ## What Frustrates You
      task: str              -- included under ## Your Task
      tool_usage: str        -- included under ## Tool Usage
      ...                    -- any other top-level key: leaf strings collected

    model:                   -- top-level 'model' key is IGNORED entirely

Usage:
    from agent.persona import build_persona_prompt
    from pathlib import Path

    prompt = build_persona_prompt(Path("agents/scripter/config.yaml"))
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def build_persona_prompt(config_path: Path) -> str:
    """
    Load a persona YAML config and return a system prompt string.

    Only the 'persona' top-level key is used. The 'model' key is silently
    ignored.  Within 'persona', known sections (identity, work, task, values,
    frustrations, tool_usage, project_context) are formatted with headers.
    All other sections have their leaf string values collected and included.

    Args:
        config_path: Path to a YAML file with a top-level 'persona' key.

    Returns:
        A system prompt string suitable for use as an Agent instruction.
    """
    raw = yaml.safe_load(config_path.read_text())
    persona = raw.get("persona", {})

    sections: list[str] = []

    # -- Identity header -------------------------------------------------
    identity = persona.get("identity", {})
    title = identity.get("title", "Agent")
    sections.append(f"You are a {title}.")

    seniority = identity.get("seniority")
    if seniority:
        sections.append(f"You are {_clean(seniority)}")

    # Include any other identity fields (besides title/seniority) verbatim
    for key, val in identity.items():
        if key in ("title", "seniority"):
            continue
        if isinstance(val, str) and val.strip():
            sections.append(_clean(val))

    # -- project_context -------------------------------------------------
    project_context = persona.get("project_context")
    if project_context and isinstance(project_context, str):
        sections.append(f"## Project Context\n{_clean(project_context)}")

    # -- work ------------------------------------------------------------
    work = persona.get("work")
    if work and isinstance(work, dict):
        parts: list[str] = []
        desc = work.get("description")
        if desc:
            parts.append(_clean(desc))
        daily = work.get("daily_activities")
        if daily and isinstance(daily, list):
            items = "\n".join(f"- {a}" for a in daily)
            parts.append(f"### What You Do Every Day\n{items}")
        typical = work.get("typical_project")
        if typical:
            parts.append(f"### A Typical Project\n{_clean(typical)}")
        if parts:
            sections.append("## Your Work\n" + "\n\n".join(parts))

    # -- module_knowledge and any other freeform sections ----------------
    # Known top-level keys that are handled explicitly above or below.
    _HANDLED = frozenset({
        "identity", "project_context", "work", "values",
        "frustrations", "task", "tool_usage",
    })
    for key, val in persona.items():
        if key in _HANDLED:
            continue
        leaf_strings = _collect_leaves(val)
        if leaf_strings:
            header = key.replace("_", " ").title()
            body = "\n\n".join(leaf_strings)
            sections.append(f"## {header}\n{body}")

    # -- frustrations ----------------------------------------------------
    frustrations = persona.get("frustrations")
    if frustrations and isinstance(frustrations, list):
        items = "\n".join(f"- {f}" for f in frustrations)
        sections.append(f"## What Frustrates You\n{items}")

    # -- values ----------------------------------------------------------
    values = persona.get("values")
    if values and isinstance(values, dict):
        parts = []
        opt = values.get("optimizes_for")
        if opt:
            parts.append(f"You optimize for:\n{_clean(opt)}")
        avoids = values.get("avoids")
        if avoids:
            parts.append(f"You avoid:\n{_clean(avoids)}")
        # Any other keys in values
        for k, v in values.items():
            if k in ("optimizes_for", "avoids"):
                continue
            if isinstance(v, str) and v.strip():
                label = k.replace("_", " ").title()
                parts.append(f"{label}:\n{_clean(v)}")
        if parts:
            sections.append("## What You Value\n\n" + "\n\n".join(parts))

    # -- task ------------------------------------------------------------
    task = persona.get("task")
    if task and isinstance(task, str):
        sections.append(f"## Your Task\n{_clean(task)}")

    # -- tool_usage ------------------------------------------------------
    tool_usage = persona.get("tool_usage")
    if tool_usage and isinstance(tool_usage, str):
        sections.append(f"## Tool Usage\n{_clean(tool_usage)}")

    runtime_orientation = _runtime_orientation_section()
    if runtime_orientation:
        sections.append(runtime_orientation)

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clean(s: str) -> str:
    """Strip leading/trailing whitespace from a string."""
    return s.strip()


def _collect_leaves(node: Any) -> list[str]:
    """
    Recursively collect all non-empty string leaf values from a nested
    dict/list structure.  Returns a flat list of stripped strings.
    """
    results: list[str] = []
    if isinstance(node, str):
        v = node.strip()
        if v:
            results.append(v)
    elif isinstance(node, dict):
        for v in node.values():
            results.extend(_collect_leaves(v))
    elif isinstance(node, list):
        for item in node:
            results.extend(_collect_leaves(item))
    return results


def _runtime_orientation_section() -> str | None:
    """Append runtime-derived repo orientation when available."""
    try:
        from agent.doctor import describe_environment
    except Exception:
        return None

    try:
        info = describe_environment()
    except Exception:
        return None

    commands = info.get("commands", {})
    return "\n".join(
        [
            "## Runtime Orientation",
            "Use these runtime-derived facts instead of guessing local paths or entrypoints:",
            f"- Repo root: {info.get('repo_root')}",
            f"- Agent env file: {info.get('env_path')}",
            f"- Doctor command: {commands.get('doctor')}",
            f"- One-shot agent command: {commands.get('agent')}",
            f"- ADK patch-builder command: {commands.get('adk')}",
            f"- ADK eval command: {commands.get('evals')}",
            "",
            "If asked how to re-orient in this repo, answer from these facts rather than inventing a generic Python invocation.",
        ]
    )
