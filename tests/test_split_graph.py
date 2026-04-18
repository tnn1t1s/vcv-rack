from vcvpatch.builder import PatchBuilder
from vcvpatch.core import CableType, Patch
from vcvpatch.graph.modules import NODE_REGISTRY, ClockDivNode, SplitNode, TonnetzNode
from vcvpatch.graph.node import SignalType
from vcvpatch.layout import RackLayout


FUN = "Fundamental"
AR = "AgentRack"
IM = "ImpromptuModular"


def test_split_is_registered_as_graph_node():
    assert NODE_REGISTRY["Fundamental/Split"] is SplitNode


def test_simple_agent_facing_nodes_can_be_loaded_from_specs():
    assert SplitNode.__module__ == "vcvpatch.graph.specs"
    assert TonnetzNode.__module__ == "vcvpatch.graph.specs"
    assert ClockDivNode.__module__ == "vcvpatch.graph.specs"
    assert TonnetzNode._required_cv[3] == SignalType.GATE


def test_split_preserves_cv_for_tonnetz_voice_routing():
    pb = PatchBuilder()
    layout = RackLayout()
    row0 = layout.row(0)

    clock = pb.module(IM, "Clocked-Clkd", position=row0.at(0), Master_clock=75, Run=1)
    lfo = pb.module(FUN, "LFO", position=row0.at(12), Frequency=-1.5, Offset=1)
    tonnetz = pb.module(AR, "Tonnetz", position=row0.at(24))
    split = pb.module(FUN, "Split", position=row0.at(36))
    voice = pb.module(FUN, "VCO", position=row0.at(44))

    pb.connect(clock.o.Clock_0, tonnetz.i.Trigger)
    pb.connect(lfo.o.Triangle, tonnetz.i.CV_1_triangle_select)
    pb.connect(tonnetz.o.Chord_poly_V_Oct, split.in_id(0))
    pb.connect(split.out_id(0), voice.i._1V_octave_pitch)

    assert pb._records[-1].cable_type == CableType.CV


def test_split_preserves_audio_for_downstream_audio_routing():
    pb = PatchBuilder()
    layout = RackLayout()
    row0 = layout.row(0)

    vco = pb.module(FUN, "VCO", position=row0.at(0))
    split = pb.module(FUN, "Split", position=row0.at(8))
    vcf = pb.module(FUN, "VCF", position=row0.at(16))
    audio = pb.module("Core", "AudioInterface2", position=row0.at(28))

    pb.connect(vco.o.Sine, split.in_id(0))
    pb.connect(split.out_id(0), vcf.i.Audio)
    assert pb._records[-1].cable_type == CableType.AUDIO

    pb.connect(vcf.out_id(0), audio.i.Left_input)

    patch = pb.build()
    assert isinstance(patch, Patch)
    assert pb.proven, pb.report()


def test_controller_specs_support_cv_inference_for_maintained_modules():
    pb = PatchBuilder()
    layout = RackLayout()
    row0 = layout.row(0)

    random = pb.module(FUN, "Random", position=row0.at(0), Internal_trigger_rate=-1.5)
    quant = pb.module("Coffee", "Quant", position=row0.at(12), Note_6=1, Note_11=1)
    dadsr = pb.module("Bogaudio", "Bogaudio-DADSRH", position=row0.at(24))
    mixer = pb.module("mscHack", "Mix_9_3_4", position=row0.at(36))

    pb.connect(random.o.Smooth, quant.i.V_OCT_In)
    assert pb._records[-1].cable_type == CableType.CV

    pb.connect(dadsr.o.Inverted_envelope, mixer.i.Ch5_Level_CV)
    assert pb._records[-1].cable_type == CableType.CV
