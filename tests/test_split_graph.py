from vcvpatch.builder import PatchBuilder
from vcvpatch.core import CableType, Patch
from vcvpatch.graph.modules import NODE_REGISTRY, SplitNode


FUN = "Fundamental"
AR = "AgentRack"
IM = "ImpromptuModular"


def test_split_is_registered_as_graph_node():
    assert NODE_REGISTRY["Fundamental/Split"] is SplitNode


def test_split_preserves_cv_for_tonnetz_voice_routing():
    pb = PatchBuilder()

    clock = pb.module(IM, "Clocked-Clkd", Master_clock=75, Run=1)
    lfo = pb.module(FUN, "LFO", Frequency=-1.5, Offset=1)
    tonnetz = pb.module(AR, "Tonnetz")
    split = pb.module(FUN, "Split")
    voice = pb.module(FUN, "VCO")

    pb.connect(clock.o.Clock_0, tonnetz.i.Trigger)
    pb.connect(lfo.o.Triangle, tonnetz.i.CV_1_triangle_select)
    pb.connect(tonnetz.o.Chord_poly_V_Oct, split.in_id(0))
    pb.connect(split.out_id(0), voice.i._1V_octave_pitch)

    assert pb._records[-1].cable_type == CableType.CV


def test_split_preserves_audio_for_downstream_audio_routing():
    pb = PatchBuilder()

    vco = pb.module(FUN, "VCO")
    split = pb.module(FUN, "Split")
    vcf = pb.module(FUN, "VCF")
    audio = pb.module("Core", "AudioInterface2")

    pb.connect(vco.o.Sine, split.in_id(0))
    pb.connect(split.out_id(0), vcf.i.Audio)
    assert pb._records[-1].cable_type == CableType.AUDIO

    pb.connect(vcf.out_id(0), audio.i.Left_input)

    patch = pb.build()
    assert isinstance(patch, Patch)
    assert pb.proven, pb.report()
