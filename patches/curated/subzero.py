"""
Subzero v6 -- Klock-style Fm triad, 303/606 sparse gate pattern.

Sequencer16 STEP params are clamped 0-1V (C4-C5 range).
SubOscillator SUBDIV2=4 drops the bass 2 octaves → F2/Ab2/C3 register.

16-step pattern (~44% density):
Step:  01  02  03  04  05  06  07  08  09  10  11  12  13  14  15  16
Note:  F4  --  C5  --  Ab4 --  C5  F4  --  --  C5  --  Ab4 --  --  --
(2oct) F2  --  C3  --  Ab2 --  C3  F2  --  --  C3  --  Ab2 --  --  --
Gate:  on  off on  off on  off on  on  off off on  off on  off off off

Signal flow:
  Clock(x4) → Sequencer16 CLOCK
  Sequencer16 CV   → Quantizer → SubOsc VOCT
  Sequencer16 TRIG → Envelopes TRIG1+TRIG2  (sparse, only 7/16 steps fire)
  SubOsc BASE+SUB1+SUB2 → Mixer → Filter → VCA → Audio
  ENV1 → VCA | ENV2 → Filter FM
"""

import math
import os
import sys
from pathlib import Path

from vcvpatch import PatchBuilder, RackLayout

OUTPUT = str(Path(__file__).resolve().parents[2] / "tests" / "subzero.vcv")

PLUGIN = "SlimeChild-Substation"

# Sequencer16 STEP params are 0-1V (C4=0V, C5=1V).
# SubOscillator SUBDIV2=4 drops 2 octaves → bass register F2/Ab2/C3.
F4   = 5/12   # 0.417V -- F4, SubOsc SUB2 → F2
Ab4  = 8/12   # 0.667V -- Ab4, SubOsc SUB2 → Ab2
C5   = 1.0    # 1.000V -- C5,  SubOsc SUB2 → C3
REST = 0.0    # gate off, pitch irrelevant

# 16-step Klock-style sparse pattern
# Step:  01    02    03    04    05    06    07    08    09    10    11    12    13    14    15    16
PITCHES = [F4, REST, C5,  REST, Ab4, REST, C5,   F4,  REST, REST, C5,  REST, Ab4,  REST, REST, REST]
GATES   = [1,  0,    1,   0,    1,   0,    1,    1,   0,    0,    1,   0,    1,    0,    0,    0   ]


def build() -> str:
    pb = PatchBuilder()
    layout = RackLayout()
    top_row = layout.row(0)
    middle_row = layout.row(1)
    bottom_row = layout.row(2)

    clock = pb.module(PLUGIN, "SlimeChild-Substation-Clock",
                      position=top_row.at(0),
                      TEMPO=math.log2(128 / 60), RUN=1, MULT=4)

    # Sequencer16: pitch values + gate pattern in one module
    seq_params = {}
    for i, (pitch, gate) in enumerate(zip(PITCHES, GATES)):
        seq_params[f"STEP{i+1}"] = pitch
        seq_params[f"TRIG{i+1}"] = float(gate)
    seq_params["LENGTH"]   = 16.0
    seq_params["RANGE_SW"] = 1.0  # 1V full-scale: param 0-1 maps directly to 0-1V

    seq = pb.module("CountModula", "Sequencer16", position=top_row.at(14), **seq_params)

    # Quantizer: F root (set scale to minor/Fm in GUI)
    quant = pb.module(PLUGIN, "SlimeChild-Substation-Quantizer",
                      position=middle_row.at(14),
                      ROOT=5, OCTAVE=0)

    # SubOscillator: saw, heavy subs
    subosc = pb.module(PLUGIN, "SlimeChild-Substation-SubOscillator",
                       position=middle_row.at(28),
                       BASE_FREQ=0, WAVEFORM=1,
                       SUBDIV1=2, SUBDIV2=4,
                       PWM=0.5, DETUNE=0.015)

    # Envelopes: percussive -- very fast attack, short decay
    envs = pb.module(PLUGIN, "SlimeChild-Substation-Envelopes",
                     position=top_row.at(38),
                     EG1_ATTACK=-3,   # instant attack (min=-3)
                     EG1_DECAY=-1.5,  # short percussive decay
                     EG2_ATTACK=-3,   # instant attack on filter
                     EG2_DECAY=-1.0,  # slightly longer filter sweep
                     HOLD=0)

    mixer = pb.module(PLUGIN, "SlimeChild-Substation-Mixer",
                      position=middle_row.at(42),
                      LEVEL1=0.8, LEVEL2=0.5, LEVEL3=0.3,
                      MIX_LEVEL=1.0, DRIVE=0.2)

    filt = pb.module(PLUGIN, "SlimeChild-Substation-Filter",
                     position=bottom_row.at(42),
                     FREQ=1.5, RES=0.3, FM=0.6)

    vca = pb.module(PLUGIN, "SlimeChild-Substation-VCA", position=bottom_row.at(56),
                    LEVEL=0)  # closed by default; ENV1 opens it
    audio = pb.module("Core", "AudioInterface2", position=bottom_row.at(68))

    # Clock → Sequencer16
    pb.chain(clock.o.MULT, seq.i.CLOCK)

    # Pitch: CV → quantizer → subosc
    pb.chain(seq.o.CV,   quant.i.IN)
    pb.chain(quant.o.OUT, subosc.i.VOCT)

    # Trigger: TRIG → envelopes (1ms pulse per step -- tighter, percussive)
    pb.chain(seq.o.TRIG, envs.i.TRIG1)
    pb.chain(seq.o.TRIG, envs.i.TRIG2)

    # Sound chain
    pb.chain(subosc.o.BASE, mixer.i.IN1)
    pb.chain(subosc.o.SUB1, mixer.i.IN2)
    pb.chain(subosc.o.SUB2, mixer.i.IN3)
    pb.chain(mixer.o.OUT,   filt.i.IN)
    pb.chain(envs.o.ENV2,   filt.i.FM)
    pb.chain(filt.o.OUT,    vca.i.IN)
    pb.chain(envs.o.ENV1,   vca.i.CV)
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
