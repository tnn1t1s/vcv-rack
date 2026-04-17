"""
SlimeChild Substation demo -- uses all 8 Substation modules.

Signal flow:
  Clock MULT (x4=16th notes) -> PolySeq CLOCK
  PolySeq SEQ_A               -> Quantizer IN  (raw CV -> scale)
  Quantizer OUT               -> SubOsc V/OCT  (quantized pitch)
  PolySeq TRIG1               -> Envelopes TRIG1 + TRIG2

  SubOsc BASE + SUB1 + SUB2   -> Mixer IN1/2/3  (blend root + 2 sub octaves)
  Mixer OUT                   -> Filter IN
  Envelopes ENV2              -> Filter FM      (filter sweep, attenuation=0.5)
  Filter OUT                  -> VCA IN
  Envelopes ENV1              -> VCA CV         (amplitude)
  VCA OUT                     -> AudioInterface2 IN_L + IN_R

Modules used:
  SlimeChild-Substation-Clock          master clock
  SlimeChild-Substation-PolySeq        polyrhythm CV sequencer
  SlimeChild-Substation-Quantizer      scale quantizer
  SlimeChild-Substation-SubOscillator  sub-harmonic oscillator
  SlimeChild-Substation-Envelopes      dual AD envelopes
  SlimeChild-Substation-Mixer          3-ch saturating mixer
  SlimeChild-Substation-Filter         LP4 ladder filter
  SlimeChild-Substation-VCA            VCA
  Core/AudioInterface2                 output
"""

import math
import os
import sys

from vcvpatch.builder import PatchBuilder

OUTPUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests", "slimechild_demo.vcv"
)

PLUGIN = "SlimeChild-Substation"


def build() -> str:
    pb = PatchBuilder()

    # ---- Clock (127 BPM, MULT=4 for 16th notes) --------------------------------
    clock = pb.module(PLUGIN, "SlimeChild-Substation-Clock",
                      TEMPO=math.log2(127 / 60), RUN=1, MULT=4)

    # ---- PolySeq: 4-step sequence A, routed via divider 1 ----------------------
    # DIV1=1 (every clock), DIV1_A=1 (route to A), A1-A4 = pitch offsets
    polyseq = pb.module(PLUGIN, "SlimeChild-Substation-PolySeq",
                        STEPS=4,
                        A1=0.0, A2=0.25, A3=-0.17, A4=0.42,
                        DIV1=1, DIV1_A=1)

    # ---- Quantizer: C minor pentatonic ----------------------------------------
    quant = pb.module(PLUGIN, "SlimeChild-Substation-Quantizer",
                      ROOT=0, OCTAVE=-1)

    # ---- SubOscillator: root + one + two octaves below -------------------------
    subosc = pb.module(PLUGIN, "SlimeChild-Substation-SubOscillator",
                       BASE_FREQ=0, WAVEFORM=2,
                       SUBDIV1=2,    # SUB1 = 1 octave below
                       SUBDIV2=4,    # SUB2 = 2 octaves below
                       PWM=0.5, DETUNE=0.02)

    # ---- Envelopes: EG1=amp (fast), EG2=filter (slower) ----------------------
    envs = pb.module(PLUGIN, "SlimeChild-Substation-Envelopes",
                     EG1_ATTACK=-3, EG1_DECAY=-1,
                     EG2_ATTACK=-3, EG2_DECAY=0,
                     HOLD=0)

    # ---- Mixer: blend BASE + SUB1 + SUB2 --------------------------------------
    mixer = pb.module(PLUGIN, "SlimeChild-Substation-Mixer",
                      LEVEL1=0.7, LEVEL2=0.5, LEVEL3=0.3,
                      MIX_LEVEL=1.0, DRIVE=0.2)

    # ---- Filter: mid cutoff, FM attenuation opened for envelope sweep ---------
    filt = pb.module(PLUGIN, "SlimeChild-Substation-Filter",
                     FREQ=3.0, RES=0.25, FM=0.5)

    # ---- VCA ------------------------------------------------------------------
    vca = pb.module(PLUGIN, "SlimeChild-Substation-VCA")

    # ---- Audio output ---------------------------------------------------------
    audio = pb.module("Core", "AudioInterface2")

    # =========================================================================
    # WIRING
    # =========================================================================

    # Clock -> PolySeq at 16th note rate
    pb.chain(clock.o.MULT,    polyseq.i.CLOCK)

    # PolySeq -> pitch chain
    pb.chain(polyseq.o.SEQ_A, quant.i.IN)
    pb.chain(quant.o.OUT,     subosc.i.VOCT)

    # PolySeq triggers -> both envelopes
    pb.chain(polyseq.o.TRIG1, envs.i.TRIG1)
    pb.chain(polyseq.o.TRIG1, envs.i.TRIG2)

    # SubOsc layers -> mixer
    pb.chain(subosc.o.BASE, mixer.i.IN1)
    pb.chain(subosc.o.SUB1, mixer.i.IN2)
    pb.chain(subosc.o.SUB2, mixer.i.IN3)

    # Mixer -> filter (FM opened via FM param above)
    pb.chain(mixer.o.OUT, filt.i.IN)
    pb.chain(envs.o.ENV2, filt.i.FM)    # filter sweep (FM param=0.5 opens it)

    # Filter -> VCA -> output
    pb.chain(filt.o.OUT,  vca.i.IN)
    pb.chain(envs.o.ENV1, vca.i.CV)     # amplitude envelope
    pb.chain(vca.o.OUT,   audio.i.IN_L)
    pb.chain(vca.o.OUT,   audio.i.IN_R)

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
