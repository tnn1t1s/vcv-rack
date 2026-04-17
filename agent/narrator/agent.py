"""
narrator/agent.py -- ADK agent that converts narration scripts to WAV audio.

The narrator:
  1. Reads the latest message from the 'vcv-script' collab channel
  2. Extracts the patch_id and script text
  3. Calls generate_speech to produce a WAV file via Google Gemini TTS
  4. Reports the output path and duration

Environment:
  Loads .env from agent/.env
  Requires GOOGLE_API_KEY for Gemini TTS
  TTS_VOICE and TTS_MODEL are optional (see agent/tools/tts.py)

Usage:
  uv run adk run agent/narrator
"""

from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from persona import build_persona_prompt
from telemetry import setup_telemetry
from experiment import wrap
from tools.collab import collab_read
from tools.tts import generate_speech

setup_telemetry("narrator")

_config = Path(__file__).parent / "config.yaml"
_tools  = [Path(__file__).parent.parent / "tools" / f for f in ["collab.py", "tts.py"]]

prompt = build_persona_prompt(config_path=_config)

root_agent = Agent(
    name="narrator",
    model=LiteLlm(model="openrouter/anthropic/claude-haiku-4-5"),
    instruction=prompt,
    tools=[wrap(collab_read, _config, _tools), wrap(generate_speech, _config, _tools)],
)
