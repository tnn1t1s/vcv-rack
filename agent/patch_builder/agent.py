"""
patch_builder/agent.py -- ADK agent that writes and proves VCV Rack patches.

The agent writes PatchBuilder Python code as a string, calls build_patch() to
exec() it in-process (no subprocess), reads proven=True/False from the result,
and iterates until the patch is proven. Then posts the path to collab.

Tools:
  file_read    -- read existing patch.py files or discovered JSON for reference
  build_patch  -- exec() patch code in-process, save patch.py + .vcv, return status
  collab_post  -- announce the saved patch path for downstream agents

Usage:
  uv run adk run agent/patch_builder
"""

from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from agent.persona import build_persona_prompt
from agent.telemetry import setup_telemetry
from agent.experiment import wrap
from agent.tools.build_patch import build_patch
from agent.tools.collab import collab_post
from agent.tools.file_read import file_read

setup_telemetry("patch_builder")

_config = Path(__file__).parent / "config.yaml"
_tools  = [Path(__file__).parent.parent / "tools" / f for f in ["build_patch.py", "collab.py", "file_read.py"]]

prompt = build_persona_prompt(config_path=_config)

root_agent = Agent(
    name="patch_builder",
    model=LiteLlm(model="openrouter/anthropic/claude-sonnet-4-5"),
    instruction=prompt,
    tools=[wrap(file_read, _config, _tools), wrap(build_patch, _config, _tools), wrap(collab_post, _config, _tools)],
)
