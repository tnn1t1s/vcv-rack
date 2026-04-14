"""
Tonnetz triad test -- Marbles triggers chord changes, LFO sweeps triangle selection.

Signal flow:
  Marbles T1 gate     --> Tonnetz TRIG   (random timing for chord changes)
  LFO Triangle (slow) --> Tonnetz CV A   (sweeps through triangles)
  Tonnetz poly out    --> Split --> 3x VCO (sine) --> Mixer --> Audio
"""

import os
import sys

from vcvpatch.builder import PatchBuilder

OUTPUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests", "tonnetz_test.vcv"
)

FUN = "Fundamental"
AR  = "AgentRack"
AI  = "AudibleInstruments"


def build() -> str:
    pb = PatchBuilder()

    # Marbles: random gate source for chord triggers
    marbles = pb.module(AI, "Marbles")

    # Slow LFO: sweeps CV A across the lattice (~0.1 Hz, unipolar 0-10V)
    lfo = pb.module(FUN, "LFO", Frequency=-1.5, Offset=1)

    # Tonnetz: ROOT=C, full attenuators
    tonnetz = pb.module(AR, "Tonnetz",
                        **{"0": 0.0,    # ROOT = C
                           "1": 1.0,    # SPREAD atten
                           "2": 1.0})   # FOCUS atten

    # Marbles T1 gate -> Tonnetz TRIG
    pb.connect(marbles.out_id(0), tonnetz.in_id(3))   # t1 -> TRIG

    # LFO triangle -> Tonnetz CV A (which triangle)
    pb.connect(lfo.o.Triangle, tonnetz.in_id(0))      # -> CV A

    # Split poly into 3 mono channels
    split = pb.module(FUN, "Split")
    pb.connect(tonnetz.out_id(0), split.in_id(0))

    # 3 simple sine VCOs
    vco1 = pb.module(FUN, "VCO")
    vco2 = pb.module(FUN, "VCO")
    vco3 = pb.module(FUN, "VCO")
    pb.connect(split.out_id(0), vco1.i._1V_octave_pitch)
    pb.connect(split.out_id(1), vco2.i._1V_octave_pitch)
    pb.connect(split.out_id(2), vco3.i._1V_octave_pitch)

    # Mixer -> audio
    mixer = pb.module(FUN, "Mixer")
    pb.connect(vco1.o.Sine, mixer.in_id(0))
    pb.connect(vco2.o.Sine, mixer.in_id(1))
    pb.connect(vco3.o.Sine, mixer.in_id(2))

    audio = pb.module("Core", "AudioInterface2")
    pb.connect(mixer.o.Mix, audio.i.Left_input)
    pb.connect(mixer.o.Mix, audio.i.Right_input)

    pb.build().save(OUTPUT)  # bypass proof (Tonnetz not in registry yet)
    return OUTPUT


if __name__ == "__main__":
    path = build()
    print(f"Saved: {path}")
