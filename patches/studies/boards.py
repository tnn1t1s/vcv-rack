"""
Boards of Canada -- nostalgic D major progression via Tonnetz.

16 bars of 4/4 at whole-note chord changes (4 bars each):
  Dmaj7   (tri 28+29)  bars 1-4
  Bm7     (tri 27+28)  bars 5-8
  Gmaj7   (tri 26+27)  bars 9-12
  A major (tri 30)     bars 13-16

I-vi-IV-V in D major with 7ths. Last chord is plain A triad for resolution.
Warm, analog, hazy.

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

OUTPUT = str(Path(__file__).resolve().parents[2] / "tests" / "boards.vcv")

FUN = "Fundamental"
AR  = "AgentRack"
BOG = "Bogaudio"

NOTES = """Boards of Canada
Nostalgic D major progression via Tonnetz stacking.

Dmaj7 (28+29) | Bm7 (27+28) | Gmaj7 (26+27) | A (30+30)

I-vi-IV-V in D, 4 bars each, 16 bars total.
Warm, detuned, hazy."""


def tri_voltage(index):
    return (index + 0.5) * 10.0 / 32.0


PGMR_SCALE = 10.0

def tri_param(index):
    return tri_voltage(index) / PGMR_SCALE


# 8-step pattern: each step = 2 bars, 4 bars per chord
# Dmaj7(28+29), Bm7(27+28), Gmaj7(26+27), A(30+30)
CV1  = [28, 28, 27, 27, 26, 26, 30, 30]
CV2  = [29, 29, 28, 28, 27, 27, 30, 30]
GATE = [ 1,  0,  1,  0,  1,  0,  1,  0]


def pgmr_main_params(offset):
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
        p[str(base + 3)] = 0.0
        p[str(base + 4)] = 1
    return p


def pgmrx_params(offset):
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

    notes = pb.module("Core", "Notes", pos=top_row.at(0), data={"text": NOTES})

    # Clock
    lfo = pb.module(FUN, "LFO", pos=top_row.at(18), Frequency=0.25)

    # Pgmr + PgmrX = 8 steps
    pgmr = pb.module(BOG, "Bogaudio-Pgmr", pos=middle_row.at(18), **pgmr_main_params(0))
    pgx1 = pb.module(BOG, "Bogaudio-PgmrX", pos=middle_row.at(32), **pgmrx_params(4))

    tonnetz = pb.module(AR, "Tonnetz", pos=middle_row.at(46))

    # ADSR: gentle pad envelope
    adsr = pb.module(FUN, "ADSR", pos=top_row.at(36),
                     Attack=0.4, Decay=0.3, Sustain=0.8, Release=0.5)

    # VCO -> Ladder (warm filter) -> Saphire (reverb) -> Audio
    vco     = pb.module(FUN, "VCO", pos=bottom_row.at(46))
    ladder  = pb.module(AR, "Ladder", pos=bottom_row.at(58),
                        Cutoff=9.0, Resonance=0.2, Spread=0.25, Shape=0.3)
    saphire = pb.module(AR, "Saphire", pos=bottom_row.at(70),
                        Mix=0.5, Time=0.6, Bend=0.15, Tone=0.4)
    vca     = pb.module(FUN, "VCA", pos=bottom_row.at(84))
    audio   = pb.module("Core", "AudioInterface2", pos=bottom_row.at(96))

    # Signal flow: LFO -> Pgmr -> Tonnetz -> VCO -> Ladder -> VCA -> Saphire -> Audio

    pb.connect(lfo.o.Square, pgmr.i.Clock)

    pb.connect(pgmr.output(0), tonnetz.input(0))
    pb.connect(pgmr.output(1), tonnetz.input(1))
    pb.connect(pgmr.output(4), tonnetz.input(3))

    pb.connect(pgmr.output(2), adsr.i.Gate)

    pb.connect(tonnetz.output(0), vco.input(0))
    pb.connect(vco.o.Sine, ladder.i.Audio)
    pb.connect(ladder.o.Out, vca.input(2))
    pb.connect(adsr.o.ENV, vca.input(1))
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
