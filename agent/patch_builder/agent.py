"""
patch_builder/agent.py -- ADK agent that writes and proves VCV Rack patches.

The agent writes PatchBuilder Python code as a string, calls build_patch() to
exec() it in-process (no subprocess), reads proven=True/False from the result,
and iterates until the patch is proven. Then posts the path to collab.

Tools:
  file_read    -- read existing patch.py files or discovered JSON for reference
  describe_module_surface -- inspect exact params, ports, and graph semantics
  build_patch  -- exec() patch code in-process, save patch.py + .vcv, return status
  collab_post  -- announce the saved patch path for downstream agents

Usage:
  uv run adk run agent/patch_builder
"""

from pathlib import Path
import os

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from persona import build_persona_prompt
from telemetry import setup_telemetry
from experiment import wrap
from tools.build_patch import build_patch
from tools.collab import collab_post
from tools.file_read import file_read
from tools.module_surface import inspect_module_surface

setup_telemetry("patch_builder")

_config = Path(__file__).parent / "config.yaml"
_tools  = [Path(__file__).parent.parent / "tools" / f for f in ["build_patch.py", "collab.py", "file_read.py", "module_surface.py"]]

prompt = build_persona_prompt(config_path=_config)
_model_name = os.environ.get("PATCH_BUILDER_MODEL", "openrouter/anthropic/claude-sonnet-4-5")

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

root_agent = Agent(
    name="patch_builder",
    model=LiteLlm(model=_model_name),
    instruction=prompt,
    tools=[
        wrap(file_read, _config, _tools),
        wrap(inspect_module_surface, _config, _tools),
        wrap(build_patch, _config, _tools),
        wrap(collab_post, _config, _tools),
    ],
)
