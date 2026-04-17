"""
patch_builder/agent.py -- ADK agent that writes and proves VCV Rack patches.

The agent writes PatchBuilder Python code as a string, calls build_patch() to
exec() it in-process (no subprocess), reads proven=True/False from the result,
and iterates until the patch is proven. Then posts the path to collab.

Tools:
  file_read    -- read existing patch.py files or discovered JSON for reference
  inspect_module_surface -- inspect exact params, ports, and graph semantics
  checkpoint   -- record concise stage markers at major boundaries
  build_patch  -- exec() patch code in-process, save patch.py + .vcv, return status
  collab_post  -- announce the saved patch path for downstream agents

Usage:
  uv run adk run agent/patch_builder
"""

from pathlib import Path
import os
import json
import time
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from agent.experiment import wrap
from agent.persona import build_persona_prompt
from agent.telemetry import setup_telemetry
from agent.tools.build_patch import build_patch
from agent.tools.checkpoint import checkpoint
from agent.tools.collab import collab_post
from agent.tools.file_read import file_read
from agent.tools.module_surface import inspect_module_surface

setup_telemetry("patch_builder")

_config = Path(__file__).parent / "config.yaml"
_tools  = [Path(__file__).parent.parent / "tools" / f for f in ["build_patch.py", "checkpoint.py", "collab.py", "file_read.py", "module_surface.py"]]
_trace_path = Path(__file__).parent.parent / ".collab" / "patch_builder_trace.jsonl"
_model_name = os.environ.get("PATCH_BUILDER_MODEL", "openrouter/anthropic/claude-sonnet-4-5")


def _env_enabled(name: str, default: bool = True) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off", ""}


_trace_enabled = _env_enabled("PATCH_BUILDER_TRACE", default=True)
_checkpoint_enabled = _env_enabled("PATCH_BUILDER_CHECKPOINTS", default=True)
_trace_mode = os.environ.get("PATCH_BUILDER_TRACE_MODE", "write").strip().lower()

prompt = build_persona_prompt(config_path=_config)
if not _checkpoint_enabled:
    prompt += (
        "\n\nCheckpoint tool is disabled for this run. "
        "Do not plan to call checkpoint; continue directly between stages."
    )

# Tooling philosophy for future agents:
# - Prefer as few tools as possible.
# - Keep prompts short; do not compensate for weak tool design with more prompt text.
# - The primary affordance surface is the registered tool itself:
#     * function name
#     * docstring
#     * argument names and types
#     * return shape
# - If the model keeps missing a capability, first improve the tool name/docstring
#   before adding prompt prose or additional tools.
# - The prompt should mainly express policy and taste ("prefer X for Y"), while
#   the tools should make valid actions obvious.


def _trace(event: str, **payload) -> None:
    """Append a lightweight JSONL trace record for harness debugging."""
    if not _trace_enabled:
        return
    if _trace_mode == "noop":
        return
    if _trace_mode == "sleep":
        time.sleep(float(os.environ.get("PATCH_BUILDER_TRACE_SLEEP_SECS", "0.005")))
        return
    try:
        _trace_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "event": event,
            **payload,
        }
        with _trace_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, default=str) + "\n")
    except Exception:
        pass


def _session_id(callback_context) -> str | None:
    try:
        invocation_context = getattr(callback_context, "_invocation_context", None)
        return getattr(getattr(invocation_context, "session", None), "id", None)
    except Exception:
        return None


def _usage_summary(llm_response) -> dict | None:
    usage = getattr(llm_response, "usage_metadata", None)
    if not usage:
        return None
    fields = {
        "prompt_tokens": getattr(usage, "prompt_token_count", None),
        "candidate_tokens": getattr(usage, "candidates_token_count", None),
        "tool_use_prompt_tokens": getattr(usage, "tool_use_prompt_token_count", None),
        "thought_tokens": getattr(usage, "thoughts_token_count", None),
        "total_tokens": getattr(usage, "total_token_count", None),
        "cached_content_tokens": getattr(usage, "cached_content_token_count", None),
    }
    return {k: v for k, v in fields.items() if v is not None}


def _request_summary(llm_request) -> dict:
    try:
        contents = getattr(llm_request, "contents", []) or []
        content_count = len(contents)
        part_count = 0
        for content in contents:
            part_count += len(getattr(content, "parts", []) or [])
        config = getattr(llm_request, "config", None)
        tools = getattr(config, "tools", None) if config else None
        tool_count = len(tools or [])
        return {
            "content_count": content_count,
            "part_count": part_count,
            "tool_count": tool_count,
        }
    except Exception:
        return {}


def _before_model(*, callback_context, llm_request):
    _trace(
        "before_model",
        session_id=_session_id(callback_context),
        model=_model_name,
        request_type=type(llm_request).__name__,
        request_summary=_request_summary(llm_request),
    )
    return None


def _after_model(*, callback_context, llm_response):
    parts = []
    try:
        content = getattr(llm_response, "content", None)
        for part in getattr(content, "parts", []) or []:
            if getattr(part, "function_call", None):
                fc = part.function_call
                parts.append({"type": "function_call", "name": getattr(fc, "name", None)})
            elif getattr(part, "function_response", None):
                fr = part.function_response
                parts.append({"type": "function_response", "name": getattr(fr, "name", None)})
            elif getattr(part, "text", None):
                parts.append({"type": "text", "preview": str(part.text)[:160]})
    except Exception:
        parts.append({"type": "unparsed"})

    _trace(
        "after_model",
        session_id=_session_id(callback_context),
        response_type=type(llm_response).__name__,
        parts=parts,
        finish_reason=str(getattr(llm_response, "finish_reason", None)),
        usage=_usage_summary(llm_response),
    )
    return None


def _before_tool(*, tool, args, tool_context):
    _trace(
        "before_tool",
        session_id=_session_id(tool_context),
        tool=getattr(tool, "name", repr(tool)),
        args=args,
    )
    return None


def _after_tool(*, tool, args, tool_context, tool_response):
    _trace(
        "after_tool",
        session_id=_session_id(tool_context),
        tool=getattr(tool, "name", repr(tool)),
        result_status=(tool_response or {}).get("status") if isinstance(tool_response, dict) else None,
    )
    return None


def _on_tool_error(*, tool, args, tool_context, error):
    _trace(
        "tool_error",
        session_id=_session_id(tool_context),
        tool=getattr(tool, "name", repr(tool)),
        error=str(error),
    )
    return None

root_agent = Agent(
    name="patch_builder",
    model=LiteLlm(model=_model_name),
    instruction=prompt,
    before_model_callback=_before_model if _trace_enabled else None,
    after_model_callback=_after_model if _trace_enabled else None,
    before_tool_callback=_before_tool if _trace_enabled else None,
    after_tool_callback=_after_tool if _trace_enabled else None,
    on_tool_error_callback=_on_tool_error if _trace_enabled else None,
    tools=[
        wrap(file_read, _config, _tools),
        wrap(inspect_module_surface, _config, _tools),
        *([wrap(checkpoint, _config, _tools)] if _checkpoint_enabled else []),
        wrap(build_patch, _config, _tools),
        wrap(collab_post, _config, _tools),
    ],
)
