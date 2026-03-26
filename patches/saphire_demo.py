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

import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vcvpatch.builder import PatchBuilder

OUTPUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests", "saphire_demo.vcv"
)

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

    # ---- Clock: 90 BPM, MULT=1 for quarter notes --------------------------------
    clock = pb.module(SC, "SlimeChild-Substation-Clock",
                      TEMPO=math.log2(90 / 60),
                      RUN=1,
                      MULT=1)

    # ---- SEQ3: 8-step C major pentatonic, all gates on -------------------------
    seq_params = {f"CV_0_{i}": v for i, v in enumerate(MELODY)}
    seq_params.update({f"GATE_{i}": 1 for i in range(8)})
    seq_params["RUN"] = 1
    seq = pb.module(FUN, "SEQ3", **seq_params)
    pb.chain(clock.o.MULT, seq.i.CLOCK)

    # ---- Crinkle: wavefolder osc, clean-ish timbre for reverb tail --------------
    crinkle = pb.module(AR, "Crinkle", TUNE=0.0, TIMBRE=0.1, SYMMETRY=0.0)
    pb.chain(seq.o.CV1, crinkle.i.VOCT)

    # ---- ADSR: medium attack/decay, long release for reverb interplay -----------
    adsr = pb.module(AR, "ADSR",
                     ATTACK=0.02, DECAY=0.2, SUSTAIN=0.5, RELEASE=0.8)
    pb.chain(seq.o.TRIG, adsr.i.GATE)

    # ---- VCA: amplitude shaped by envelope -------------------------------------
    vca = pb.module(FUN, "VCA")
    pb.chain(crinkle.o.OUT, vca.i.IN1)
    pb.chain(adsr.o.ENV,    vca.i.LIN1)

    # ---- Saphire: wet-heavy, long tail, slight pre-delay -----------------------
    saphire = pb.module(AR, "Saphire",
                        MIX=0.65, TIME=0.8, BEND=0.0, TONE=0.7, PRE=0.08)
    pb.chain(vca.o.OUT1, saphire.i.IN_L)
    pb.chain(vca.o.OUT1, saphire.i.IN_R)

    # ---- Audio output ----------------------------------------------------------
    audio = pb.module("Core", "AudioInterface2")
    pb.chain(saphire.o.OUT_L, audio.i.IN_L)
    pb.chain(saphire.o.OUT_R, audio.i.IN_R)

    pb.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    path = build()
    print(f"Saved: {path}")
