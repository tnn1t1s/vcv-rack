"""
Eval: Cm chord sequencer patch

Sends a natural-language prompt to the live agent and validates the resulting
.vcv file against a set of structural assertions -- no hardcoded param values,
just the routing that must be correct for the patch to produce sound.

Run:
    OPENROUTER_API_KEY=... .venv/bin/pytest evals/eval_cm_chord_seq.py -v -s

The -s flag lets you see the agent's final response in real time.

Marked `eval` so normal pytest runs skip it unless you pass -m eval:
    .venv/bin/pytest -m eval
"""

import asyncio
import os
import tempfile
from pathlib import Path

import pytest
from dotenv import load_dotenv

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from evals.patch_checks import assert_cm_chord_seq_patch
from vcvpatch.serialize import load_vcv

load_dotenv(Path(__file__).resolve().parent.parent / "agent" / ".env")

# ---------------------------------------------------------------------------
# The prompt under test -- this is the artifact being stored
# ---------------------------------------------------------------------------

PROMPT = (
    "Build the Cm chord sequencer patch: "
    "Clocked-Clkd clock into SEQ3, "
    "SEQ3.CV1 into ChordCV (minor), "
    "ChordCV NOTE1/2/3 into three VCOs, "
    "VCOs SAW outputs into Bogaudio-Mix4 IN1/IN2/IN3, "
    "Mix4 into VCA shaped by ADSR (gate from SEQ3.TRIG), "
    "VCA into Chronoblob2 tape delay, "
    "delay into AudioInterface2. "
    "Save to {output_path}"
)

# ---------------------------------------------------------------------------
# Eval fixture: run agent, return patch dict
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def patch_dict(tmp_path_factory):
    """Run the agent once per module; return the loaded patch dict."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        pytest.skip("OPENROUTER_API_KEY not set")

    output_path = str(tmp_path_factory.mktemp("eval") / "cm_chord_seq_eval.vcv")
    prompt = PROMPT.format(output_path=output_path)

    # Import here so missing google-adk doesn't break collection
    from agent.patch_builder.agent import root_agent

    async def _run():
        session_service = InMemorySessionService()
        session = await session_service.create_session(
            state={}, app_name="vcv_eval", user_id="eval"
        )
        runner = Runner(
            app_name="vcv_eval",
            agent=root_agent,
            session_service=session_service,
        )
        content = types.Content(parts=[types.Part.from_text(text=prompt)])
        final = ""
        async for event in runner.run_async(
            session_id=session.id, user_id="eval", new_message=content
        ):
            if event.is_final_response() and event.content:
                final = event.content.parts[0].text
        return final

    response = asyncio.run(_run())
    print(f"\n--- Agent response ---\n{response}\n---")

    assert os.path.exists(output_path), (
        f"Agent did not save a .vcv file to {output_path}.\nResponse:\n{response}"
    )
    return load_vcv(output_path)


# ---------------------------------------------------------------------------
# Assertions
# ---------------------------------------------------------------------------

class TestCmChordSeqEval:
    def test_all_required_modules_present(self, patch_dict):
        assert_cm_chord_seq_patch(patch_dict)

    def test_patch_file_is_valid_vcv(self, patch_dict):
        assert "modules" in patch_dict
        assert "cables" in patch_dict
        assert len(patch_dict["modules"]) >= 9
        assert len(patch_dict["cables"]) >= 8
