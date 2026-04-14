"""
Tests for Saphire module registration in the vcvpatch layer.

Verifies:
  - Saphire appears in the installed plugin registry
  - Saphire appears in the graph NODE_REGISTRY
  - All param/port IDs come from discovered/ JSON (source of truth)
  - A minimal Saphire patch (VCO -> Saphire -> Audio) proves correctly
"""

import pytest
from vcvpatch.core import Patch
from vcvpatch.metadata import module_metadata, param_id, input_port, output_port
from vcvpatch.graph.modules import NODE_REGISTRY, SaphireNode
from vcvpatch.graph.installed import InstalledRegistry
from vcvpatch.builder import PatchBuilder


AR  = "AgentRack"
FUN = "Fundamental"


def saphire_discovered():
    return module_metadata(AR, "Saphire")


# ---------------------------------------------------------------------------
# Registry (now discovered/ based)
# ---------------------------------------------------------------------------

class TestSaphireRegistry:

    def test_in_installed_registry(self):
        reg = InstalledRegistry()
        assert reg.has(AR, "Saphire"), \
            "AgentRack/Saphire not found in installed plugins -- rebuild and install"

    def test_in_node_registry(self):
        assert "AgentRack/Saphire" in NODE_REGISTRY

    def test_node_class_is_saphire_node(self):
        assert NODE_REGISTRY["AgentRack/Saphire"] is SaphireNode

    def test_params_discovered(self):
        d = saphire_discovered()
        params = d["params"]
        # Verify IDs by canonical API name (source of truth is discovered/ JSON)
        assert param_id(AR, "Saphire", "Mix") == 0
        assert param_id(AR, "Saphire", "Time") == 1
        assert param_id(AR, "Saphire", "Bend") == 2
        assert param_id(AR, "Saphire", "Tone") == 3
        assert param_id(AR, "Saphire", "Pre_delay") == 4

    def test_inputs_discovered(self):
        d = saphire_discovered()
        inputs = d["inputs"]
        assert input_port(AR, "Saphire", "In_L")["id"] == 0
        assert input_port(AR, "Saphire", "In_R")["id"] == 1

    def test_outputs_discovered(self):
        d = saphire_discovered()
        outputs = d["outputs"]
        assert output_port(AR, "Saphire", "Out_L")["id"] == 0
        assert output_port(AR, "Saphire", "Out_R")["id"] == 1

    def test_at_least_five_params(self):
        """Saphire::NUM_PARAMS was 5; IR was added later. At least 5 required."""
        d = saphire_discovered()
        assert len(d["params"]) >= 5


# ---------------------------------------------------------------------------
# Graph node
# ---------------------------------------------------------------------------

class TestSaphireNode:

    def test_audio_inputs(self):
        assert 0 in SaphireNode._audio_inputs   # In L
        assert 1 in SaphireNode._audio_inputs   # In R

    def test_audio_outputs(self):
        assert 0 in SaphireNode._audio_outputs  # Out L
        assert 1 in SaphireNode._audio_outputs  # Out R

    def test_routes(self):
        # L->L and R->R
        assert (0, 0) in SaphireNode._routes
        assert (1, 1) in SaphireNode._routes


# ---------------------------------------------------------------------------
# Patch proof -- use canonical port names from discovered/
# ---------------------------------------------------------------------------

class TestSaphirePatchProof:

    def test_minimal_patch_proves(self):
        """VCO -> Saphire -> AudioInterface2 should prove."""
        pb = PatchBuilder()
        vco  = pb.module(FUN, "VCO")
        sph  = pb.module(AR,  "Saphire", Mix=0.5, Time=0.8, Bend=0.0, Tone=0.7)
        out  = pb.module("Core", "AudioInterface2")

        pb.chain(vco.o.Sine, sph.i.In_L)
        pb.chain(vco.o.Sine, sph.i.In_R)
        pb.chain(sph.o.Out_L, out.i.Left_input)
        pb.chain(sph.o.Out_R, out.i.Right_input)

        patch = pb.build()
        assert isinstance(patch, Patch)
        assert pb.proven, f"Patch not proven:\n{pb.report()}"

    def test_mono_input_patch_proves(self):
        """VCO -> Saphire In L only (mono fold) -> Audio should prove."""
        pb = PatchBuilder()
        vco  = pb.module(FUN, "VCO")
        sph  = pb.module(AR,  "Saphire", Mix=0.65)
        out  = pb.module("Core", "AudioInterface2")

        pb.chain(vco.o.Sine, sph.i.In_L)
        pb.chain(sph.o.Out_L, out.i.Left_input)
        pb.chain(sph.o.Out_R, out.i.Right_input)

        patch = pb.build()
        assert isinstance(patch, Patch)
        assert pb.proven, f"Patch not proven:\n{pb.report()}"

    def test_saphire_without_output_does_not_prove(self):
        """Saphire with no output connected should raise PatchCompileError."""
        from vcvpatch.builder import PatchCompileError
        pb = PatchBuilder()
        vco = pb.module(FUN, "VCO")
        sph = pb.module(AR,  "Saphire")
        pb.chain(vco.o.Sine, sph.i.In_L)
        # deliberately no output connection
        with pytest.raises(PatchCompileError):
            pb.build()
