"""
16-step gate sequence triggering a static Cm7 chord. No filter, no reverb.

SEQ3 row 1 + row 2 gates -> ADSR -> VCA
ChordCV (Cm7) -> VCO1 + VCO2 -> VCMixer -> VCA -> Sum -> Audio
"""

from vcvpatch.builder import PatchBuilder

pb = PatchBuilder()

clock = pb.module("ImpromptuModular", "Clocked-Clkd",
                  **{"Master clock": 120.0, "Run": 1.0})

# GateSequencer16: 16 steps fully param-based
# Pattern: on off on on off on off on | on on off on on off on on
seq = pb.module("CountModula", "GateSequencer16", **{
    "Track 1 step 1":  1, "Track 1 step 2":  0, "Track 1 step 3":  1, "Track 1 step 4":  1,
    "Track 1 step 5":  0, "Track 1 step 6":  1, "Track 1 step 7":  0, "Track 1 step 8":  1,
    "Track 1 step 9":  1, "Track 1 step 10": 1, "Track 1 step 11": 0, "Track 1 step 12": 1,
    "Track 1 step 13": 1, "Track 1 step 14": 0, "Track 1 step 15": 1, "Track 1 step 16": 1,
})

chord  = pb.module("AaronStatic", "ChordCV",
                   **{"Root Note": 0.0, "Chord Type": -1.0,
                      "Inversion": 0.0, "Voicing": 1.0})

vco1   = pb.module("Fundamental", "VCO", Frequency=0.0,   Pulse_width=0.5)
vco2   = pb.module("Fundamental", "VCO", Frequency=-12.0, Pulse_width=0.5)

mix    = pb.module("Fundamental", "VCMixer")
vca    = pb.module("Fundamental", "VCA")
summer = pb.module("Fundamental", "Sum")

env    = pb.module("Fundamental", "ADSR",
                   Attack=0.01, Decay=0.3, Sustain=0.5, Release=0.4)

audio  = pb.module("Core", "AudioInterface2")

pb.connect(clock.o.Master_clock, seq.i.Clock)
pb.connect(clock.o.Reset,        seq.i.Reset)
pb.connect(seq.o.Track_1_gate,   env.i.Gate)

# Chord -> oscillators -> mix -> vca -> sum -> audio
pb.connect(chord.o.Polyphonic, vco1.i._1V_octave_pitch)
pb.connect(chord.o.Polyphonic, vco2.i._1V_octave_pitch)
pb.connect(vco1.o.Square,       mix.i.Channel_1)
pb.connect(vco2.o.Square,       mix.i.Channel_2)
pb.connect(mix.o.Mix,           vca.i.Channel_1)
pb.connect(vca.o.Channel_1,     summer.i.Polyphonic)
pb.connect(summer.o.Monophonic, audio.i.Left_input)
pb.connect(summer.o.Monophonic, audio.i.Right_input)

pb.connect(env.o.Envelope, vca.i.Channel_1_linear_CV)

print(pb.status)
for w in pb.warnings:
    print("WARN:", w)

out = "/Users/palaitis/Development/vcv-rack/patches/cm7_seq.vcv"
pb.save(out)
print(f"Saved: {out}")
