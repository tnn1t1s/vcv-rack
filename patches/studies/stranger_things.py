"""
Stranger Things theme -- CMaj7 arpeggio C-E-G-B-C-B-G-E at 16th notes.

Signal flow (same as slimechild_demo, PolySeq replaced with SEQ3 for 8 steps):
  Clock MULT(x4)  -> SEQ3 CLOCK
  SEQ3 CV1        -> Quantizer IN   (exact CMaj7 voltages, quantized to C major)
  Quantizer OUT   -> SubOsc VOCT
  SEQ3 TRIG       -> Envelopes TRIG1 + TRIG2

  SubOsc BASE+SUB1+SUB2 -> Mixer -> Filter -> VCA -> AudioInterface2
  Envelopes ENV1  -> VCA CV
  Envelopes ENV2  -> Filter FM
"""

import math
import os
import sys
from pathlib import Path

from vcvpatch import PatchBuilder, RackLayout

OUTPUT = str(Path(__file__).resolve().parents[2] / "tests" / "stranger_things.vcv")

PLUGIN = "SlimeChild-Substation"

# CMaj7 arpeggio: C-E-G-B-C-B-G-E in 1V/oct (C4 = 0V)
C, E, G, B = 0.0, 4/12, 7/12, 11/12
STEPS = [C, E, G, B, C+1, B, G, E]


def build() -> str:
    pb = PatchBuilder()
    layout = RackLayout()
    top_row = layout.row(0)
    middle_row = layout.row(1)
    bottom_row = layout.row(2)

    # Clock: 120 BPM, x4 multiplier for 16th notes
    clock = pb.module(PLUGIN, "SlimeChild-Substation-Clock",
                      pos=top_row.at(0),
                      TEMPO=math.log2(120 / 60), RUN=1, MULT=4)

    # SEQ3: 8-step sequencer, steps set to CMaj7 voltages
    seq = pb.module("Fundamental", "SEQ3", pos=top_row.at(14), **{
        f"CV_1_step_{i+1}": v for i, v in enumerate(STEPS)
    })

    # Quantizer: C major (CMaj7 notes C/E/G/B are all in C major)
    quant = pb.module(PLUGIN, "SlimeChild-Substation-Quantizer",
                      pos=middle_row.at(14),
                      ROOT=0, OCTAVE=0)

    # SubOscillator: sine-ish wave, slight detune for that synth shimmer
    subosc = pb.module(PLUGIN, "SlimeChild-Substation-SubOscillator",
                       pos=middle_row.at(28),
                       BASE_FREQ=0, WAVEFORM=0,
                       SUBDIV1=2,   # one octave below
                       SUBDIV2=4,   # two octaves below
                       PWM=0.5, DETUNE=0.01)

    # Envelopes: fast attack, medium decay for arpeggio articulation
    envs = pb.module(PLUGIN, "SlimeChild-Substation-Envelopes",
                     pos=top_row.at(30),
                     EG1_ATTACK=-4, EG1_DECAY=-1,
                     EG2_ATTACK=-4, EG2_DECAY=0,
                     HOLD=0)

    # Mixer: blend root + subs (heavier on root for melody clarity)
    mixer = pb.module(PLUGIN, "SlimeChild-Substation-Mixer",
                      pos=middle_row.at(42),
                      LEVEL1=0.9, LEVEL2=0.4, LEVEL3=0.2,
                      MIX_LEVEL=1.0, DRIVE=0.1)

    # Filter: slightly open, envelope sweep for movement
    filt = pb.module(PLUGIN, "SlimeChild-Substation-Filter",
                     pos=bottom_row.at(42),
                     FREQ=3.5, RES=0.2, FM=0.5)

    # VCA
    vca = pb.module(PLUGIN, "SlimeChild-Substation-VCA", pos=bottom_row.at(56))

    # Audio output
    audio = pb.module("Core", "AudioInterface2", pos=bottom_row.at(68))

    # --- Wiring ---

    # Clock -> SEQ3
    pb.chain(clock.o.MULT, seq.i.Clock)

    # SEQ3 -> pitch chain
    pb.chain(seq.o.CV_1, quant.i.IN)
    pb.chain(quant.o.OUT, subosc.i.VOCT)

    # SEQ3 trigger -> envelopes
    pb.chain(seq.o.Trigger, envs.i.TRIG1)
    pb.chain(seq.o.Trigger, envs.i.TRIG2)

    # SubOsc layers -> mixer
    pb.chain(subosc.o.BASE, mixer.i.IN1)
    pb.chain(subosc.o.SUB1, mixer.i.IN2)
    pb.chain(subosc.o.SUB2, mixer.i.IN3)

    # Mixer -> filter -> VCA -> output
    pb.chain(mixer.o.OUT, filt.i.IN)
    pb.chain(envs.o.ENV2, filt.i.FM)
    pb.chain(filt.o.OUT,  vca.i.IN)
    pb.chain(envs.o.ENV1, vca.i.CV)
    pb.chain(vca.o.OUT, audio.i.Left_input)
    pb.chain(vca.o.OUT, audio.i.Right_input)

    print(pb.status)
    if not pb.proven:
        print("\nProof report:")
        print(pb.report())
        sys.exit(1)

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    patch = pb.build()
    patch.save(OUTPUT)
    print(f"Saved: {OUTPUT}")
    return OUTPUT


if __name__ == "__main__":
    build()
