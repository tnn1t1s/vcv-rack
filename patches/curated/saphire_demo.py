"""
Saphire Demo -- minimal patch to showcase the convolution reverb.

Signal flow:
  SlimeChild/Clock (90 BPM, x4)   -->  SEQ3 CLOCK
  SEQ3 CV1                         -->  Crinkle V/OCT
  SEQ3 TRIG                        -->  ADSR GATE
  Crinkle OUT                      -->  VCA IN1
  ADSR ENV                         -->  VCA LIN1   (amplitude)
  VCA OUT1                         -->  Saphire IN_L + IN_R
  Saphire OUT_L                    -->  AudioInterface2 IN_L
  Saphire OUT_R                    -->  AudioInterface2 IN_R

Melody: C major pentatonic, 8 steps, quarter notes at 90 BPM
"""

import math
import os
import sys
from pathlib import Path

from vcvpatch import PatchBuilder, RackLayout

OUTPUT = str(Path(__file__).resolve().parents[2] / "tests" / "saphire_demo.vcv")

AR  = "AgentRack"
SC  = "SlimeChild-Substation"
FUN = "Fundamental"

# C major pentatonic: C D E G A
SEMITONE = 1 / 12
MELODY = [
    0  * SEMITONE,   # C4
    2  * SEMITONE,   # D4
    4  * SEMITONE,   # E4
    7  * SEMITONE,   # G4
    9  * SEMITONE,   # A4
    7  * SEMITONE,   # G4
    4  * SEMITONE,   # E4
    2  * SEMITONE,   # D4
]


def build() -> str:
    pb = PatchBuilder()
    layout = RackLayout()
    top_row = layout.row(0)
    voice_row = layout.row(1)

    # ---- Clock: 90 BPM, MULT=1 for quarter notes --------------------------------
    clock = pb.module(SC, "SlimeChild-Substation-Clock",
                      pos=top_row.at(0),
                      TEMPO=math.log2(90 / 60),
                      RUN=1,
                      MULT=1)

    # ---- SEQ3: 8-step C major pentatonic, all gates on -------------------------
    seq_params = {f"CV_1_step_{i+1}": v for i, v in enumerate(MELODY)}
    seq_params.update({f"Step_{i+1}_trigger": 1 for i in range(8)})
    seq_params["Run"] = 1
    seq = pb.module(FUN, "SEQ3", pos=top_row.at(14), **seq_params)
    pb.chain(clock.o.MULT, seq.i.Clock)

    # ---- Crinkle: wavefolder osc, clean-ish timbre for reverb tail --------------
    crinkle = pb.module(AR, "Crinkle", pos=voice_row.at(14),
                        Tune=0.0, Timbre=0.1, Symmetry=0.0)
    pb.chain(seq.o.CV_1, crinkle.i.V_Oct)

    # ---- ADSR: medium attack/decay, long release for reverb interplay -----------
    adsr = pb.module(AR, "ADSR", pos=voice_row.at(26),
                     Attack=0.02, Decay=0.2, Sustain=0.5, Release=0.8)
    pb.chain(seq.o.Trigger, adsr.i.Gate)

    # ---- VCA: amplitude shaped by envelope -------------------------------------
    vca = pb.module(FUN, "VCA", pos=voice_row.at(38))
    pb.chain(crinkle.o.Out, vca.i.IN)
    pb.chain(adsr.o.Envelope, vca.i.CV)

    # ---- Saphire: wet-heavy, long tail, slight pre-delay -----------------------
    saphire = pb.module(AR, "Saphire", pos=voice_row.at(48),
                        Mix=0.65, Time=0.8, Bend=0.0, Tone=0.7, Pre_delay=0.08)
    pb.chain(vca.o.OUT, saphire.i.In_L)
    pb.chain(vca.o.OUT, saphire.i.In_R)

    # ---- Audio output ----------------------------------------------------------
    audio = pb.module("Core", "AudioInterface2", pos=voice_row.at(62))
    pb.chain(saphire.o.Out_L, audio.i.Left_input)
    pb.chain(saphire.o.Out_R, audio.i.Right_input)

    pb.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    path = build()
    print(f"Saved: {path}")
