"""
Interstellar Drift -- cinematic Cm progression via Tonnetz.

16 bars of 4/4 at whole-note chord changes (4 bars each):
  Cm7     (tri 17+18)  bars 1-4
  Abmaj7  (tri 16+17)  bars 5-8
  Ebmaj7  (tri 18+19)  bars 9-12
  Bbmaj7  (tri 20+21)  bars 13-16

All adjacent triangle stacks; smooth voice leading throughout.
Dark, cinematic, slow-evolving.

Signal flow:
  LFO -> Pgmr (+ PgmrX)
  Pgmr Ch A -> Tonnetz CV1
  Pgmr Ch B -> Tonnetz CV2
  Pgmr Ch C -> ADSR GATE
  Pgmr Step trigger -> Tonnetz TRIG
  Tonnetz CHORD -> VCO V/Oct -> Ladder -> Saphire -> Audio
"""

import os
import sys
from pathlib import Path

from vcvpatch import PatchBuilder, RackLayout

OUTPUT = str(Path(__file__).resolve().parents[2] / "tests" / "interstellar.vcv")

FUN = "Fundamental"
AR  = "AgentRack"
BOG = "Bogaudio"

NOTES = """Interstellar Drift
Cinematic Cm progression via Tonnetz stacking.

Cm7 (17+18) | Abmaj7 (16+17) | Ebmaj7 (18+19) | Bbmaj7 (20+21)

4 bars each, 16 bars total.
LFO at ~0.25Hz = whole notes."""


def tri_voltage(index):
    """CV voltage (0-10V) that maps to triangle index via floor(v * 32 / 10)."""
    return (index + 0.5) * 10.0 / 32.0


PGMR_SCALE = 10.0

def tri_param(index):
    """Pgmr param value for a triangle index."""
    return tri_voltage(index) / PGMR_SCALE


# 8-step pattern: each step = 2 bars (half-note clock), 4 bars per chord
# Chords: Cm7(17+18), Abmaj7(16+17), Ebmaj7(18+19), Bbmaj7(20+21)
#          step 1,2     step 3,4       step 5,6        step 7,8
CV1  = [17, 17, 16, 16, 18, 18, 20, 20]
CV2  = [18, 18, 17, 17, 19, 19, 21, 21]
GATE = [ 1,  0,  1,  0,  1,  0,  1,  0]


def pgmr_main_params(offset):
    """Pgmr main module params for 4 steps starting at offset."""
    p = {
        "0": 1,   # Direction = forward
        "1": 1,   # Select on clock = auto-advance
    }
    for s in range(4):
        pos = offset + s
        base = 2 + s * 5
        p[str(base + 0)] = tri_param(CV1[pos])
        p[str(base + 1)] = tri_param(CV2[pos])
        p[str(base + 2)] = float(GATE[pos])
        p[str(base + 3)] = 0.0  # unused channel D
        p[str(base + 4)] = 1    # Select = enabled
    return p


def pgmrx_params(offset):
    """PgmrX expander params for 4 steps starting at offset."""
    p = {}
    for s in range(4):
        pos = offset + s
        base = s * 5
        p[str(base + 0)] = tri_param(CV1[pos])
        p[str(base + 1)] = tri_param(CV2[pos])
        p[str(base + 2)] = float(GATE[pos])
        p[str(base + 3)] = 0.0
        p[str(base + 4)] = 1
    return p


def build() -> str:
    pb = PatchBuilder()
    layout = RackLayout()
    top_row = layout.row(0)
    middle_row = layout.row(1)
    bottom_row = layout.row(2)

    # Notes
    notes = pb.module("Core", "Notes", position=top_row.at(0), data={"text": NOTES})

    # Clock: LFO at ~0.25Hz (one pulse per 2 bars at ~120 BPM half-note)
    lfo = pb.module(FUN, "LFO", position=top_row.at(18), Frequency=0.25)

    # Pgmr + PgmrX = 8 steps
    pgmr = pb.module(BOG, "Bogaudio-Pgmr", position=middle_row.at(18), **pgmr_main_params(0))
    pgx1 = pb.module(BOG, "Bogaudio-PgmrX", position=middle_row.at(32), **pgmrx_params(4))

    # Tonnetz
    tonnetz = pb.module(AR, "Tonnetz", position=middle_row.at(46))

    # ADSR: slow attack for pad-like swells
    adsr = pb.module(FUN, "ADSR", position=top_row.at(36),
                     Attack=0.3, Decay=0.4, Sustain=0.7, Release=0.6)

    # VCO -> Ladder -> Saphire -> Audio
    vco    = pb.module(FUN, "VCO", position=bottom_row.at(46))
    ladder = pb.module(AR, "Ladder", position=bottom_row.at(58), Cutoff=9.5, Resonance=0.3, Spread=0.15)
    saphire = pb.module(AR, "Saphire", position=bottom_row.at(70), Mix=0.45, Time=0.7, Bend=0.1, Tone=0.5)
    vca    = pb.module(FUN, "VCA", position=bottom_row.at(84))
    audio  = pb.module("Core", "AudioInterface2", position=bottom_row.at(96))

    # Signal flow: LFO -> Pgmr -> Tonnetz -> VCO -> Ladder -> Saphire -> Audio

    # Clock
    pb.connect(lfo.o.Square, pgmr.i.Clock)

    # Pgmr -> Tonnetz
    pb.connect(pgmr.output(0), tonnetz.input(0))    # Ch A -> CV1
    pb.connect(pgmr.output(1), tonnetz.input(1))    # Ch B -> CV2
    pb.connect(pgmr.output(4), tonnetz.input(3))    # Step trigger -> TRIG

    # Pgmr Ch C -> ADSR gate
    pb.connect(pgmr.output(2), adsr.i.Gate)

    # Tonnetz -> VCO -> Ladder -> VCA -> Saphire -> Audio
    pb.connect(tonnetz.output(0), vco.input(0))      # CHORD -> V/Oct
    pb.connect(vco.o.Sine, ladder.i.Audio)
    pb.connect(ladder.o.Out, vca.input(2))            # Ladder -> VCA In
    pb.connect(adsr.o.ENV, vca.input(1))         # ADSR -> VCA CV
    pb.connect(vca.output(0), saphire.input(0))       # -> In L
    pb.connect(saphire.output(0), audio.input(0))     # Out L ->
    pb.connect(saphire.output(1), audio.input(1))     # Out R ->

    print(f"Proven: {pb.proven}")
    print(f"Status: {pb.status}")
    if pb.proven:
        pb.save(OUTPUT)
        print(f"Saved: {OUTPUT}")
    else:
        pb.build().save(OUTPUT)
        print(f"Saved (unproven): {OUTPUT}")

    return OUTPUT


if __name__ == "__main__":
    build()
