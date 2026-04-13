"""
Dub techno patch -- AgentRack modules where possible.

AgentRack used for: Ladder (LPF), Saphire (reverb), ADSR x2
Third-party still needed for: clock, chord source, VCO (poly), VCA, Sum, bandpass, delay, output

Signal path:
  Clocked-Clkd (120 BPM)
    -> ADSR1 (filter env) + ADSR2 (vca env)

  ChordCV (Cm7 poly)
    -> VCO1 (SQR, unison) + VCO2 (SQR, -12st)
    -> VCMixer
    -> Fundamental VCA (poly, env-controlled)
    -> Fundamental Sum (poly -> mono)
    -> AgentRack Ladder (LPF, ADSR1 sweeps cutoff)
    -> Bogaudio VCF (bandpass, LFO1 sweeps cutoff -- tonal movement)
    -> AgentRack Saphire (reverb)
    -> Chronoblob2 (ping-pong delay)
    -> AudioInterface2

Modulation (matching tutorial):
  ADSR1 -> Ladder cutoff mod
  ADSR2 -> VCA linear CV
  LFO1  -> Bogaudio bandpass cutoff (slow sweep)
  LFO2  -> Chronoblob2 L + R delay time CV
  Random -> VCO1+2 FM and PWM
"""

import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder

pb = PatchBuilder()

# ── Clock ─────────────────────────────────────────────────────────────────────
clock = pb.module("ImpromptuModular", "Clocked-Clkd",
                  **{"Master clock": 120.0, "Run": 1.0})

# ── Chord source ───────────────────────────────────────────────────────────────
chord = pb.module("AaronStatic", "ChordCV",
                  **{"Root Note": 0.0, "Chord Type": -1.0,
                     "Inversion": 0.0, "Voicing": 1.0})

# ── Oscillators ───────────────────────────────────────────────────────────────
vco1 = pb.module("Fundamental", "VCO", Frequency=0.0,   Pulse_width=0.5,
                 Frequency_modulation=0.1, Pulse_width_modulation=0.08)
vco2 = pb.module("Fundamental", "VCO", Frequency=-12.0, Pulse_width=0.5,
                 Frequency_modulation=0.1, Pulse_width_modulation=0.08)

# ── Mixer ─────────────────────────────────────────────────────────────────────
mix = pb.module("Fundamental", "VCMixer")

# ── VCA (poly) ────────────────────────────────────────────────────────────────
vca = pb.module("Fundamental", "VCA")

# ── Poly -> mono ──────────────────────────────────────────────────────────────
summer = pb.module("Fundamental", "Sum")

# ── Envelopes (Fundamental until AgentRack ADSR gets CV inputs -- issue #1) ───
env_filter = pb.module("Fundamental", "ADSR",
                        Attack=0.008, Decay=0.5, Sustain=0.0, Release=0.6)
env_vca    = pb.module("Fundamental", "ADSR",
                        Attack=0.015, Decay=0.4, Sustain=0.6, Release=0.8)

# ── AgentRack Ladder (LPF) ────────────────────────────────────────────────────
# Low cutoff; ADSR sweeps it open on each gate
ladder = pb.module("AgentRack", "Ladder",
                   Cutoff=0.25, Resonance=0.4)

# ── Bogaudio bandpass (tonal movement, LFO-swept) ────────────────────────────
bp = pb.module("Bogaudio", "Bogaudio-VCF",
               **{"Center/cutoff frequency": 0.45,
                  "Resonance / bandwidth":   0.5,
                  "Mode": 2.0})

# ── AgentRack Saphire (reverb) ────────────────────────────────────────────────
# Long decay, high mix -- the signature dub wash
saphire = pb.module("AgentRack", "Saphire",
                    Mix=0.65, Time=0.80, Tone=0.4)

# ── Delay (ping-pong) ─────────────────────────────────────────────────────────
delay = pb.module("AlrightDevices", "Chronoblob2",
                  **{"Delay Time": 0.375, "Feedback": 0.58,
                     "Dry/Wet": 0.40, "Delay Mode": 1.0,
                     "Time Modulation Mode": 0.0})

# ── Modulation ────────────────────────────────────────────────────────────────
lfo1 = pb.module("Fundamental", "LFO", Frequency=-2.5)   # slow, bandpass cutoff sweep
lfo2 = pb.module("Fundamental", "LFO", Frequency=-2.0)   # slow, delay wobble
rnd  = pb.module("Fundamental", "Random",
                 **{"Internal trigger rate": -1.5})

# ── Output ────────────────────────────────────────────────────────────────────
audio = pb.module("Core", "AudioInterface2")

# ═══════════════════════════════════════════════════════════════════════════════
# AUDIO SIGNAL FLOW
# ═══════════════════════════════════════════════════════════════════════════════

pb.connect(chord.o.Polyphonic, vco1.i._1V_octave_pitch)
pb.connect(chord.o.Polyphonic, vco2.i._1V_octave_pitch)

pb.connect(vco1.o.Square, mix.i.Channel_1)
pb.connect(vco2.o.Square, mix.i.Channel_2)

pb.connect(mix.o.Mix,       vca.i.Channel_1)
pb.connect(vca.o.Channel_1, summer.i.Polyphonic)

pb.connect(summer.o.Monophonic, ladder.i.Audio)
pb.connect(ladder.o.Out, bp.i.Signal)
pb.connect(bp.o.Signal,  saphire.i.In_L)
pb.connect(bp.o.Signal,  saphire.i.In_R)

pb.connect(saphire.o.Out_L, delay.i.Left)
pb.connect(saphire.o.Out_R, delay.i.Right_Return)

pb.connect(delay.o.Left,       audio.i.Left_input)
pb.connect(delay.o.Right_Send, audio.i.Right_input)

# ═══════════════════════════════════════════════════════════════════════════════
# GATE + CV MODULATION
# ═══════════════════════════════════════════════════════════════════════════════

pb.connect(clock.o.Clock_1, env_filter.i.Gate)
pb.connect(clock.o.Clock_1, env_vca.i.Gate)

pb.connect(env_filter.o.Envelope, ladder.i.Cutoff_mod)
pb.connect(env_vca.o.Envelope,    vca.i.Channel_1_linear_CV)

pb.connect(lfo1.o.Sine, bp.i.Cutoff_CV)

pb.connect(lfo2.o.Sine,     delay.i.L_Delay_Time_CV)
pb.connect(lfo2.o.Triangle, delay.i.R_Delay_Time_CV)

# Random -> ADSR decay and release CV (organic envelope variation, per tutorial)
pb.connect(rnd.o.Smooth, env_filter.i.Decay)
pb.connect(rnd.o.Smooth, env_filter.i.Release)
pb.connect(rnd.o.Smooth, env_vca.i.Decay)
pb.connect(rnd.o.Smooth, env_vca.i.Release)

# ═══════════════════════════════════════════════════════════════════════════════

print(pb.status)
for w in pb.warnings:
    print("WARN:", w)

out = "/Users/palaitis/Development/vcv-rack/patches/dub_techno_agentrack.vcv"
pb.save(out)
print(f"\nSaved: {out}")
