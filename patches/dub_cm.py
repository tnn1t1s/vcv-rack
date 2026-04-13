"""
Basic Channel dub -- Cm with distance.

Slow, hypnotic chord movement through Cm -> Ab -> Eb -> Gm.
All four chords cluster on the Tonnetz (triangles 20, 16, 17, 21),
so voice leading is maximally smooth. Deep filter sweep, massive reverb.

Tonnetz triangles (ROOT=0):
  Cm  = 20  U(2,0)  {C, Eb, G}
  Ab  = 16  D(2,0)  {Ab, C, Eb}   -- adjacent to Cm
  Eb  = 17  D(2,1)  {Eb, G, Bb}   -- adjacent to Cm and Gm
  Gm  = 21  U(2,1)  {G, Bb, D}    -- adjacent to Eb

Signal flow:
  Clock (75 BPM) --> ClockDiv
  ClockDiv /8     --> SEQ3 ext clock (chord change every 2 bars)
  ClockDiv /1     --> ADSR gate (per-beat envelope)
  SEQ3 CV1        --> Tonnetz CV A
  SEQ3 Trigger    --> Tonnetz TRIG
  Tonnetz CHORD   --> Split --> 3x Crinkle --> BusCrush
  ADSR ENV        --> VCA (amplitude)
  BusCrush OUT    --> VCA --> Ladder (deep filter)
  Slow LFO        --> Ladder CUTOFF_MOD (filter sweep)
  Ladder OUT      --> Saphire (hall reverb, very wet)
  Saphire OUT     --> Audio
"""

import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vcvpatch.builder import PatchBuilder

OUTPUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests", "dub_cm.vcv"
)

FUN = "Fundamental"
AR  = "AgentRack"


def tri_voltage(index):
    """CV voltage (0-10V) that maps to triangle index via floor(v * 32 / 10)."""
    return (index + 0.5) * 10.0 / 32.0


# Cm -> Ab -> Eb -> Gm
CHORDS = [20, 16, 17, 21]


def build() -> str:
    pb = PatchBuilder()

    # ---- Clock: 75 BPM -------------------------------------------------------
    clock = pb.module("SlimeChild-Substation", "SlimeChild-Substation-Clock",
                      TEMPO=math.log2(75 / 60), RUN=1)

    # ---- ClockDiv: /8 for chord changes (every 2 bars) -----------------------
    cdiv = pb.module(AR, "ClockDiv")
    pb.connect(clock.o.Base_clock, cdiv.i.Clock)

    # ---- SEQ3: 4 steps cycling Cm -> Ab -> Eb -> Gm -------------------------
    seq = pb.module(FUN, "SEQ3", **{
        "1": 1,                         # Run = on
        "3": 4,                         # Steps = 4
        "4": tri_voltage(CHORDS[0]),    # Cm
        "5": tri_voltage(CHORDS[1]),    # Ab
        "6": tri_voltage(CHORDS[2]),    # Eb
        "7": tri_voltage(CHORDS[3]),    # Gm
    })
    # External clock from /8 divider
    pb.connect(cdiv.out_id(2), seq.i.Clock)     # /8 -> SEQ3 clock

    # ---- Tonnetz: ROOT=0, no spread/focus ------------------------------------
    tonnetz = pb.module(AR, "Tonnetz",
                        **{"0": 0.0,    # ROOT = C
                           "1": 1.0,    # SPREAD atten
                           "2": 1.0})   # FOCUS atten

    pb.connect(seq.out_id(1), tonnetz.in_id(0))    # SEQ3 CV1 -> Tonnetz CV A
    pb.connect(seq.out_id(0), tonnetz.in_id(3))    # SEQ3 Trigger -> Tonnetz TRIG

    # ---- Split poly into 3 mono channels ------------------------------------
    split = pb.module(FUN, "Split")
    pb.connect(tonnetz.out_id(0), split.in_id(0))

    # ---- 3 Crinkle voices: warm wavefolder tones ----------------------------
    voice1 = pb.module(AR, "Crinkle", TUNE=0.0, TIMBRE=0.05, SYMMETRY=0.0)
    voice2 = pb.module(AR, "Crinkle", TUNE=0.0, TIMBRE=0.08, SYMMETRY=0.03)
    voice3 = pb.module(AR, "Crinkle", TUNE=0.0, TIMBRE=0.06, SYMMETRY=0.02)

    pb.connect(split.out_id(0), voice1.i.V_Oct)
    pb.connect(split.out_id(1), voice2.i.V_Oct)
    pb.connect(split.out_id(2), voice3.i.V_Oct)

    # ---- BusCrush: mix the three voices -------------------------------------
    bus = pb.module(AR, "BusCrush")
    pb.connect(voice1.o.OUT, bus.in_id(0))
    pb.connect(voice2.o.OUT, bus.in_id(1))
    pb.connect(voice3.o.OUT, bus.in_id(2))

    # ---- ADSR: long attack, long release for dub pads ----------------------
    adsr = pb.module(AR, "ADSR",
                     ATTACK=0.15, DECAY=0.4, SUSTAIN=0.6, RELEASE=0.8)
    pb.connect(clock.o.Base_clock, adsr.i.GATE)

    # ---- VCA: shape amplitude with envelope ---------------------------------
    vca = pb.module(FUN, "VCA")
    pb.connect(bus.out_id(0), vca.i.Channel_1)
    pb.connect(adsr.o.Envelope, vca.i.Channel_1_linear_CV)

    # ---- Slow LFO for filter sweep (~0.03 Hz, one full cycle ~30 sec) -------
    lfo = pb.module(FUN, "LFO", Frequency=-3.0, Offset=1)

    # ---- Ladder: deep lowpass, resonance for that dub warmth ----------------
    filt = pb.module(AR, "Ladder",
                     Cutoff=8.5, Resonance=0.35, Spread=0.15, Shape=0.0)
    pb.connect(vca.o.Channel_1, filt.i.Audio)
    pb.connect(lfo.o.Triangle, filt.i.CUTOFF_MOD)
    pb.connect(adsr.o.Envelope, filt.i.CUTOFF_MOD)

    # ---- Saphire: massive hall reverb, very wet -----------------------------
    saphire = pb.module(AR, "Saphire",
                        Mix=0.65, Time=0.92, Bend=0.0, Tone=0.25)
    pb.connect(filt.o.OUT, saphire.i.In_L)
    pb.connect(filt.o.OUT, saphire.i.In_R)

    # ---- Audio output -------------------------------------------------------
    audio = pb.module("Core", "AudioInterface2")
    pb.connect(saphire.o.Out_L, audio.i.Left_input)
    pb.connect(saphire.o.Out_R, audio.i.Right_input)

    pb.build().save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    path = build()
    print(f"Saved: {path}")
