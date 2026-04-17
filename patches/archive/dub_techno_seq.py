"""
Dub techno -- 24-step chord root sequence via SEQ3 + SequentialSwitch2.

Technique from the tutorial: SEQ3 has 3 rows of 8 steps (chord roots as V/oct).
SequentialSwitch2 cycles through rows clocked by SEQ3's Step 8 trigger output --
so it advances exactly when SEQ3 completes each 8-step cycle.
Pattern: row1(8) -> row2(8) -> row3(8) -> back to row1.
SS output feeds ChordCV which adds minor 7th voicing polyphonically.

Chord roots (V/oct, 1/12V per semitone from C4=0V):
  Steps 1-8  (row 1): C  F  C  G  C  Ab Bb C
  Steps 9-16 (row 2): F  C  G  C  Bb F  G  C

AgentRack: Ladder (LPF), Saphire (reverb), ADSR x2 (when #1 adds CV inputs -- using Fundamental for now)
"""

from vcvpatch.builder import PatchBuilder

pb = PatchBuilder()

C  =  0.0
F  =  5/12
G  =  7/12
Bb = 10/12
Ab = -4/12

# ── Clock ─────────────────────────────────────────────────────────────────────
clock = pb.module("ImpromptuModular", "Clocked-Clkd",
                  **{"Master clock": 120.0, "Run": 1.0})

# ── SEQ3 (3 rows = 3 chord root sequences, 8 steps each) ──────────────────────
seq = pb.module("Fundamental", "SEQ3",
    Steps=8,
    **{
        # Steps 1-8
        "CV 1 step 1": C,  "CV 1 step 2": F,  "CV 1 step 3": C,  "CV 1 step 4": G,
        "CV 1 step 5": C,  "CV 1 step 6": Ab, "CV 1 step 7": Bb, "CV 1 step 8": C,
        # Steps 9-16
        "CV 2 step 1": F,  "CV 2 step 2": C,  "CV 2 step 3": G,  "CV 2 step 4": C,
        "CV 2 step 5": Bb, "CV 2 step 6": F,  "CV 2 step 7": G,  "CV 2 step 8": C,
        # Gates: all steps active
        "Step 1 trigger": 1, "Step 2 trigger": 1, "Step 3 trigger": 1, "Step 4 trigger": 1,
        "Step 5 trigger": 1, "Step 6 trigger": 1, "Step 7 trigger": 1, "Step 8 trigger": 1,
    })

# ── SequentialSwitch2 (4 inputs -> 1 output, clocked by SEQ3 end-of-cycle) ───
# Steps param: 0=2steps, 1=3steps, 2=4steps -- use 0 for 2 rows = 16 steps
ss = pb.module("Fundamental", "SequentialSwitch2", Steps=0)

# ── ChordCV (adds minor 7th voicing to incoming root CV) ─────────────────────
chord = pb.module("AaronStatic", "ChordCV",
                  **{"Root Note": 0.0, "Chord Type": -1.0,
                     "Inversion": 0.0, "Voicing": 1.0})

# ── Oscillators ───────────────────────────────────────────────────────────────
vco1 = pb.module("Fundamental", "VCO", Frequency=0.0,   Pulse_width=0.5,
                 Frequency_modulation=0.1, Pulse_width_modulation=0.08)
vco2 = pb.module("Fundamental", "VCO", Frequency=-12.0, Pulse_width=0.5,
                 Frequency_modulation=0.1, Pulse_width_modulation=0.08)

# ── Mixer + VCA + Sum ─────────────────────────────────────────────────────────
mix    = pb.module("Fundamental", "VCMixer")
vca    = pb.module("Fundamental", "VCA")
summer = pb.module("Fundamental", "Sum")

# ── Envelopes (Fundamental until AgentRack ADSR gets CV inputs -- issue #1) ───
env_filter = pb.module("Fundamental", "ADSR",
                        Attack=0.008, Decay=0.5, Sustain=0.0, Release=0.6)
env_vca    = pb.module("Fundamental", "ADSR",
                        Attack=0.015, Decay=0.4, Sustain=0.6, Release=0.8)

# ── AgentRack Ladder + Bogaudio bandpass ──────────────────────────────────────
ladder = pb.module("AgentRack", "Ladder", Cutoff=0.25, Resonance=0.4)
bp     = pb.module("Bogaudio", "Bogaudio-VCF",
                   **{"Center/cutoff frequency": 0.45,
                      "Resonance / bandwidth": 0.5, "Mode": 2.0})

# ── AgentRack Saphire (reverb) ────────────────────────────────────────────────
saphire = pb.module("AgentRack", "Saphire", Mix=0.65, Time=0.80, Tone=0.4)

# ── Delay ─────────────────────────────────────────────────────────────────────
delay = pb.module("AlrightDevices", "Chronoblob2",
                  **{"Delay Time": 0.375, "Feedback": 0.58,
                     "Dry/Wet": 0.40, "Delay Mode": 1.0,
                     "Time Modulation Mode": 0.0})

# ── Modulation ────────────────────────────────────────────────────────────────
lfo1 = pb.module("Fundamental", "LFO", Frequency=-2.5)
lfo2 = pb.module("Fundamental", "LFO", Frequency=-2.0)
rnd  = pb.module("Fundamental", "Random", **{"Internal trigger rate": -1.5})

# ── Output ────────────────────────────────────────────────────────────────────
audio = pb.module("Core", "AudioInterface2")

# ═══════════════════════════════════════════════════════════════════════════════
# CLOCK + SEQUENCER
# ═══════════════════════════════════════════════════════════════════════════════

pb.connect(clock.o.Master_clock, seq.i.Clock)
pb.connect(clock.o.Reset,        seq.i.Reset)
pb.connect(clock.o.Reset,        ss.i.Reset)

# SEQ3 step 8 trigger -> SS clock (advances SS after each 8-step cycle)
pb.connect(seq.o.Step_8, ss.i.Clock)

# SEQ3 rows -> SS inputs
pb.connect(seq.o.CV_1, ss.i.Channel_1)
pb.connect(seq.o.CV_2, ss.i.Channel_2)

# Static Cm7 for now -- SS not connected to ChordCV

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
pb.connect(ladder.o.Out,        bp.i.Signal)
pb.connect(bp.o.Signal,         saphire.i.In_L)
pb.connect(bp.o.Signal,         saphire.i.In_R)

pb.connect(saphire.o.Out_L, delay.i.Left)
pb.connect(saphire.o.Out_R, delay.i.Right_Return)
pb.connect(delay.o.Left,       audio.i.Left_input)
pb.connect(delay.o.Right_Send, audio.i.Right_input)

# ═══════════════════════════════════════════════════════════════════════════════
# GATE + CV MODULATION
# ═══════════════════════════════════════════════════════════════════════════════

# SEQ3 trigger output -> envelopes (gates the chords)
pb.connect(seq.o.Trigger, env_filter.i.Gate)
pb.connect(seq.o.Trigger, env_vca.i.Gate)

pb.connect(env_filter.o.Envelope, ladder.i.Cutoff_mod)
pb.connect(env_vca.o.Envelope,    vca.i.Channel_1_linear_CV)

pb.connect(lfo1.o.Sine, bp.i.Cutoff_CV)
pb.connect(lfo2.o.Sine,     delay.i.L_Delay_Time_CV)
pb.connect(lfo2.o.Triangle, delay.i.R_Delay_Time_CV)

pb.connect(rnd.o.Smooth, env_filter.i.Decay)
pb.connect(rnd.o.Smooth, env_filter.i.Release)
pb.connect(rnd.o.Smooth, env_vca.i.Decay)
pb.connect(rnd.o.Smooth, env_vca.i.Release)

# ═══════════════════════════════════════════════════════════════════════════════

print(pb.status)
for w in pb.warnings:
    print("WARN:", w)

out = os.path.splitext(os.path.abspath(__file__))[0] + ".vcv"
pb.save(out)
print(f"\nSaved: {out}")
