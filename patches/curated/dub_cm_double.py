"""
Double Tonnetz dub -- two complementary chord paths crossfading.

Two Tonnetz modules play stacked triangle pairs (major/minor at same
lattice position, sharing 2 of 3 pitch classes). A very slow LFO
crossfades between paths so only one sounds at a time.

Stacked pairs (ROOT=C, all at r=-1):
  Step 1: Cm(20) / Ab(19)  -- share C, Eb
  Step 2: Fm(18) / Db(17)  -- share Ab, F
  Step 3: Gm(22) / Eb(21)  -- share Bb, G
  Step 4: Cm(20) / Ab(19)  -- back to start

At any switching moment, only 1 pitch class changes between paths.
This is the smoothest possible harmonic crossfade on the Tonnetz.

Path A (minor):  Cm -> Fm -> Gm -> Cm   [i-iv-v-i]
Path B (major):  Ab -> Db -> Eb -> Ab   [VI-II-III-VI]

Signal flow:
  Clocked (75 BPM) -> ClockDiv
  ClockDiv /8 -> SEQ3 (4 steps, CV1=minor, CV2=major)
  Clocked Clock_0 -> ADSR gate (per-beat envelope)

  SEQ3 CV1 -> Tonnetz_A -> Split_A -> 3x Crinkle -> BusCrush_A -> VCA_sw_A
  SEQ3 CV2 -> Tonnetz_B -> Split_B -> 3x Crinkle -> BusCrush_B -> VCA_sw_B

  LFO_sw_a SQR (unipolar)          -> VCA_sw_A CV  (open when high)
  LFO_sw_b SQR (unipolar, inverted) -> VCA_sw_B CV  (open when low)

  VCA_sw_A + VCA_sw_B -> VCA_amp (ADSR envelope)
  VCA_amp -> Ladder (filter, LFO sweep + envelope)
  Ladder -> Saphire (hall reverb)
  Saphire -> Audio

Usage:
  uv run python -m patches.dub_cm_double
"""

import os
from pathlib import Path

from vcvpatch import CableType, PatchBuilder, RackLayout

OUTPUT = str(Path(__file__).resolve().parents[2] / "tests" / "dub_cm_double.vcv")

FUN = "Fundamental"
AR  = "AgentRack"
IM  = "ImpromptuModular"


def tri_voltage(index):
    """CV voltage (0-10V) that maps to triangle index via floor(v * 32 / 10)."""
    return (index + 0.5) * 10.0 / 32.0


# Stacked pairs: (minor_index, major_index)
#   (q=0,  r=-1): Cm(20) / Ab(19)
#   (q=-1, r=-1): Fm(18) / Db(17)
#   (q=1,  r=-1): Gm(22) / Eb(21)
PATH_A = [20, 18, 22, 20]   # minor: Cm -> Fm -> Gm -> Cm
PATH_B = [19, 17, 21, 19]   # major: Ab -> Db -> Eb -> Ab


def build() -> str:
    pb = PatchBuilder()
    layout = RackLayout()
    control_row = layout.row(0)
    path_a_row = layout.row(1)
    path_b_row = layout.row(2)
    mix_row = layout.row(3)

    # ---- Clock: 75 BPM -------------------------------------------------------
    clock = pb.module(IM, "Clocked-Clkd",
                      pos=control_row.at(0),
                      Master_clock=75, Run=1)

    # ---- ClockDiv: /8 for chord changes (every 2 bars at 75 BPM) -------------
    cdiv = pb.module(AR, "ClockDiv", pos=control_row.at(14))
    pb.connect(clock.o.Clock_0, cdiv.i.Clock)

    # ---- SEQ3: 4 steps, CV1 = minor path, CV2 = major path -------------------
    seq = pb.module(FUN, "SEQ3", pos=control_row.at(28), **{
        "Run": 1,
        "Steps": 4,
        # CV1 row: minor path (Cm -> Fm -> Gm -> Cm)
        "CV_1_step_1": tri_voltage(PATH_A[0]),
        "CV_1_step_2": tri_voltage(PATH_A[1]),
        "CV_1_step_3": tri_voltage(PATH_A[2]),
        "CV_1_step_4": tri_voltage(PATH_A[3]),
        # CV2 row: major path (Ab -> Db -> Eb -> Ab)
        "CV_2_step_1": tri_voltage(PATH_B[0]),
        "CV_2_step_2": tri_voltage(PATH_B[1]),
        "CV_2_step_3": tri_voltage(PATH_B[2]),
        "CV_2_step_4": tri_voltage(PATH_B[3]),
        # All 4 triggers active
        "Step_1_trigger": 1, "Step_2_trigger": 1,
        "Step_3_trigger": 1, "Step_4_trigger": 1,
    })
    pb.connect(cdiv.o._8, seq.i.Clock)

    # ===========================================================================
    # PATH A -- minor triads: Cm -> Fm -> Gm -> Cm
    # ===========================================================================

    tonnetz_a = pb.module(AR, "Tonnetz", pos=path_a_row.at(0))
    pb.connect(seq.o.CV_1, tonnetz_a.i.CV_1_triangle_select)
    pb.connect(seq.o.Trigger, tonnetz_a.i.Trigger)

    split_a = pb.module(FUN, "Split", pos=path_a_row.at(12))
    pb.connect(tonnetz_a.o.Chord_poly_V_Oct, split_a.in_id(0))

    voice_a1 = pb.module(AR, "Crinkle", pos=path_a_row.at(24), Tune=0.0, Timbre=0.05, Symmetry=0.0)
    voice_a2 = pb.module(AR, "Crinkle", pos=path_a_row.at(32), Tune=0.0, Timbre=0.08, Symmetry=0.03)
    voice_a3 = pb.module(AR, "Crinkle", pos=path_a_row.at(40), Tune=0.0, Timbre=0.06, Symmetry=0.02)
    pb.connect(split_a.out_id(0), voice_a1.i.V_Oct, cable_type=CableType.CV)
    pb.connect(split_a.out_id(1), voice_a2.i.V_Oct, cable_type=CableType.CV)
    pb.connect(split_a.out_id(2), voice_a3.i.V_Oct, cable_type=CableType.CV)

    bus_a = pb.module(AR, "BusCrush", pos=path_a_row.at(50))
    pb.connect(voice_a1.o.Out, bus_a.i.Channel_1_in)
    pb.connect(voice_a2.o.Out, bus_a.i.Channel_2_in)
    pb.connect(voice_a3.o.Out, bus_a.i.Channel_3_in)

    # ===========================================================================
    # PATH B -- major triads: Ab -> Db -> Eb -> Ab
    # ===========================================================================

    tonnetz_b = pb.module(AR, "Tonnetz", pos=path_b_row.at(0))
    pb.connect(seq.o.CV_2, tonnetz_b.i.CV_1_triangle_select)
    pb.connect(seq.o.Trigger, tonnetz_b.i.Trigger)

    split_b = pb.module(FUN, "Split", pos=path_b_row.at(12))
    pb.connect(tonnetz_b.o.Chord_poly_V_Oct, split_b.in_id(0))

    voice_b1 = pb.module(AR, "Crinkle", pos=path_b_row.at(24), Tune=0.0, Timbre=0.10, Symmetry=0.05)
    voice_b2 = pb.module(AR, "Crinkle", pos=path_b_row.at(32), Tune=0.0, Timbre=0.12, Symmetry=0.07)
    voice_b3 = pb.module(AR, "Crinkle", pos=path_b_row.at(40), Tune=0.0, Timbre=0.09, Symmetry=0.04)
    pb.connect(split_b.out_id(0), voice_b1.i.V_Oct, cable_type=CableType.CV)
    pb.connect(split_b.out_id(1), voice_b2.i.V_Oct, cable_type=CableType.CV)
    pb.connect(split_b.out_id(2), voice_b3.i.V_Oct, cable_type=CableType.CV)

    bus_b = pb.module(AR, "BusCrush", pos=path_b_row.at(50))
    pb.connect(voice_b1.o.Out, bus_b.i.Channel_1_in)
    pb.connect(voice_b2.o.Out, bus_b.i.Channel_2_in)
    pb.connect(voice_b3.o.Out, bus_b.i.Channel_3_in)

    # ===========================================================================
    # SWITCHING -- complementary LFOs drive two VCAs
    # ===========================================================================

    # Very slow LFO (~0.03 Hz, period ~32 sec). Switches paths every ~16 sec.
    # At 75 BPM with /8 chord clock, that's ~2.5 chord changes per path.
    lfo_sw_a = pb.module(FUN, "LFO", pos=control_row.at(50), Frequency=-5.0, Offset=1)           # unipolar
    lfo_sw_b = pb.module(FUN, "LFO", pos=control_row.at(60), Frequency=-5.0, Offset=1, Invert=1) # complement

    vca_sw_a = pb.module(FUN, "VCA", pos=mix_row.at(0))
    pb.connect(bus_a.o.Stereo_left_out, vca_sw_a.i.IN)
    pb.connect(lfo_sw_a.o.Square, vca_sw_a.i.CV)

    vca_sw_b = pb.module(FUN, "VCA", pos=mix_row.at(10))
    pb.connect(bus_b.o.Stereo_left_out, vca_sw_b.i.IN)
    pb.connect(lfo_sw_b.o.Square, vca_sw_b.i.CV)

    # ===========================================================================
    # SHARED PROCESSING -- envelope, filter, reverb, output
    # ===========================================================================

    # ADSR: long attack/release for dub pads, gated by master clock
    adsr = pb.module(AR, "ADSR", pos=control_row.at(72),
                     Attack=0.15, Decay=0.4, Sustain=0.6, Release=0.8)
    pb.connect(clock.o.Clock_0, adsr.i.Gate)

    # Amplitude VCA: both switching paths sum into one input
    vca_amp = pb.module(FUN, "VCA", pos=mix_row.at(22))
    pb.connect(vca_sw_a.o.OUT, vca_amp.i.IN)
    pb.connect(vca_sw_b.o.OUT, vca_amp.i.IN)   # cable summing
    pb.connect(adsr.o.Envelope, vca_amp.i.CV)

    # Slow filter sweep LFO (~0.13 Hz, one full cycle ~8 sec)
    lfo_filt = pb.module(FUN, "LFO", pos=control_row.at(84), Frequency=-3.0, Offset=1)

    # Ladder filter: deep lowpass with resonance
    filt = pb.module(AR, "Ladder", pos=mix_row.at(34),
                     Cutoff=8.5, Resonance=0.35, Spread=0.15, Shape=0.0)
    pb.connect(vca_amp.o.OUT, filt.i.Audio)
    pb.connect(lfo_filt.o.Triangle, filt.i.Cutoff_mod)
    pb.connect(adsr.o.Envelope, filt.i.Cutoff_mod)

    # Saphire: massive hall reverb
    saphire = pb.module(AR, "Saphire", pos=mix_row.at(46),
                        Mix=0.65, Time=0.92, Bend=0.0, Tone=0.25)
    pb.connect(filt.o.Out, saphire.i.In_L)
    pb.connect(filt.o.Out, saphire.i.In_R)

    # Audio output
    audio = pb.module("Core", "AudioInterface2", pos=mix_row.at(60))
    pb.connect(saphire.o.Out_L, audio.i.Left_input)
    pb.connect(saphire.o.Out_R, audio.i.Right_input)

    # ===========================================================================
    # BUILD
    # ===========================================================================

    pb.build().save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    path = build()
    print(f"Saved: {path}")
