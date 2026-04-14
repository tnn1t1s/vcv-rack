"""
8-step sequencer triggering a Cm chord through tape delay.

Signal flow:
  Clocked-Clkd  -->  SEQ3 (clock)
  SEQ3.CV1      -->  ChordCV (root: C minor)
  ChordCV       -->  VCO1/2/3 (chord voices: C, Eb, G)
  VCO1/2/3.SAW  -->  Mix4
  Mix4.OUT_L    -->  VCA (shaped by ADSR)
  ADSR          <--  SEQ3.GATE
  VCA.OUT       -->  Chronoblob2 (tape delay)
  Chronoblob2   -->  AudioInterface2

Run:
    uv run python -m tests.cm_chord_seq
"""

import os

from vcvpatch import PatchBuilder

OUT_PATH = os.path.join(os.path.dirname(__file__), "cm_chord_seq.vcv")

pb = PatchBuilder(zoom=1.0)

clock = pb.module("ImpromptuModular", "Clocked-Clkd", RUN=1, BPM=120)
seq   = pb.module("Fundamental",      "SEQ3")
chord = pb.module("AaronStatic",      "ChordCV",       CHORD_TYPE=-3)  # minor
vco1  = pb.module("Fundamental",      "VCO")
vco2  = pb.module("Fundamental",      "VCO")
vco3  = pb.module("Fundamental",      "VCO")
mix   = pb.module("Bogaudio",         "Bogaudio-Mix4")
adsr  = pb.module("Fundamental",      "ADSR",  ATTACK=0.01, DECAY=0.2, SUSTAIN=0.6, RELEASE=0.3)
vca   = pb.module("Fundamental",      "VCA",   LEVEL1=1.0)
delay = pb.module("AlrightDevices",   "Chronoblob2",   TIME=0.4, FEEDBACK=0.35, MIX=0.5)
audio = pb.module("Core",             "AudioInterface2")

# Clock and sequencer (cable types auto-detected)
pb.connect(clock.CLK0,  seq.i.CLOCK)
pb.connect(seq.TRIG,    adsr.i.GATE)

# Sequencer CV -> chord generator root
pb.connect(seq.CV1,     chord.i.ROOT)

# Chord voices -> VCO pitches
pb.connect(chord.o.NOTE1, vco1.i.PITCH)
pb.connect(chord.o.NOTE2, vco2.i.PITCH)
pb.connect(chord.o.NOTE3, vco3.i.PITCH)

# Envelope -> VCA CV
pb.connect(adsr.ENV, vca.i.CV)

# Audio chain: 3 VCOs -> mixer -> VCA -> tape delay -> output
pb.chain(vco2.SAW, mix.i.IN2)
pb.chain(vco3.SAW, mix.i.IN3)

(pb.chain(vco1.SAW, mix.i.IN1)
     .to(vca.i.IN)           # mix.OUT_L -> vca.IN
     .to(delay.i.IN_L)       # vca.OUT   -> delay.IN_L
     .fan_out(audio.i.IN_L, audio.i.IN_R))

print(pb.describe())
print()

patch = pb.build()
patch.save(OUT_PATH)

print("Done.")
print(f'\n  open -a "VCV Rack 2 Free" "{OUT_PATH}"')
