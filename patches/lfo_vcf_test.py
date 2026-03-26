"""
LFO → AgentRack/Attenuate → VCF reference patch.

Demonstrates AgentRack/Attenuate as a real VCV Rack module.

Signal flow:
  LFO1 (2Hz, SIN) → Attenuate.IN → Attenuate.OUT → VCF.FREQ
  LFO2 (0.07Hz, unipolar) is unused here -- Attenuate.SCALE knob is static at 0.5.
  VCO.SAW → VCF.IN → Audio L+R

To vary attenuation: turn the SCALE knob in Rack (0=silence, 1=full sweep).
"""

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vcvpatch.builder import PatchBuilder

OUTPUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests", "lfo_vcf_test.vcv"
)


def build():
    pb = PatchBuilder()

    vco = pb.module("Fundamental", "VCO", FREQ=0.0, PW=0.5)

    # FREQ_CV (param 3) must be non-zero or VCF ignores its FREQ input
    vcf = pb.module("Fundamental", "VCF", FREQ=0.5, RES=0.8, FREQ_CV=0.6)

    # LFO1: 2Hz sweep signal
    lfo1 = pb.module("Fundamental", "LFO", FREQ=2.0)

    # AgentRack Attenuate: SCALE=0.5 (50% of LFO reaches VCF cutoff)
    att = pb.module("AgentRack", "Attenuate", SCALE=0.5)

    audio = pb.module("Core", "AudioInterface2")

    pb.chain(vco.o.SAW,   vcf.i.IN)       # audio: VCO → VCF
    pb.chain(lfo1.o.SIN,  att.i.IN)       # LFO sweep → Attenuate input
    pb.chain(att.o.OUT,   vcf.i.FREQ)     # attenuated sweep → VCF cutoff
    pb.chain(vcf.o.LPF,   audio.i.IN_L)
    pb.chain(vcf.o.LPF,   audio.i.IN_R)

    print(pb.status)
    print(pb.report())

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    pb.compile().save(OUTPUT)
    print(f"Saved: {OUTPUT}")


if __name__ == "__main__":
    build()
