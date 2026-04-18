"""
Tonnetz Demo -- trigger-addressed chord generator driving three Crinkle voices
through Ladder filter and Saphire reverb.

Signal flow:
  ClockDiv /4         --> Tonnetz TRIG        (chord changes every 4 beats)
  LFO TRI (slow)      --> Tonnetz CV A        (sweeps through lattice triangles)
  Tonnetz CHORD ch0    --> Crinkle 1 V/OCT    (low voice)
  Tonnetz CHORD ch1    --> Crinkle 2 V/OCT    (mid voice)
  Tonnetz CHORD ch2    --> Crinkle 3 V/OCT    (high voice)
  Clock /1             --> ADSR GATE           (per-beat envelope)
  ADSR ENV             --> VCA LIN             (amplitude shaping)
  Crinkle 1+2+3       --> BusCrush IN 1-3     (mix)
  BusCrush OUT L       --> Ladder IN           (filter)
  ADSR ENV             --> Ladder CUTOFF_MOD   (filter sweep)
  Ladder OUT           --> Saphire IN          (reverb)
  Saphire OUT          --> AudioInterface2     (output)

All modules are AgentRack except Core/AudioInterface2.
The patch showcases Tonnetz chord generation with voice leading.
"""

import math
import os
import sys
from pathlib import Path

from vcvpatch import PatchBuilder, RackLayout

OUTPUT = str(Path(__file__).resolve().parents[2] / "tests" / "tonnetz_demo.vcv")

AR  = "AgentRack"
FUN = "Fundamental"


def build() -> str:
    pb = PatchBuilder()
    layout = RackLayout()
    top_row = layout.row(0)
    voice_row = layout.row(1)
    output_row = layout.row(2)

    # ---- Clock source: 120 BPM ------------------------------------------------
    clock = pb.module("SlimeChild-Substation", "SlimeChild-Substation-Clock",
                      position=top_row.at(0),
                      TEMPO=math.log2(120 / 60), RUN=1)

    # ---- ClockDiv: /4 for chord changes, /1 passes through for gates ----------
    cdiv = pb.module(AR, "ClockDiv", position=top_row.at(14))
    pb.connect(clock.o.BASE, cdiv.i.Clock)

    # ---- Slow LFO: sweeps CV A across the Tonnetz lattice ---------------------
    # Freq ~ 0.05 Hz (one full cycle ~ 20 sec), unipolar 0-10V
    lfo = pb.module(FUN, "LFO", position=top_row.at(24),
                    Frequency=-2.5, Offset=1)  # Offset=1 = unipolar 0-10V

    # ---- Tonnetz chord generator ----------------------------------------------
    # Tonnetz port IDs: CV_A=0, CV_B=1, CV_C=2, TRIG=3, RESET=4, CHORD_OUT=0
    # Tonnetz param IDs: ROOT=0, SPREAD_ATTEN=1, FOCUS_ATTEN=2
    # No discovered metadata yet, so pass raw integer param IDs
    tonnetz = pb.module(AR, "Tonnetz",
                        position=top_row.at(38),
                        **{"0": 0.0,    # ROOT = C
                           "1": 0.8,    # SPREAD atten = 80%
                           "2": 0.7})   # FOCUS atten = 70%

    # LFO sweeps the triangle selection
    pb.connect(lfo.o.Triangle, tonnetz.in_id(0))       # LFO -> CV A (center)
    pb.connect(cdiv.out_id(1), tonnetz.in_id(3))       # /4 -> TRIG

    # ---- Three Crinkle voices for the triad -----------------------------------
    # Tonnetz outputs 3-channel poly on output 0
    # We need to split poly channels. Use Fundamental/Mult or connect poly directly.
    # Since Crinkle takes monophonic V/OCT, we need a poly split.
    # Use three separate connections from the poly output -- VCV Rack will
    # deliver channel 0 to a mono input by default. We need a splitter.

    # Use Bogaudio/Bogaudio-PolySplit to fan out the 3 poly channels
    # Actually, simpler: use the poly output into a single poly-aware oscillator.
    # But Crinkle is mono. Let's use Fundamental/Split to break poly into mono.

    split = pb.module(FUN, "Split", position=voice_row.at(38))
    pb.connect(tonnetz.out_id(0), split.in_id(0))     # CHORD poly -> Split IN

    voice1 = pb.module(AR, "Crinkle", position=voice_row.at(50), Tune=0.0, Timbre=0.08, Symmetry=0.0)
    voice2 = pb.module(AR, "Crinkle", position=voice_row.at(58), Tune=0.0, Timbre=0.12, Symmetry=0.05)
    voice3 = pb.module(AR, "Crinkle", position=voice_row.at(66), Tune=0.0, Timbre=0.15, Symmetry=0.1)

    pb.connect(split.out_id(0), voice1.i.V_Oct)        # ch 0 -> voice 1
    pb.connect(split.out_id(1), voice2.i.V_Oct)        # ch 1 -> voice 2
    pb.connect(split.out_id(2), voice3.i.V_Oct)        # ch 2 -> voice 3

    # ---- ADSR: medium attack for pad-like feel --------------------------------
    adsr = pb.module(AR, "ADSR", position=top_row.at(52),
                     Attack=0.08, Decay=0.3, Sustain=0.7, Release=0.6)
    pb.connect(clock.o.BASE, adsr.i.Gate)

    # ---- BusCrush: mix the three voices ---------------------------------------
    bus = pb.module(AR, "BusCrush", position=output_row.at(50))
    pb.connect(voice1.o.Out, bus.in_id(0))             # voice 1 -> ch 1
    pb.connect(voice2.o.Out, bus.in_id(1))             # voice 2 -> ch 2
    pb.connect(voice3.o.Out, bus.in_id(2))             # voice 3 -> ch 3

    # ---- VCA: shape amplitude with envelope -----------------------------------
    vca = pb.module(FUN, "VCA", position=output_row.at(64))
    pb.connect(bus.out_id(0), vca.i.IN)           # BusCrush L -> VCA
    pb.connect(adsr.o.Envelope, vca.i.CV)

    # ---- Ladder: gentle lowpass with envelope sweep ---------------------------
    # Cutoff is log2(Hz): log2(800) ~ 9.64, warm but open
    filt = pb.module(AR, "Ladder", position=output_row.at(76),
                     Cutoff=9.64, Resonance=0.25, Spread=0.1, Shape=0.0)
    pb.connect(vca.o.OUT, filt.i.Audio)
    pb.connect(adsr.o.Envelope, filt.i.Cutoff_mod)

    # ---- Saphire: hall reverb ------------------------------------------------
    saphire = pb.module(AR, "Saphire", position=output_row.at(88),
                        Mix=0.55, Time=0.85, Bend=0.0, Tone=0.35)
    pb.connect(filt.o.Out, saphire.i.In_L)
    pb.connect(filt.o.Out, saphire.i.In_R)

    # ---- Audio output ---------------------------------------------------------
    audio = pb.module("Core", "AudioInterface2", position=output_row.at(102))
    pb.connect(saphire.o.Out_L, audio.i.Left_input)
    pb.connect(saphire.o.Out_R, audio.i.Right_input)

    pb.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    path = build()
    print(f"Saved: {path}")
