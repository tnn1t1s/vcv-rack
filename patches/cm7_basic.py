"""
Stripped down: Cm7 chord through oscillators and filter. Nothing else.

Clock -> ADSR -> VCA + Ladder cutoff
ChordCV (Cm7) -> VCO1 + VCO2 -> VCMixer -> VCA -> Sum -> Ladder -> Audio
"""

import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder

pb = PatchBuilder()

clock  = pb.module("ImpromptuModular", "Clocked-Clkd",
                   **{"Master clock": 120.0, "Run": 1.0})

chord  = pb.module("AaronStatic", "ChordCV",
                   **{"Root Note": 0.0, "Chord Type": -1.0,
                      "Inversion": 0.0, "Voicing": 1.0})

vco1   = pb.module("Fundamental", "VCO", Frequency=0.0,   Pulse_width=0.5)
vco2   = pb.module("Fundamental", "VCO", Frequency=-12.0, Pulse_width=0.5)

mix    = pb.module("Fundamental", "VCMixer")
vca    = pb.module("Fundamental", "VCA")
summer = pb.module("Fundamental", "Sum")

env    = pb.module("Fundamental", "ADSR",
                   Attack=0.01, Decay=0.4, Sustain=0.5, Release=0.5)

ladder = pb.module("AgentRack", "Ladder", Cutoff=0.3, Resonance=0.4)

audio  = pb.module("Core", "AudioInterface2")

# Chord -> oscillators
pb.connect(chord.o.Polyphonic, vco1.i._1V_octave_pitch)
pb.connect(chord.o.Polyphonic, vco2.i._1V_octave_pitch)

# Oscillators -> mix -> vca -> sum -> filter -> out
pb.connect(vco1.o.Square,       mix.i.Channel_1)
pb.connect(vco2.o.Square,       mix.i.Channel_2)
pb.connect(mix.o.Mix,           vca.i.Channel_1)
pb.connect(vca.o.Channel_1,     summer.i.Polyphonic)
pb.connect(summer.o.Monophonic, ladder.i.Audio)
pb.connect(ladder.o.Out,        audio.i.Left_input)
pb.connect(ladder.o.Out,        audio.i.Right_input)

# Clock -> envelope -> VCA + filter cutoff
pb.connect(clock.o.Clock_1,       env.i.Gate)
pb.connect(env.o.Envelope,        vca.i.Channel_1_linear_CV)
pb.connect(env.o.Envelope,        ladder.i.Cutoff_mod)

print(pb.status)
for w in pb.warnings:
    print("WARN:", w)

out = "/Users/palaitis/Development/vcv-rack/patches/cm7_basic.vcv"
pb.save(out)
print(f"Saved: {out}")
