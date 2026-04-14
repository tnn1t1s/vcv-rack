"""
Pytest suite for agent/patch_tools.py.

Tests run without Google ADK or a live Gemini session -- all tool_context
arguments are replaced with a lightweight FakeContext that carries a
unique session_id per test (via pytest fixtures).
"""

import json
import os
import tempfile
import uuid

import pytest

from agent.state import get as state_get, reset as state_reset
from agent.patch_tools import (
    add_module,
    compile_and_save,
    connect_audio,
    connect_cv,
    describe_module,
    fan_out_audio,
    get_status,
    list_modules,
    modulate,
    new_patch,
    reset_patch,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeContext:
    """Minimal stand-in for google.adk.tools.ToolContext."""
    def __init__(self, session_id: str):
        self.session_id = session_id


@pytest.fixture()
def ctx():
    """Fresh session context for each test."""
    sid = str(uuid.uuid4())
    yield FakeContext(sid)
    # Clean up session state after the test.
    state_reset(sid)


def _ok(result: dict):
    """Assert result is ok and return it."""
    assert result["status"] == "ok", f"Expected ok, got: {result}"
    return result


def _err(result: dict):
    """Assert result is an error and return it."""
    assert result["status"] == "error", f"Expected error, got: {result}"
    return result


# ---------------------------------------------------------------------------
# new_patch / reset_patch
# ---------------------------------------------------------------------------

class TestNewPatch:
    def test_new_patch_returns_ok(self, ctx):
        r = _ok(new_patch(ctx))
        assert "message" in r

    def test_new_patch_clears_state(self, ctx):
        add_module("vco1", "Fundamental", "VCO", tool_context=ctx)
        new_patch(ctx)
        s = state_get(ctx.session_id)
        assert s["modules"] == {}

    def test_reset_patch_is_alias(self, ctx):
        r = _ok(reset_patch(ctx))
        assert "message" in r


# ---------------------------------------------------------------------------
# list_modules
# ---------------------------------------------------------------------------

class TestListModules:
    def test_returns_ok(self, ctx):
        r = _ok(list_modules(ctx))
        assert "by_plugin" in r
        assert "introspectable" in r

    def test_includes_fundamental(self, ctx):
        r = list_modules(ctx)
        assert "Fundamental" in r["by_plugin"]

    def test_includes_core(self, ctx):
        r = list_modules(ctx)
        assert "Core" in r["by_plugin"]

    def test_vco_is_introspectable(self, ctx):
        r = list_modules(ctx)
        assert "Fundamental/VCO" in r["introspectable"]


# ---------------------------------------------------------------------------
# describe_module
# ---------------------------------------------------------------------------

class TestDescribeModule:
    def test_vco_outputs(self, ctx):
        r = _ok(describe_module("Fundamental", "VCO", tool_context=ctx))
        # outputs is now a list of {id, name} dicts (from discovered/)
        output_names = [o["name"] for o in r["outputs"]]
        assert "Sawtooth" in output_names
        assert "Square" in output_names

    def test_vco_inputs(self, ctx):
        r = describe_module("Fundamental", "VCO", tool_context=ctx)
        # '1V/octave pitch' is the canonical name for VOCT
        input_names = [i["name"] for i in r["inputs"]]
        assert any("octave" in n.lower() for n in input_names), \
            f"No V/oct input found; inputs={input_names}"

    def test_vcf_has_attenuator_note(self, ctx):
        r = describe_module("Fundamental", "VCF", tool_context=ctx)
        notes_text = " ".join(r["notes"])
        assert "attenuator" in notes_text.lower()

    def test_unknown_module_returns_error(self, ctx):
        _err(describe_module("NoPlugin", "NoModel", tool_context=ctx))

    def test_vca_required_cv_noted(self, ctx):
        r = describe_module("Fundamental", "VCA", tool_context=ctx)
        notes_text = " ".join(r["notes"])
        assert "required" in notes_text.lower()


# ---------------------------------------------------------------------------
# add_module
# ---------------------------------------------------------------------------

class TestAddModule:
    def test_add_vco(self, ctx):
        r = _ok(add_module("vco1", "Fundamental", "VCO", tool_context=ctx))
        assert r["name"] == "vco1"
        assert r["introspectable"] is True

    def test_params_applied(self, ctx):
        # Use canonical param name "Frequency" (id=2) for Fundamental/LFO
        _ok(add_module("lfo1", "Fundamental", "LFO",
                        params_json='{"Frequency": 0.3}', tool_context=ctx))
        s = state_get(ctx.session_id)
        handle = s["modules"]["lfo1"]
        # Frequency is param id 2 in Fundamental/LFO (from discovered/)
        assert handle._module._param_values.get(2) == pytest.approx(0.3)

    def test_invalid_params_json(self, ctx):
        _err(add_module("x", "Fundamental", "VCO", params_json="not json",
                         tool_context=ctx))

    def test_duplicate_name_overwrites(self, ctx):
        add_module("vco1", "Fundamental", "VCO", tool_context=ctx)
        add_module("vco1", "Fundamental", "LFO", tool_context=ctx)
        s = state_get(ctx.session_id)
        handle = s["modules"]["vco1"]
        assert handle._module.model == "LFO"

    def test_unknown_module_still_adds(self, ctx):
        # UnknownNode path -- should succeed but introspectable=False
        r = _ok(add_module("mystery", "FakePlugin", "FakeModel", tool_context=ctx))
        assert r["introspectable"] is False


# ---------------------------------------------------------------------------
# connect_audio
# ---------------------------------------------------------------------------

class TestConnectAudio:
    @pytest.fixture(autouse=True)
    def setup(self, ctx):
        self.ctx = ctx
        add_module("vco1", "Fundamental", "VCO", tool_context=ctx)
        add_module("vcf1", "Fundamental", "VCF", tool_context=ctx)
        add_module("audio", "Core", "AudioInterface2", tool_context=ctx)

    def test_basic_connect(self):
        # VCO 'Sawtooth' output (id=2) -> VCF 'Audio' input (id=3)
        r = _ok(connect_audio("vco1.Sawtooth", "vcf1.i.Audio", tool_context=self.ctx))
        assert r["from"] == "vco1.Sawtooth"
        assert r["to"] == "vcf1.i.Audio"

    def test_unknown_module_errors(self):
        _err(connect_audio("ghost.Sawtooth", "vcf1.i.Audio", tool_context=self.ctx))

    def test_unknown_port_errors(self):
        _err(connect_audio("vco1.NOSUCHPORT", "vcf1.i.Audio", tool_context=self.ctx))

    def test_color_stored(self):
        # AudioInterface2 input canonical name: 'Left input' -> normalizes to 'left input'
        # Use 'Left_input' (underscore -> space in normalization)
        r = _ok(connect_audio("vco1.Sawtooth", "audio.i.Left_input",
                               color="red", tool_context=self.ctx))
        assert r["color"] == "red"


# ---------------------------------------------------------------------------
# fan_out_audio
# ---------------------------------------------------------------------------

class TestFanOutAudio:
    @pytest.fixture(autouse=True)
    def setup(self, ctx):
        self.ctx = ctx
        add_module("vco1", "Fundamental", "VCO", tool_context=ctx)
        add_module("audio", "Core", "AudioInterface2", tool_context=ctx)

    def test_fan_out_both_channels(self):
        r = _ok(fan_out_audio(
            "vco1.Sawtooth",
            ["audio.i.Left_input", "audio.i.Right_input"],
            tool_context=self.ctx,
        ))
        assert len(r["to"]) == 2

    def test_bad_src_errors(self):
        _err(fan_out_audio("ghost.Sawtooth", ["audio.i.Left_input"], tool_context=self.ctx))

    def test_bad_dst_errors(self):
        _err(fan_out_audio("vco1.Sawtooth", ["audio.i.NOPE"], tool_context=self.ctx))


# ---------------------------------------------------------------------------
# modulate
# ---------------------------------------------------------------------------

class TestModulate:
    @pytest.fixture(autouse=True)
    def setup(self, ctx):
        self.ctx = ctx
        add_module("lfo1", "Fundamental", "LFO", tool_context=ctx)
        add_module("vcf1", "Fundamental", "VCF", tool_context=ctx)

    def test_modulate_creates_cable(self):
        # LFO 'Sine' output (id=0) -> VCF 'Frequency' input (id=0)
        r = _ok(modulate("lfo1.Sine", "vcf1.i.Frequency", tool_context=self.ctx))
        assert r["from"] == "lfo1.Sine"
        assert r["to"] == "vcf1.i.Frequency"

    def test_attenuation_set(self):
        modulate("lfo1.Sine", "vcf1.i.Frequency", attenuation=0.7, tool_context=self.ctx)
        s = state_get(self.ctx.session_id)
        vcf_handle = s["modules"]["vcf1"]
        # VCF 'Cutoff frequency CV' attenuator is param id 3
        assert vcf_handle._module._param_values.get(3) == pytest.approx(0.7)

    def test_bad_src_module_errors(self):
        _err(modulate("ghost.Sine", "vcf1.i.Frequency", tool_context=self.ctx))

    def test_bad_dst_port_errors(self):
        _err(modulate("lfo1.Sine", "vcf1.i.NOSUCH", tool_context=self.ctx))


# ---------------------------------------------------------------------------
# connect_cv
# ---------------------------------------------------------------------------

class TestConnectCV:
    @pytest.fixture(autouse=True)
    def setup(self, ctx):
        self.ctx = ctx
        add_module("clock1", "ImpromptuModular", "Clocked-Clkd", tool_context=ctx)
        add_module("seq1",   "Fundamental",      "SEQ3",          tool_context=ctx)

    def test_clock_cable(self):
        # Clocked-Clkd 'Clock 1' output (id=1) -> SEQ3 'Clock' input (id=1)
        r = _ok(connect_cv(
            "clock1.o.Clock_1", "seq1.i.Clock",
            color="white", role="clock",
            tool_context=self.ctx,
        ))
        assert r["role"] == "clock"

    def test_bad_port_errors(self):
        _err(connect_cv("clock1.o.NOPE", "seq1.i.Clock", tool_context=self.ctx))


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------

class TestGetStatus:
    def test_empty_patch(self, ctx):
        r = _ok(get_status(ctx))
        assert r["proven"] is False   # no audio sink connected
        assert r["named_modules"] == []

    def test_proven_simple_patch(self, ctx):
        add_module("vco1",  "Fundamental",     "VCO",            tool_context=ctx)
        add_module("audio", "Core",            "AudioInterface2", tool_context=ctx)
        connect_audio("vco1.Sawtooth", "audio.i.Left_input",  tool_context=ctx)
        connect_audio("vco1.Sawtooth", "audio.i.Right_input", tool_context=ctx)
        r = _ok(get_status(ctx))
        assert r["proven"] is True
        assert "vco1" in r["named_modules"]

    def test_status_contains_routing(self, ctx):
        add_module("vco1",  "Fundamental", "VCO",             tool_context=ctx)
        add_module("audio", "Core",        "AudioInterface2", tool_context=ctx)
        connect_audio("vco1.Sawtooth", "audio.i.Left_input", tool_context=ctx)
        r = get_status(ctx)
        assert "VCO" in r["routing"]


# ---------------------------------------------------------------------------
# compile_and_save
# ---------------------------------------------------------------------------

class TestCompileAndSave:
    def test_save_proven_patch(self, ctx):
        add_module("vco1",  "Fundamental", "VCO",             tool_context=ctx)
        add_module("audio", "Core",        "AudioInterface2", tool_context=ctx)
        connect_audio("vco1.Sawtooth", "audio.i.Left_input",  tool_context=ctx)
        connect_audio("vco1.Sawtooth", "audio.i.Right_input", tool_context=ctx)

        with tempfile.NamedTemporaryFile(suffix=".vcv", delete=False) as f:
            path = f.name
        try:
            r = _ok(compile_and_save(path, tool_context=ctx))
            assert r["proven"] is True
            assert os.path.exists(path)
            assert os.path.getsize(path) > 0
        finally:
            os.unlink(path)

    def test_save_unproven_patch_errors(self, ctx):
        add_module("vco1", "Fundamental", "VCO", tool_context=ctx)
        # No audio output connected -- not proven
        with tempfile.NamedTemporaryFile(suffix=".vcv", delete=False) as f:
            path = f.name
        try:
            r = _err(compile_and_save(path, tool_context=ctx))
            assert "proven" in r["message"].lower() or "compile" in r["message"].lower()
        finally:
            if os.path.exists(path):
                os.unlink(path)


# ---------------------------------------------------------------------------
# Full end-to-end: simple drone patch
# ---------------------------------------------------------------------------

class TestDronePatch:
    """VCO -> Plateau reverb -> AudioInterface2, proven on first attempt."""

    def test_drone_patch_proven_and_saves(self, ctx):
        _ok(new_patch(ctx))

        _ok(add_module("vco1",   "Fundamental", "VCO",             tool_context=ctx))
        _ok(add_module("reverb", "Valley",      "Plateau",         tool_context=ctx))
        _ok(add_module("audio",  "Core",        "AudioInterface2", tool_context=ctx))

        # Plateau inputs are 'Left' (id=0) and 'Right' (id=1)
        # Plateau outputs are 'Left' (id=0) and 'Right' (id=1)
        _ok(connect_audio("vco1.Sawtooth", "reverb.i.Left", tool_context=ctx))
        _ok(fan_out_audio("reverb.o.Left",
                          ["audio.i.Left_input", "audio.i.Right_input"],
                          color="green", tool_context=ctx))

        status = _ok(get_status(ctx))
        assert status["proven"] is True, status["report"]

        with tempfile.NamedTemporaryFile(suffix=".vcv", delete=False) as f:
            path = f.name
        try:
            _ok(compile_and_save(path, tool_context=ctx))
            assert os.path.getsize(path) > 0
        finally:
            os.unlink(path)

    def test_drone_with_lfo_modulation(self, ctx):
        _ok(new_patch(ctx))

        _ok(add_module("vco1",   "Fundamental", "VCO",             tool_context=ctx))
        _ok(add_module("lfo1",   "Fundamental", "LFO",
                        params_json='{"Frequency": 0.5}', tool_context=ctx))
        _ok(add_module("audio",  "Core",        "AudioInterface2", tool_context=ctx))

        _ok(connect_audio("vco1.Sawtooth", "audio.i.Left_input",  tool_context=ctx))
        _ok(connect_audio("vco1.Sawtooth", "audio.i.Right_input", tool_context=ctx))
        # VCO 'Pulse width modulation' input (id=3)
        _ok(modulate("lfo1.Sine", "vco1.i.Pulse_width_modulation",
                     attenuation=0.4, tool_context=ctx))

        status = _ok(get_status(ctx))
        assert status["proven"] is True, status["report"]
