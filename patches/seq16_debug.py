"""
Seq16 debug: SlimeChild Clock -> Sequencer16 -> VCO + Envelope -> Audio
4 obvious pitches to verify CV port. Envelope on TRIG to verify gate port.
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vcvpatch.builder import PatchBuilder

OUTPUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "tests", "seq16_debug.vcv")

PLUGIN = "SlimeChild-Substation"

pb = PatchBuilder()

clock = pb.module(PLUGIN, "SlimeChild-Substation-Clock",
                  TEMPO=math.log2(120 / 60), RUN=1, MULT=4)

seq = pb.module("CountModula", "Sequencer16",
    STEP1=0.0,   # C4
    STEP2=0.25,  # D4ish
    STEP3=0.5,   # E4ish
    STEP4=0.75,  # F#4ish
    TRIG1=1.0, TRIG2=1.0, TRIG3=1.0, TRIG4=1.0,
    LENGTH=4.0,
)

envs = pb.module(PLUGIN, "SlimeChild-Substation-Envelopes",
                 EG1_ATTACK=-5, EG1_DECAY=-2, HOLD=0)

vco  = pb.module("Fundamental", "VCO")
vca  = pb.module(PLUGIN, "SlimeChild-Substation-VCA", LEVEL=0)
audio = pb.module("Core", "AudioInterface2")

pb.chain(clock.o.MULT,  seq.i.CLOCK)
pb.chain(seq.o.CV,      vco.i.V_OCT)
pb.chain(seq.o.TRIG,    envs.i.TRIG1)
pb.chain(vco.o.SIN,     vca.i.IN)
pb.chain(envs.o.ENV1,   vca.i.CV)
pb.chain(vca.o.OUT,     audio.i.IN_L)
pb.chain(vca.o.OUT,     audio.i.IN_R)

print(pb.status)
if not pb.proven:
    print(pb.report())
    sys.exit(1)

os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
pb.build().save(OUTPUT)
print(f"Saved: {OUTPUT}")
