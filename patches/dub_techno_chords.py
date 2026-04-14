"""
Dub techno chord patch -- Basic Channel / Maurizio style.

Signal path:
  ChordCV (Cm7, poly 4 voices)
    -> VCO1 (SQR, unison) + VCO2 (SQR, -12st octave below)
    -> VCMixer
    -> Fundamental VCF (LPF, poly, low cutoff)
    -> Fundamental VCA (poly)
    -> Fundamental Sum (poly -> mono)
    -> Bogaudio VCF (bandpass, slow sweep)
    -> Valley Plateau (heavy reverb)
    -> Chronoblob2 (ping-pong delay, tempo-adjacent)
    -> AudioInterface2

Clock:
  Clocked-Clkd at 120 BPM
    -> ADSR1 gate (filter env)
    -> ADSR2 gate (vca env)

Modulation:
  ADSR1 (filter env, quick snappy)  -> VCF cutoff CV
  ADSR2 (vca env, sustained)        -> VCA linear CV
  LFO1 (SIN, very slow ~0.05 Hz)   -> Bogaudio VCF cutoff sweep
  LFO2 (SIN, slow ~0.07 Hz)        -> Chronoblob2 L + R delay CV (opposite)
  Random (smooth, very slow)        -> VCO1+2 FM and PWM (subtle detuning texture)

Key dub techno settings:
  - Low filter cutoff: env opens then closes for that underwater chord swell
  - Long reverb decay: chords blur into each other
  - Delay feedback ~0.6: echoes sustain without washing out
  - Clock triggers at quarter notes: chords hit on every beat
"""

from vcvpatch.builder import PatchBuilder

pb = PatchBuilder()

# ── Clock ─────────────────────────────────────────────────────────────────────
# Run param = 1.0 so it starts immediately
clock = pb.module("ImpromptuModular", "Clocked-Clkd",
                  **{"Master clock": 120.0, "Run": 1.0})

# ── Chord source ───────────────────────────────────────────────────────────────
# Cm7: Root=0 (C), Type=-1 (minor 7th), Voicing=1 (slight open voicing)
# Outputs polyphonic 4-voice Cm7 chord CV (1V/oct).
chord = pb.module("AaronStatic", "ChordCV",
                  **{"Root Note": 0.0, "Chord Type": -1.0,
                     "Inversion": 0.0, "Voicing": 1.0})

# ── Oscillators ───────────────────────────────────────────────────────────────
# VCO1: unison with chord, square wave
# VCO2: one octave below (-12 st), square wave
# FM/PWM attenuverters opened slightly for Random modulation texture
vco1 = pb.module("Fundamental", "VCO", Frequency=0.0,   Pulse_width=0.5,
                 Frequency_modulation=0.1, Pulse_width_modulation=0.08)
vco2 = pb.module("Fundamental", "VCO", Frequency=-12.0, Pulse_width=0.5,
                 Frequency_modulation=0.1, Pulse_width_modulation=0.08)

# ── Mixer ─────────────────────────────────────────────────────────────────────
mix = pb.module("Fundamental", "VCMixer")

# ── Filter + VCA (polyphonic) ─────────────────────────────────────────────────
# Low cutoff for submerged dub feel; env opens it on each hit
vcf  = pb.module("Fundamental", "VCF",
                 Cutoff_frequency=0.30, Resonance=0.35,
                 Cutoff_frequency_CV=0.55)
vca  = pb.module("Fundamental", "VCA")

# ── Poly -> mono ──────────────────────────────────────────────────────────────
summer = pb.module("Fundamental", "Sum")

# ── Envelopes ─────────────────────────────────────────────────────────────────
# Filter envelope: quick attack, medium decay, no sustain -- classic dub chord swell
env_filter = pb.module("Fundamental", "ADSR",
                        Attack=0.008, Decay=0.5, Sustain=0.0, Release=0.6)
# VCA envelope: slightly slower, sustain holds the chord body
env_vca    = pb.module("Fundamental", "ADSR",
                        Attack=0.015, Decay=0.4, Sustain=0.6, Release=0.8)

# ── Bandpass (post-mono, tonal movement) ──────────────────────────────────────
bp = pb.module("Bogaudio", "Bogaudio-VCF",
               **{"Center/cutoff frequency": 0.45,
                  "Resonance / bandwidth":   0.5,
                  "Mode": 2.0})

# ── Reverb ────────────────────────────────────────────────────────────────────
# Heavy, long reverb -- the signature dub techno wash
reverb = pb.module("Valley", "Plateau",
                   **{"Wet level": 0.65, "Decay": 0.82,
                      "Input low cut": 0.25, "Size": 0.75})

# ── Delay (ping-pong) ─────────────────────────────────────────────────────────
# 0.375s = dotted 8th at 120 BPM, high feedback for dub repeats
delay = pb.module("AlrightDevices", "Chronoblob2",
                  **{"Delay Time": 0.375, "Feedback": 0.58,
                     "Dry/Wet": 0.40, "Delay Mode": 1.0,
                     "Time Modulation Mode": 0.0})

# ── Modulation ────────────────────────────────────────────────────────────────
# Very slow LFOs -- dub techno movement is glacial
lfo1 = pb.module("Fundamental", "LFO", Frequency=-2.5)   # ~0.05 Hz, bandpass sweep
lfo2 = pb.module("Fundamental", "LFO", Frequency=-2.0)   # ~0.08 Hz, delay wobble
rnd  = pb.module("Fundamental", "Random",
                 **{"Internal trigger rate": -1.5})       # slow smooth random

# ── Output ────────────────────────────────────────────────────────────────────
audio = pb.module("Core", "AudioInterface2")

# ═══════════════════════════════════════════════════════════════════════════════
# AUDIO SIGNAL FLOW
# ═══════════════════════════════════════════════════════════════════════════════

# ChordCV polyphonic -> both VCO pitch inputs (4-voice poly per VCO)
pb.connect(chord.o.Polyphonic, vco1.i._1V_octave_pitch)
pb.connect(chord.o.Polyphonic, vco2.i._1V_octave_pitch)

# VCOs -> mixer
pb.connect(vco1.o.Square, mix.i.Channel_1)
pb.connect(vco2.o.Square, mix.i.Channel_2)

# Mixer -> VCF -> VCA -> Sum
pb.connect(mix.o.Mix,            vcf.i.Audio)
pb.connect(vcf.o.Lowpass_filter, vca.i.Channel_1)
pb.connect(vca.o.Channel_1,      summer.i.Polyphonic)

# Sum -> bandpass -> reverb -> delay -> output
pb.connect(summer.o.Monophonic, bp.i.Signal)
pb.connect(bp.o.Signal,         reverb.i.Left)
pb.connect(reverb.o.Left,       delay.i.Left)
pb.connect(reverb.o.Right,      delay.i.Right_Return)
pb.connect(delay.o.Left,        audio.i.Left_input)
pb.connect(delay.o.Right_Send,  audio.i.Right_input)

# ═══════════════════════════════════════════════════════════════════════════════
# GATE + CV MODULATION
# ═══════════════════════════════════════════════════════════════════════════════

# Clock -> both envelopes
pb.connect(clock.o.Clock_1, env_filter.i.Gate)
pb.connect(clock.o.Clock_1, env_vca.i.Gate)

# Filter envelope -> VCF cutoff
pb.connect(env_filter.o.Envelope, vcf.i.Frequency)

# VCA envelope -> VCA linear CV
pb.connect(env_vca.o.Envelope, vca.i.Channel_1_linear_CV)

# LFO1 (sine) -> bandpass cutoff sweep
pb.connect(lfo1.o.Sine, bp.i.Cutoff_CV)

# LFO2 -> delay time CV (sine L, triangle R for slow ping-pong wander)
pb.connect(lfo2.o.Sine,     delay.i.L_Delay_Time_CV)
pb.connect(lfo2.o.Triangle, delay.i.R_Delay_Time_CV)

# Random smooth -> VCO FM and PWM (subtle analog-style drift)
pb.connect(rnd.o.Smooth, vco1.i.Frequency_modulation)
pb.connect(rnd.o.Smooth, vco2.i.Frequency_modulation)
pb.connect(rnd.o.Smooth, vco1.i.Pulse_width_modulation)
pb.connect(rnd.o.Smooth, vco2.i.Pulse_width_modulation)

# ═══════════════════════════════════════════════════════════════════════════════

print(pb.status)
for w in pb.warnings:
    print("WARN:", w)

out = "/Users/palaitis/Development/vcv-rack/patches/dub_techno_chords.vcv"
pb.save(out)
print(f"\nSaved: {out}")
print("\nTips:")
print("  - Clocked-Clkd: press RUN button to start")
print("  - Raise VCF cutoff and/or filter env amount if too dark")
print("  - Tweak ChordCV Chord Type: -3=minor, -1=min7, 0=maj7 for different colours")
print("  - Plateau decay can go to 0.9+ for more wash")
