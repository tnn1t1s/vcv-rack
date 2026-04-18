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
                      position=top_row.at(0),
                      TEMPO=math.log2(120 / 60),   # = 1.0
                      RUN=1,
                      MULT=4)

    # ---- SEQ3: 8-step C minor pentatonic melody, all gates on ------------------
    seq_params = {f"CV_1_step_{i+1}": v for i, v in enumerate(MELODY)}
    seq_params.update({f"Step_{i+1}_trigger": 1 for i in range(8)})
    seq_params["Run"] = 1
    seq = pb.module(FUN, "SEQ3", position=top_row.at(14), **seq_params)
    pb.chain(clock.o.MULT, seq.i.Clock)

    # ---- LFO: very slow (~0.07 Hz), bipolar, for timbre sweep ------------------
    lfo = pb.module(FUN, "LFO", position=top_row.at(34), Frequency=-1.2, Offset=0)   # Offset=0 = bipolar ±5V

    # ---- Crinkle: wavefolder oscillator, mild starting timbre ------------------
    crinkle = pb.module(AR, "Crinkle", position=voice_row.at(14),
                        Tune=0.0, Timbre=0.15, Symmetry=0.1, Timbre_CV=1.0)
    pb.chain(seq.o.CV_1, crinkle.i.V_Oct)

    # ---- Attenuate: scale LFO ±5V to ~±0.25 so timbre sweeps 0.15±0.25 --------
    att = pb.module(AR, "Attenuate", position=top_row.at(42), Scale_1=0.4)    # 5V * 0.4 = 2V swing → ±0.2 timbre
    pb.chain(lfo.o.Sine, att.i.In_1)
    pb.chain(att.o.Out_1, crinkle.i.Timbre_CV)

    # ---- AgentRack ADSR: snappy attack, medium decay, held sustain -------------
    adsr = pb.module(AR, "ADSR", position=voice_row.at(26),
                     Attack=0.01, Decay=0.15, Sustain=0.65, Release=0.4)
    pb.chain(seq.o.Trigger, adsr.i.Gate)

    # ---- Ladder: Huovilainen ladder LP, envelope sweep via CUTOFF_MOD ----------
    filt = pb.module(AR, "Ladder", position=voice_row.at(38), Cutoff=0.55, Resonance=0.3)
    pb.chain(crinkle.o.Out, filt.i.Audio)
    pb.chain(adsr.o.Envelope, filt.i.Cutoff_mod)

    # ---- Fundamental VCA: linear, driven by ADSR envelope ---------------------
    vca = pb.module(FUN, "VCA", position=output_row.at(38))
    pb.chain(filt.o.Out, vca.i.IN)
    pb.chain(adsr.o.Envelope, vca.i.CV)

    # ---- Audio output ----------------------------------------------------------
    audio = pb.module("Core", "AudioInterface2", position=output_row.at(50))
    pb.chain(vca.o.OUT, audio.i.Left_input)
    pb.chain(vca.o.OUT, audio.i.Right_input)

    pb.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    path = build()
    print(f"Saved: {path}")
