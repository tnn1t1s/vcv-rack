"""
Noise percussion test patch -- sequencer-gated noise through reverb.

Row 0 (control):  Clock | SEQ3 | ADSR | VCA
Row 1 (audio):    Noise | Attenuate | Saphire | AudioInterface2

Signal flow:
  Clock.MULT   ──►  SEQ3.CLOCK
  SEQ3.TRIG    ──►  ADSR.GATE

  Noise.WHITE  ──►  VCA.IN1          (gated burst on each step)
  ADSR.ENV     ──►  VCA.LIN1

  Noise.CRACKLE ──►  Att.IN_0  (×0.4)  ──►  Saphire.IN_L  (ambient crackle)
  VCA.OUT1      ──►  Att.IN_1  (×0.8)  ──►  Saphire.IN_R  (sequenced noise)

  Saphire.OUT_L ──►  Audio.IN_L
  Saphire.OUT_R ──►  Audio.IN_R

Row 1 column widths:
  Noise=8HP  Attenuate=8HP  Saphire=8HP  Audio=12HP  → 36HP total
"""

import math
import os
import sys

from vcvpatch.builder import PatchBuilder

OUTPUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests", "saphire_test.vcv"
)

AR   = "AgentRack"
SC   = "SlimeChild-Substation"
FUN  = "Fundamental"
CORE = "Core"

# Row 0 — control: Clock(8HP), SEQ3(8HP), ADSR(6HP), VCA(4HP)
C_CLOCK = 0
C_SEQ3  = C_CLOCK + 8
C_ADSR  = C_SEQ3  + 8
C_VCA   = C_ADSR  + 6

# Row 1 — audio: all 8HP columns
C_NOISE   = 0
C_ATT     = C_NOISE   + 8
C_SAPHIRE = C_ATT     + 8
C_AUDIO   = C_SAPHIRE + 8


def build() -> str:
    pb = PatchBuilder()

    # ── Row 0: Control ──────────────────────────────────────────────────────
    clock = pb.module(SC, "SlimeChild-Substation-Clock",
                      pos=[C_CLOCK, 0],
                      TEMPO=math.log2(90 / 60),
                      RUN=1,
                      MULT=1)

    # Sparse gate pattern: steps 1, 3, 5, 8 (euclidean-ish)
    gate_pattern = [1, 0, 1, 0, 1, 0, 0, 1]
    seq_params = {f"GATE_{i}": gate_pattern[i] for i in range(8)}
    seq_params["RUN"] = 1
    seq = pb.module(FUN, "SEQ3", pos=[C_SEQ3, 0], **seq_params)
    pb.chain(clock.o.MULT, seq.i.CLOCK)

    adsr = pb.module(AR, "ADSR", pos=[C_ADSR, 0],
                     ATTACK=0.005, DECAY=0.12, SUSTAIN=0.0, RELEASE=0.3)
    pb.chain(seq.o.TRIG, adsr.i.GATE)

    vca = pb.module(FUN, "VCA", pos=[C_VCA, 0])
    pb.chain(adsr.o.ENV, vca.i.LIN1)

    # ── Row 1: Audio ────────────────────────────────────────────────────────
    noise = pb.module(AR, "Noise", pos=[C_NOISE, 1])

    pb.chain(noise.o.WHITE, vca.i.IN1)

    att = pb.module(AR, "Attenuate", pos=[C_ATT, 1],
                    SCALE_0=0.4,   # CRACKLE → Saphire L (ambient)
                    SCALE_1=0.8)   # gated WHITE → Saphire R (percussion)

    pb.chain(noise.o.CRACKLE, att.i.IN_0)
    pb.chain(vca.o.OUT1,      att.i.IN_1)

    saphire = pb.module(AR, "Saphire", pos=[C_SAPHIRE, 1],
                        MIX=1.0, TIME=0.7, BEND=0.0, TONE=0.7, PRE=0.0, IR=38)
    pb.chain(att.o.OUT_0, saphire.i.IN_L)
    pb.chain(att.o.OUT_1, saphire.i.IN_R)

    audio = pb.module(CORE, "AudioInterface2", pos=[C_AUDIO, 1])
    pb.chain(saphire.o.OUT_L, audio.i.IN_L)
    pb.chain(saphire.o.OUT_R, audio.i.IN_R)

    pb.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    path = build()
    print(f"Saved: {path}")
