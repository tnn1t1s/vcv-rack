"""
Tutorial patch: 16-step sequencer -> ADSR -> wavetable synth -> output

Signal flow:
  Substation Clock MULT (x4 = 16th notes) -> NoteSeq16 CLOCK
  NoteSeq16 VOCT -> Plaits VOCT   (pitch)
  NoteSeq16 GATE -> ADSR GATE     (amplitude envelope)
  NoteSeq16 GATE -> Plaits GATE   (Plaits internal LPG trigger)
  Plaits OUT     -> VCA IN1       (audio through VCA)
  ADSR ENV       -> VCA CV        (required: opens VCA)
  VCA OUT1       -> AudioInterface2 IN_L, IN_R

Clock math at 127 BPM:
  TEMPO = log2(127/60) = 1.082
  BASE output = 127 quarter notes/min (1 per beat)
  MULT output with MULT=4 = 508 pulses/min = 16th notes
  16 steps x 16th note = 4 beats = 1 bar per pattern cycle
"""

import math
import os
import sys

from vcvpatch.builder import PatchBuilder

OUTPUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests", "simple_wavetable_16.vcv"
)


def build() -> str:
    pb = PatchBuilder()

    # ---- Clock (127 BPM, MULT at x4 = 16th notes) --------------------------
    # Substation Clock: TEMPO = log2(BPM/60), MULT param = integer multiplier
    clock = pb.module("SlimeChild-Substation", "SlimeChild-Substation-Clock",
                      TEMPO=math.log2(127 / 60), RUN=1, MULT=4)

    # ---- 16-step sequencer --------------------------------------------------
    seq = pb.module("JW-Modules", "NoteSeq16")

    # ---- Wavetable synth (AudibleInstruments Plaits) ------------------------
    synth = pb.module("AudibleInstruments", "Plaits",
                      MODEL=8,          # wavetable model
                      HARMONICS=0.5,
                      TIMBRE=0.6,
                      MORPH=0.4,
                      DECAY=0.3)

    # ---- Amplitude envelope -------------------------------------------------
    adsr = pb.module("Bogaudio", "Bogaudio-ADSR",
                     ATTACK=0.01, DECAY=0.2, SUSTAIN=0.7, RELEASE=0.4)

    # ---- VCA ----------------------------------------------------------------
    vca = pb.module("Fundamental", "VCA")

    # ---- Audio output -------------------------------------------------------
    audio = pb.module("Core", "AudioInterface2")

    # =========================================================================
    # WIRING
    # =========================================================================

    # MULT output fires 4x per beat = 16th notes
    pb.chain(clock.o.MULT, seq.i.CLOCK)

    # Sequencer -> pitch and gates
    pb.chain(seq.o.VOCT,  synth.i.VOCT)   # pitch CV
    pb.chain(seq.o.GATE,  adsr.i.GATE)    # trigger ADSR
    pb.chain(seq.o.GATE,  synth.i.GATE)   # also trigger Plaits LPG

    # Audio chain: Plaits -> VCA -> output
    pb.chain(synth.o.OUT,   vca.i.IN1)
    pb.chain(adsr.o.ENV,    vca.i.CV)      # required: opens VCA
    pb.chain(vca.o.OUT1,    audio.i.IN_L)
    pb.chain(vca.o.OUT1,    audio.i.IN_R)

    # =========================================================================
    # PROOF & SAVE
    # =========================================================================

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
