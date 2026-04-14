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
    python3 tests/cm_chord_seq.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vcvpatch import PatchBuilder, COLORS

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

# Clock and sequencer
pb.connect(clock.CLK0,  seq.i.CLOCK,  color=COLORS["white"])
pb.connect(seq.TRIG,    adsr.i.GATE,  color=COLORS["white"], role="gate")

# Sequencer CV -> chord generator root
pb.connect(seq.CV1,     chord.i.ROOT, color=COLORS["cyan"])

# Chord voices -> VCO pitches
pb.connect(chord.o.NOTE1, vco1.i.PITCH, color=COLORS["cyan"])
pb.connect(chord.o.NOTE2, vco2.i.PITCH, color=COLORS["cyan"])
pb.connect(chord.o.NOTE3, vco3.i.PITCH, color=COLORS["cyan"])

# Envelope -> VCA CV
pb.connect(adsr.ENV, vca.i.CV, color=COLORS["orange"], role="cv")

# Audio chain: 3 VCOs -> mixer -> VCA -> tape delay -> output
pb.chain(vco2.SAW, mix.i.IN2)
pb.chain(vco3.SAW, mix.i.IN3)

(pb.chain(vco1.SAW, mix.i.IN1)
     .to(vca.i.IN,     color=COLORS["yellow"])   # mix.OUT_L -> vca.IN
     .to(delay.i.IN_L, color=COLORS["yellow"])   # vca.OUT   -> delay.IN_L
     .fan_out(audio.i.IN_L, audio.i.IN_R, color=COLORS["green"]))

print(pb.describe())
print()

compiled = pb.compile()
compiled.save(OUT_PATH)

print("Done.")
print(f'\n  open -a "VCV Rack 2 Free" "{OUT_PATH}"')
