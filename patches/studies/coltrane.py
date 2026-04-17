"""
Coltrane Lattice -- Giant Steps-inspired major 7ths via Tonnetz.

16 bars of 4/4 at whole-note chord changes (4 bars each):
  Cmaj7   (tri 24+25)  bars 1-4
  Ebmaj7  (tri 18+19)  bars 5-8
  Gbmaj7  (tri 12+13)  bars 9-12
  Amaj7   (tri 30+31)  bars 13-16

Major 7ths moving by major thirds (augmented triad cycle).
The Tonnetz lattice was built for this motion. Wide voice leading
jumps give tension; the symmetry provides coherence.

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

from vcvpatch.builder import PatchBuilder

OUTPUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests", "coltrane.vcv"
)

FUN = "Fundamental"
AR  = "AgentRack"
BOG = "Bogaudio"

NOTES = """Coltrane Lattice
Giant Steps: maj7 chords moving by major thirds.

Cmaj7 (24+25) | Ebmaj7 (18+19) | Gbmaj7 (12+13) | Amaj7 (30+31)

Augmented triad cycle of maj7 chords.
The Tonnetz was built for this."""


def tri_voltage(index):
    return (index + 0.5) * 10.0 / 32.0


PGMR_SCALE = 10.0

def tri_param(index):
    return tri_voltage(index) / PGMR_SCALE


# 8-step pattern: each step = 2 bars, 4 bars per chord
# Cmaj7(24+25), Ebmaj7(18+19), Gbmaj7(12+13), Amaj7(30+31)
CV1  = [24, 24, 18, 18, 12, 12, 30, 30]
CV2  = [25, 25, 19, 19, 13, 13, 31, 31]
GATE = [ 1,  0,  1,  0,  1,  0,  1,  0]


def pgmr_main_params(offset):
    p = {
        "0": 1,
        "1": 1,
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

    notes = pb.module("Core", "Notes", data={"text": NOTES})

    # Clock
    lfo = pb.module(FUN, "LFO", Frequency=0.25)

    # Pgmr + PgmrX = 8 steps
    pgmr = pb.module(BOG, "Bogaudio-Pgmr",  **pgmr_main_params(0))
    pgx1 = pb.module(BOG, "Bogaudio-PgmrX", **pgmrx_params(4))

    tonnetz = pb.module(AR, "Tonnetz")

    # ADSR: slightly more percussive for the jazz feel
    adsr = pb.module(FUN, "ADSR",
                     ATTACK=0.1, DECAY=0.4, SUSTAIN=0.6, RELEASE=0.5)

    # VCO -> Ladder -> Saphire -> Audio
    vco     = pb.module(FUN, "VCO")
    ladder  = pb.module(AR, "Ladder", Cutoff=10.0, Resonance=0.15, Spread=0.1)
    saphire = pb.module(AR, "Saphire", Mix=0.35, Time=0.5, Bend=0.0, Tone=0.7)
    vca     = pb.module(FUN, "VCA")
    audio   = pb.module("Core", "AudioInterface2")

    # Signal flow: LFO -> Pgmr -> Tonnetz -> VCO -> Ladder -> VCA -> Saphire -> Audio

    pb.connect(lfo.o.Square, pgmr.i.Clock)

    pb.connect(pgmr.output(0), tonnetz.input(0))
    pb.connect(pgmr.output(1), tonnetz.input(1))
    pb.connect(pgmr.output(4), tonnetz.input(3))

    pb.connect(pgmr.output(2), adsr.i.Gate)

    pb.connect(tonnetz.output(0), vco.input(0))
    pb.connect(vco.o.Sine, ladder.i.Audio)
    pb.connect(ladder.o.Out, vca.input(2))
    pb.connect(adsr.o.Envelope, vca.input(1))
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
