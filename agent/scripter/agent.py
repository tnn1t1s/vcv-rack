"""
scripter/agent.py -- ADK agent that reads a patch.py and writes a narration script.

The scripter:
  1. Receives a patch_id (e.g. "01") from the user or orchestrator
  2. Calls read_patch to get the Python source with slug substitution applied
  3. Traces the signal flow left-to-right and writes a 60-second ASMR tutorial
  4. Posts the script + patch_id to the 'vcv-script' collab channel

Environment:
  Loads .env from agent/.env
  Uses OPENROUTER_API_KEY via LiteLlm

Usage:
  uv run adk run agent/scripter
"""

from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from persona import build_persona_prompt
from telemetry import setup_telemetry
from experiment import wrap
from tools.patch_reader import read_patch
from tools.collab import collab_post

setup_telemetry("scripter")

_config = Path(__file__).parent / "config.yaml"
_tools  = [Path(__file__).parent.parent / "tools" / f for f in ["patch_reader.py", "collab.py"]]

prompt = build_persona_prompt(config_path=_config)

root_agent = Agent(
    name="scripter",
    model=LiteLlm(model="openrouter/anthropic/claude-sonnet-4-5"),
    instruction=prompt,
    tools=[wrap(read_patch, _config, _tools), wrap(collab_post, _config, _tools)],
)
