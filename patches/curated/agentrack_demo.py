"""
AgentRack Demo -- exercises all four custom modules alongside SlimeChild Substation.

Signal flow:
  SlimeChild/Clock (120 BPM, x4)  -->  SEQ3 CLOCK
  SEQ3 CV_A                        -->  Crinkle V/OCT   (melody)
  SEQ3 TRIG                        -->  ADSR GATE        (amplitude envelope)
  Fundamental/LFO SIN              -->  Attenuate IN     (slow timbre sweep)
  Attenuate OUT                    -->  Crinkle TIMBRE   (wavefold modulation)

  Crinkle OUT                      -->  SlimeChild/Filter IN
  ADSR ENV                         -->  SlimeChild/Filter FM  (envelope filter sweep)
  SlimeChild/Filter OUT            -->  Fundamental/VCA IN1
  ADSR ENV                         -->  Fundamental/VCA LIN1  (amplitude)
  Fundamental/VCA OUT1             -->  AudioInterface2 L + R

Melody: C minor pentatonic, 8 steps at 16th notes, 120 BPM
"""

import math
import os
from pathlib import Path

from vcvpatch import PatchBuilder, RackLayout

OUTPUT = str(Path(__file__).resolve().parents[2] / "tests" / "agentrack_demo.vcv")

AR  = "AgentRack"
SC  = "SlimeChild-Substation"
FUN = "Fundamental"

# C minor pentatonic: C Eb F G Bb  (in volts, 1V/oct, C4 = 0V)
SEMITONE = 1 / 12
MELODY = [
    0 * SEMITONE,   # C
    3 * SEMITONE,   # Eb
    5 * SEMITONE,   # F
    7 * SEMITONE,   # G
    10 * SEMITONE,  # Bb
    7 * SEMITONE,   # G
    5 * SEMITONE,   # F
    3 * SEMITONE,   # Eb
]


def build() -> str:
    pb = PatchBuilder()
    layout = RackLayout()
    top_row = layout.row(0)
    voice_row = layout.row(1)
    output_row = layout.row(2)

    # ---- Clock: 120 BPM, MULT=4 for 16th notes ---------------------------------
    clock = pb.module(SC, "SlimeChild-Substation-Clock",
                      pos=top_row.at(0),
                      TEMPO=math.log2(120 / 60),   # = 1.0
                      RUN=1,
                      MULT=4)

    # ---- SEQ3: 8-step C minor pentatonic melody, all gates on ------------------
    seq_params = {f"CV_0_{i}": v for i, v in enumerate(MELODY)}
    seq_params.update({f"GATE_{i}": 1 for i in range(8)})
    seq_params["RUN"] = 1
    seq = pb.module(FUN, "SEQ3", pos=top_row.at(14), **seq_params)
    pb.chain(clock.o.MULT, seq.i.CLOCK)

    # ---- LFO: very slow (~0.07 Hz), bipolar, for timbre sweep ------------------
    lfo = pb.module(FUN, "LFO", pos=top_row.at(34), FREQ=-1.2, OFFSET=0)   # OFFSET=0 = bipolar ±5V

    # ---- Crinkle: wavefolder oscillator, mild starting timbre ------------------
    crinkle = pb.module(AR, "Crinkle", pos=voice_row.at(14),
                        TUNE=0.0, TIMBRE=0.15, SYMMETRY=0.1, TIMBRE_CV=1.0)
    pb.chain(seq.o.CV1, crinkle.i.VOCT)

    # ---- Attenuate: scale LFO ±5V to ~±0.25 so timbre sweeps 0.15±0.25 --------
    att = pb.module(AR, "Attenuate", pos=top_row.at(42), SCALE=0.4)    # 5V * 0.4 = 2V swing → ±0.2 timbre
    pb.chain(lfo.o.SIN, att.i.IN)
    pb.chain(att.o.OUT, crinkle.i.TIMBRE)

    # ---- AgentRack ADSR: snappy attack, medium decay, held sustain -------------
    adsr = pb.module(AR, "ADSR", pos=voice_row.at(26),
                     ATTACK=0.01, DECAY=0.15, SUSTAIN=0.65, RELEASE=0.4)
    pb.chain(seq.o.TRIG, adsr.i.GATE)

    # ---- Ladder: Huovilainen ladder LP, envelope sweep via CUTOFF_MOD ----------
    filt = pb.module(AR, "Ladder", pos=voice_row.at(38), FREQ=0.55, RES=0.3)
    pb.chain(crinkle.o.OUT, filt.i.IN)
    pb.chain(adsr.o.ENV,    filt.i.CUTOFF_MOD)

    # ---- Fundamental VCA: linear, driven by ADSR envelope ---------------------
    vca = pb.module(FUN, "VCA", pos=output_row.at(38))
    pb.chain(filt.o.OUT,  vca.i.IN1)
    pb.chain(adsr.o.ENV,  vca.i.LIN1)

    # ---- Audio output ----------------------------------------------------------
    audio = pb.module("Core", "AudioInterface2", pos=output_row.at(50))
    pb.chain(vca.o.OUT1, audio.i.IN_L)
    pb.chain(vca.o.OUT1, audio.i.IN_R)

    pb.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    path = build()
    print(f"Saved: {path}")
