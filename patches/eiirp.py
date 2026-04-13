"""
Everything In Its Right Place -- Radiohead chord progression via Tonnetz.

20 eighth-note steps (4/4 + 6/4), 7 chord hits:
  Pos  1,2:    F major     (hit, hit)
  Pos  3:      F major     (hold)
  Pos  4:      C major     (hit)
  Pos  5:      C major     (hold)
  Pos  6:      C major     (hit)
  Pos  7:      C major     (hold)
  Pos  8:      Dbmaj7      (hit)
  Pos  9:      Dbmaj7      (hold)
  Pos  10:     Dbmaj7      (hit)
  Pos  11:     Eb6         (hit)
  Pos  12-20:  Eb6         (hold)

Signal flow:
  LFO -> Pgmr (+ 4x PgmrX)
  Pgmr Ch A -> Tonnetz CV1  (primary triangle)
  Pgmr Ch B -> Tonnetz CV2  (stack triangle)
  Pgmr Ch C -> ADSR GATE    (articulate 7 hits)
  Pgmr Ch D -> (downbeat pulse on bar 1 and bar 2)
  Pgmr Step trigger -> Tonnetz TRIG
  Tonnetz CHORD -> VCO V/Oct -> VCA (env from ADSR) -> Audio
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vcvpatch.builder import PatchBuilder

OUTPUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests", "eiirp.vcv"
)

FUN = "Fundamental"
AR  = "AgentRack"
BOG = "Bogaudio"


def tri_voltage(index):
    """CV voltage (0-10V) that maps to triangle index via floor(v * 32 / 10)."""
    return (index + 0.5) * 10.0 / 32.0


# Pgmr output voltage = param * SCALE.
# Bogaudio convention: param -1..1 -> output -10V..10V (assumed).
PGMR_SCALE = 10.0

def tri_param(index):
    """Pgmr param value for a triangle index."""
    return tri_voltage(index) / PGMR_SCALE


# 20-step pattern at eighth-note resolution
#                1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20
CV1  = [        10,10,10,12,12,12,12,17,17,17,20,20,20,20,20,20,20,20,20,20]
CV2  = [        10,10,10,12,12,12,12,18,18,18,21,21,21,21,21,21,21,21,21,21]
GATE = [         1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
DBEAT= [         1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
#                ^bar1                   ^bar2


def pgmr_main_params(offset):
    """Pgmr main module params for 4 steps starting at offset."""
    p = {
        "0": 1,   # Direction = forward
        "1": 1,   # Select on clock = auto-advance
    }
    for s in range(4):
        pos = offset + s
        # Pgmr layout: step N has A,B,C,D at base+0..3, Select at base+4
        # Step 1: params 2-5, sel 6; Step 2: 7-10, sel 11; Step 3: 12-15, sel 16; Step 4: 17-20, sel 21
        base = 2 + s * 5
        p[str(base + 0)] = tri_param(CV1[pos])
        p[str(base + 1)] = tri_param(CV2[pos])
        p[str(base + 2)] = float(GATE[pos])
        p[str(base + 3)] = float(DBEAT[pos])
        p[str(base + 4)] = 1   # Select = enabled
    return p


def pgmrx_params(offset):
    """PgmrX expander params for 4 steps starting at offset."""
    p = {}
    for s in range(4):
        pos = offset + s
        # PgmrX layout: step N has A,B,C,D at base+0..3, Select at base+4
        # Step 1: 0-3, sel 4; Step 2: 5-8, sel 9; Step 3: 10-13, sel 14; Step 4: 15-18, sel 19
        base = s * 5
        p[str(base + 0)] = tri_param(CV1[pos])
        p[str(base + 1)] = tri_param(CV2[pos])
        p[str(base + 2)] = float(GATE[pos])
        p[str(base + 3)] = float(DBEAT[pos])
        p[str(base + 4)] = 1   # Select = enabled
    return p


def build() -> str:
    pb = PatchBuilder()

    # ---- Clock: LFO square at ~2.5Hz (eighth notes at ~75 BPM) ---------------
    lfo = pb.module(FUN, "LFO", Frequency=1.3)

    # ---- Pgmr + 4x PgmrX = 20 steps (must be adjacent) ----------------------
    pgmr = pb.module(BOG, "Bogaudio-Pgmr",  **pgmr_main_params(0))
    pgx1 = pb.module(BOG, "Bogaudio-PgmrX", **pgmrx_params(4))
    pgx2 = pb.module(BOG, "Bogaudio-PgmrX", **pgmrx_params(8))
    pgx3 = pb.module(BOG, "Bogaudio-PgmrX", **pgmrx_params(12))
    pgx4 = pb.module(BOG, "Bogaudio-PgmrX", **pgmrx_params(16))

    # ---- Tonnetz --------------------------------------------------------------
    tonnetz = pb.module(AR, "Tonnetz")

    # ---- ADSR envelope -------------------------------------------------------
    adsr = pb.module(FUN, "ADSR",
                     ATTACK=0.0, DECAY=0.3, SUSTAIN=0.5, RELEASE=0.4)

    # ---- VCO + VCA + Audio ---------------------------------------------------
    vco   = pb.module(FUN, "VCO")
    vca   = pb.module(FUN, "VCA")
    audio = pb.module("Core", "AudioInterface2")

    # Signal flow: LFO -> Pgmr -> Tonnetz -> VCO -> VCA -> Audio

    # Clock
    pb.connect(lfo.o.Square, pgmr.i.Clock)

    # Pgmr -> Tonnetz (use raw IDs for Pgmr outputs / Tonnetz inputs)
    pb.connect(pgmr.output(0), tonnetz.input(0))    # Seq A -> CV1
    pb.connect(pgmr.output(1), tonnetz.input(1))    # Seq B -> CV2
    pb.connect(pgmr.output(4), tonnetz.input(3))    # Step trigger -> TRIG

    # Pgmr Ch C -> ADSR gate
    pb.connect(pgmr.output(2), adsr.i.Gate)

    # Tonnetz chord -> VCO pitch (mono, channel 0)
    pb.connect(tonnetz.output(0), vco.input(0))      # CHORD -> V/Oct

    # VCO -> VCA -> Audio
    pb.chain(vco.o.Sine, vca.input(2))               # Sine -> VCA Ch1 In
    pb.connect(adsr.o.Envelope, vca.input(1))         # ADSR ENV -> VCA Ch1 CV
    pb.connect(vca.output(0), audio.input(0))         # VCA -> Left
    pb.connect(vca.output(0), audio.input(1))         # VCA -> Right

    # Prove and save
    print(f"Proven: {pb.proven}")
    print(f"Status: {pb.status}")
    if pb.proven:
        pb.save(OUTPUT)
        print(f"Saved: {OUTPUT}")
    else:
        # Fall back to unproven save for debugging
        pb.build().save(OUTPUT)
        print(f"Saved (unproven): {OUTPUT}")

    return OUTPUT


if __name__ == "__main__":
    build()
