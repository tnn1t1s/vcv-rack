"""Repo-local agent environment summary for fresh sessions."""

from __future__ import annotations

import os
from pathlib import Path
from textwrap import dedent

from vcvpatch import supported_modules

REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = REPO_ROOT / "agent" / ".env"
DEFAULT_MODEL = "openrouter/anthropic/claude-sonnet-4-5"


def describe_environment() -> dict:
    modules = supported_modules()
    plugins = sorted({module.plugin for module in modules})
    return {
        "repo_root": str(REPO_ROOT),
        "env_path": str(ENV_PATH),
        "env_exists": ENV_PATH.exists(),
        "model": os.environ.get("PATCH_BUILDER_MODEL", DEFAULT_MODEL),
        "supported_module_count": len(modules),
        "supported_plugin_count": len(plugins),
        "supported_plugins": plugins,
        "commands": {
            "doctor": "uv run vcv-agent-doctor",
            "agent": 'uv run vcv-agent "Create a minimal test patch"',
            "adk": "uv run adk run agent/patch_builder",
            "evals": "uv run pytest evals/test_adk_patch_builder.py -q -s",
        },
    }


def render_environment(info: dict) -> str:
    plugins_preview = ", ".join(info["supported_plugins"][:8])
    if len(info["supported_plugins"]) > 8:
        plugins_preview += ", ..."
    env_state = "present" if info["env_exists"] else "missing"
    return dedent(
        f"""\
        VCV Rack agent environment
        ==========================
        Repo root: {info['repo_root']}
        Env file: {info['env_path']} ({env_state})
        Default patch-builder model: {info['model']}
        Supported palette: {info['supported_module_count']} modules across {info['supported_plugin_count']} plugins
        Supported plugins (sample): {plugins_preview}

        Canonical commands
        ------------------
        Doctor: {info['commands']['doctor']}
        Run patch-builder once: {info['commands']['agent']}
        ADK patch-builder loop: {info['commands']['adk']}
        ADK evals: {info['commands']['evals']}

        Fresh-session rule
        ------------------
        Start from the repo root and run the doctor first. Do not guess Python
        invocation paths or env file locations when the runtime can tell you.
        """
    )


def main() -> None:
    print(render_environment(describe_environment()))


if __name__ == "__main__":
    main()
