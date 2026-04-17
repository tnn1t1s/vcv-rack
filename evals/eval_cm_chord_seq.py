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

import pytest

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from vcvpatch.serialize import load_vcv

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
# Helpers
# ---------------------------------------------------------------------------

def _models(patch_dict: dict) -> dict[str, dict]:
    """Return {model_slug: module_dict} for every module in the patch."""
    return {m["model"]: m for m in patch_dict["modules"]}


def _cables(patch_dict: dict) -> list[dict]:
    return patch_dict.get("cables", [])


def _ports_into(patch_dict: dict, model: str) -> set[int]:
    """Return the set of inputId values for cables arriving at the named model."""
    mods = _models(patch_dict)
    if model not in mods:
        return set()
    target_id = mods[model]["id"]
    return {c["inputId"] for c in _cables(patch_dict) if c["inputModuleId"] == target_id}


def _src_models_into(patch_dict: dict, dst_model: str) -> set[str]:
    """Return the set of source model slugs for cables landing on dst_model."""
    mods = _models(patch_dict)
    if dst_model not in mods:
        return set()
    target_id = mods[dst_model]["id"]
    id_to_model = {m["id"]: m["model"] for m in patch_dict["modules"]}
    return {
        id_to_model[c["outputModuleId"]]
        for c in _cables(patch_dict)
        if c["inputModuleId"] == target_id and c["outputModuleId"] in id_to_model
    }


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
    from agent.root_agent import root_agent

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
    REQUIRED_MODELS = [
        "Clocked-Clkd",
        "SEQ3",
        "ChordCV",
        "VCO",           # at least one; there should be three
        "Bogaudio-Mix4",
        "VCA",
        "ADSR",
        "Chronoblob2",
        "AudioInterface2",
    ]

    def test_all_required_modules_present(self, patch_dict):
        present = {m["model"] for m in patch_dict["modules"]}
        for model in self.REQUIRED_MODELS:
            assert model in present, f"Missing module: {model}"

    def test_three_vcos(self, patch_dict):
        vcos = [m for m in patch_dict["modules"] if m["model"] == "VCO"]
        assert len(vcos) == 3, f"Expected 3 VCOs, got {len(vcos)}"

    def test_vcos_feed_mix4_audio_inputs(self, patch_dict):
        """VCO SAW outputs must land on Mix4 IN ports (2, 5, 8), not LEVEL/PAN CVs."""
        mix4_audio_inputs = {2, 5, 8, 11}   # IN1-IN4 per the corrected registry
        ports = _ports_into(patch_dict, "Bogaudio-Mix4")
        audio_ports_used = ports & mix4_audio_inputs
        assert len(audio_ports_used) >= 3, (
            f"Expected at least 3 VCOs on Mix4 audio IN ports {mix4_audio_inputs}, "
            f"but cables arrived at ports {ports}"
        )

    def test_seq3_clocked_by_clock(self, patch_dict):
        srcs = _src_models_into(patch_dict, "SEQ3")
        assert "Clocked-Clkd" in srcs, f"SEQ3 is not clocked by Clocked-Clkd; sources: {srcs}"

    def test_chordcv_fed_by_seq3(self, patch_dict):
        srcs = _src_models_into(patch_dict, "ChordCV")
        assert "SEQ3" in srcs, f"ChordCV root not driven by SEQ3; sources: {srcs}"

    def test_vcos_fed_by_chordcv(self, patch_dict):
        srcs = _src_models_into(patch_dict, "VCO")
        assert "ChordCV" in srcs, f"VCOs not pitched by ChordCV; sources: {srcs}"

    def test_adsr_gated_by_seq3(self, patch_dict):
        srcs = _src_models_into(patch_dict, "ADSR")
        assert "SEQ3" in srcs, f"ADSR gate not driven by SEQ3; sources: {srcs}"

    def test_vca_fed_by_mix4(self, patch_dict):
        srcs = _src_models_into(patch_dict, "VCA")
        assert "Bogaudio-Mix4" in srcs, f"VCA audio not fed by Mix4; sources: {srcs}"

    def test_vca_enveloped_by_adsr(self, patch_dict):
        srcs = _src_models_into(patch_dict, "VCA")
        assert "ADSR" in srcs, f"VCA CV not driven by ADSR; sources: {srcs}"

    def test_chronoblob_fed_by_vca(self, patch_dict):
        srcs = _src_models_into(patch_dict, "Chronoblob2")
        assert "VCA" in srcs, f"Chronoblob2 not fed by VCA; sources: {srcs}"

    def test_audio_interface_fed_by_chronoblob(self, patch_dict):
        srcs = _src_models_into(patch_dict, "AudioInterface2")
        assert "Chronoblob2" in srcs, (
            f"AudioInterface2 not fed by Chronoblob2; sources: {srcs}"
        )

    def test_patch_file_is_valid_vcv(self, patch_dict):
        assert "modules" in patch_dict
        assert "cables" in patch_dict
        assert len(patch_dict["modules"]) >= 9
        assert len(patch_dict["cables"]) >= 8
