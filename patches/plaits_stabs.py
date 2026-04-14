"""
Faithful recreation of 'Dub Tech Stabs with Plaits.vcv'

Signal chain (matches original exactly):
  SimpleClock (clockMult=4, auto-start)
    .Clock -> DrumKit/Sequencer clock
    .Reset -> DrumKit/Sequencer input 3
    ./4    -> ClockDivider, RandomValues, Chronoblob2 sync, DADSRH trigger
    ./32   -> Drums[type=4] direct trigger (phrase accent)

  ClockDivider out[3] (/16 of /4 = one stab per 4 beats)
    -> Plaits trigger

  RandomValues (triggered by /4)
    .Random_7 -> Coffee/Quant V/oct In
    .Random_2 -> Plaits Timbre

  Coffee/Quant (only F and Bb active = Cm7 tensions)
    .V/oct Out -> Plaits V/oct
    .V/oct Out -> Kickall Tune V/Oct (kick follows chord)

  Plaits (Chord model=6, set via data)
    -> LVCF1 signal in
  ADSR (gate from DrumKit/Seq out[7], patterns empty so stays quiet)
    -> LVCF1 cutoff CV
  LVCF1 -> Mixer Ch2

  DADSRH (looping, triggered by /4)
    .Inverted -> Mixer Ch5 Level CV (Kickall volume pumping)
    .Inverted -> Mixer Ch6 Level CV (Plateau direct volume pumping)

  DrumKit/Sequencer (empty patterns, just provides clocked triggers)
    out[4] -> Drums type=3 (perc)
    out[5] -> Drums type=2 (rim)
    out[6] -> Kickall (BD)
    out[7] -> Drums type=0 (hat) + ADSR gate

  Mixer (mscHack 9ch):
    Ch1: Drums type=0
    Ch2: LVCF1 (Plaits)
    Ch3: Drums type=2
    Ch4: Drums type=3
    Ch5: Kickall  [Level CV from DADSRH]
    Ch6: Plateau direct [Level CV from DADSRH]
    Ch7: Drums type=4 (/32 triggered)
    AUX1: Chronoblob2 send/return (delay)
    AUX2: Plateau send/return (reverb)

  Plateau out -> Mixer Ch6 direct AND Mixer AUX2 return AND LVCF2 (dead-end)
  Mixer main -> Pressor -> AudioInterface2
"""

from vcvpatch.builder import PatchBuilder

pb = PatchBuilder()

# ── Clock (clockMult=4 halves the effective BPM, auto-start via data) ─────────
clock = pb.module("JW-Modules", "SimpleClock",
                  data={"clockMult": 4, "running": True},
                  **{"BPM": 1.0, "Run": 0.0, "Random Reset Probability": -2.0})

# ── Clock divider ─────────────────────────────────────────────────────────────
cdiv = pb.module("AgentRack", "ClockDiv")

# ── Drum sequencer (patterns empty -- just provides clocked structure) ─────────
drumseq = pb.module("DrumKit", "Sequencer",
                    data={"running": True, "cycling": False, "currentPlay": 1,
                          "programs": [1,2,1,2,1,2,1,2]})

# ── Random values (new random pitch+timbre on every beat) ─────────────────────
rnd = pb.module("Fundamental", "RandomValues")

# ── Coffee/Quant: only F (param 7) and Bb (param 12) active ───────────────────
quant = pb.module("Coffee", "Quant", **{
    "Note 1":  0,  # C   off
    "Note 2":  0,  # C#  off
    "Note 3":  0,  # D   off
    "Note 4":  0,  # Eb  off
    "Note 5":  0,  # E   off
    "Note 6":  1,  # F   ON
    "Note 7":  0,  # F#  off
    "Note 8":  0,  # G   off
    "Note 9":  0,  # Ab  off
    "Note 10": 0,  # A   off
    "Note 11": 1,  # Bb  ON
    "Note 12": 0,  # B   off
})

# ── Plaits: Chord model set via data (no manual step needed) ──────────────────
plaits = pb.module("AudibleInstruments", "Plaits",
                   data={"lowCpu": False, "model": 6},
                   **{
    "Frequency":             -0.9445768594741821,
    "Harmonics":              0.29879525303840637,
    "Timbre":                 0.11445778608322144,
    "Morph":                  0.30722782015800476,
    "Lowpass gate decay":     1.0,
    "Lowpass gate response":  0.5012022256851196,
})

# ── ADSR (gate from drum seq track 8, patterns empty so filter stays dark) ────
adsr = pb.module("Bogaudio", "Bogaudio-ADSR", **{
    "Attack":  0.06746988743543625,
    "Decay":   0.0,
    "Sustain": 0.0,
    "Release": 0.07285448908805847,
})

# ── LVCF1: Plaits filter (dark, ADSR-controlled but rarely opens) ─────────────
lvcf1 = pb.module("Bogaudio", "Bogaudio-LVCF",
                  data={"poles": 4, "bandwidthMode": "pitched"},
                  **{
    "Center/cutoff frequency":  0.15060241520404816,
    "Frequency CV attenuation": 0.4240967631340027,
    "Resonance / bandwidth":    0.15301203727722168,
})

# ── DADSRH: looping envelope from /4 clock -> mixer volume CV (pumping) ───────
dadsr = pb.module("Bogaudio", "Bogaudio-DADSRH",
                  data={"triggerOnLoad": True, "shouldTriggerOnLoad": True},
                  **{
    "Delay":          0.0,
    "Attack":         0.1446,
    "Decay":          0.1313,
    "Sustain":        0.0,
    "Release":        0.0,
    "Hold":           0.4328,
    "Attack shape":   1.0,
    "Decay shape":    1.0,
    "Release shape":  1.0,
    "Loop":           1.0,
    "Speed":          1.0,
    "Retrigger":      1.0,
})

# ── Drum voices ───────────────────────────────────────────────────────────────
# Types from original: 0=hat, 2=rim, 3=perc, 4=phrase-accent
drums_hat  = pb.module("dbRackModules", "Drums", **{
    "Type": 0.0, "Sample selection": 6.0, "Pitch": 0.45, "Decay": 0.226})
drums_rim  = pb.module("dbRackModules", "Drums", **{
    "Type": 2.0, "Sample selection": 9.0, "Pitch": 0.45, "Decay": 0.113})
drums_perc = pb.module("dbRackModules", "Drums", **{
    "Type": 3.0, "Sample selection": 3.0, "Pitch": 0.45, "Decay": 0.201})
drums_acc  = pb.module("dbRackModules", "Drums", **{
    "Type": 4.0, "Sample selection": 3.0, "Pitch": 0.45, "Decay": 1.0})

# ── Kickall ───────────────────────────────────────────────────────────────────
kick = pb.module("Befaco", "Kickall", **{
    "Tune":                       33.92992401123047,
    "Wave shape":                 0.21204811334609985,
    "VCA Envelope decay time":    0.460000604391098,
})

# ── Mixer: exact original channel assignments and AUX send levels ─────────────
# Ch params: Main=0, Ch1..Ch9=1..9, Gr1..Gr3=10..12, AUX1..AUX4=13..16
# AUX send params: Ch1.AUX1=81, Ch2.AUX1=85, Ch2.AUX2=86, Ch3.AUX2=90,
#                  Ch4.AUX2=94, Ch7.AUX2=106
mixer = pb.module("mscHack", "Mix_9_3_4", **{
    "Main Level":       0.7181,
    "Ch1. Level":       0.69,    # drums_hat
    "Ch2. Level":       0.646,   # LVCF1/Plaits
    "Ch3. Level":       0.378,   # drums_rim
    "Ch4. Level":       0.392,   # drums_perc
    "Ch5. Level":       0.404,   # Kickall (also modulated by DADSRH)
    "Ch6. Level":       0.444,   # Plateau direct (also modulated by DADSRH)
    "Ch7. Level":       0.678,   # drums_acc
    "AUX1. Level":      0.82,    # Chronoblob return
    "AUX2. Level":      0.844,   # Plateau return
    # AUX sends
    "Ch2. AUX 1 Level": 0.9072,  # Plaits -> Chronoblob
    "Ch2. AUX 2 Level": 0.8771,  # Plaits -> Plateau
    "Ch3. AUX 2 Level": 0.4506,  # drums_rim -> Plateau
    "Ch4. AUX 2 Level": 0.5325,  # drums_perc -> Plateau
    "Ch7. AUX 2 Level": 0.9747,  # drums_acc -> Plateau
})

# ── Plateau (dry+wet, output goes to Ch6 direct AND AUX2 return) ─────────────
plateau = pb.module("Valley", "Plateau", **{
    "Dry level":  1.0,
    "Wet level":  0.4922,
    "Size":       0.663636326789856,
    "Decay":      0.5511191487312317,
})

# ── Chronoblob2 (AUX1 send/return -- delay) ───────────────────────────────────
delay = pb.module("AlrightDevices", "Chronoblob2",
                  data={"delay_mode": 1, "hold_behavior": 0, "sync_prescaler": 6},
                  **{
    "Feedback":   0.6566261053085327,
    "Delay Time": 0.4204815626144409,
    "Dry/Wet":    0.5662652850151062,
})

# ── LVCF2 (dead-end: Plateau -> LVCF2, output unconnected, matches original) ──
lvcf2 = pb.module("Bogaudio", "Bogaudio-LVCF",
                  data={"poles": 4, "bandwidthMode": "pitched"},
                  **{
    "Center/cutoff frequency":  0.0,
    "Frequency CV attenuation": 1.0,
    "Resonance / bandwidth":    0.0,
})

# ── Compressor ────────────────────────────────────────────────────────────────
pressor = pb.module("Bogaudio", "Bogaudio-Pressor", **{
    "Threshold":   0.6373478770256042,
    "Ratio":       0.8939758539199829,
    "Attack":      0.3162277638912201,
    "Release":     0.2487582266330719,
    "Output gain": 0.3493974804878235,
})

# ── Output ────────────────────────────────────────────────────────────────────
audio = pb.module("Core", "AudioInterface2")

# ═══════════════════════════════════════════════════════════════════════════════
# CONNECTIONS (matches original cable list)
# ═══════════════════════════════════════════════════════════════════════════════

# Clock -> drum sequencer (Clock input 0, Reset input 3)
pb.connect(clock.o.Clock,  drumseq.in_id(0))
pb.connect(clock.o.Reset,  drumseq.in_id(3))

# Clock /4 -> ClockDivider, RandomValues, Chronoblob sync, DADSRH
pb.connect(clock.o._4,     cdiv.i.Clock)
pb.connect(clock.o.Reset,  cdiv.i.Reset)
pb.connect(clock.o._4,     rnd.i.Trigger)
pb.connect(clock.o._4,     delay.i.Sync_Trigger)
pb.connect(clock.o._4,     dadsr.i.Trigger)

# Clock /32 -> drums_acc (phrase accent, very slow)
pb.connect(clock.o._32, drums_acc.i.Trig)

# ClockDiv /16 of /4 = very slow stab (every 4 beats * 16 = 16 beats)
pb.connect(cdiv.o._16, plaits.i.Trigger)

# Drum sequencer -> drum triggers
pb.connect(drumseq.out_id(4), drums_perc.i.Trig)
pb.connect(drumseq.out_id(5), drums_rim.i.Trig)
pb.connect(drumseq.out_id(6), kick.i.Trigger)
pb.connect(drumseq.out_id(7), drums_hat.i.Trig)
pb.connect(drumseq.out_id(7), adsr.i.Gate)

# RandomValues -> Quant V/oct + Plaits timbre
pb.connect(rnd.o.Random_7, quant.i.V_OCT_In)
pb.connect(rnd.o.Random_2, plaits.i.Timbre)

# Quant -> Plaits V/oct AND Kickall tune (kick follows chord)
pb.connect(quant.o.V_OCT_Out, plaits.i.Pitch_1V_oct_)
pb.connect(quant.o.V_OCT_Out, kick.i.Tune_V_Oct_)

# ADSR -> LVCF1 cutoff CV
pb.connect(adsr.o.Envelope, lvcf1.i.Cutoff_CV)

# Plaits -> LVCF1 -> Mixer Ch2
pb.connect(plaits.o.Main,  lvcf1.i.Signal)
pb.connect(lvcf1.o.Signal, mixer.i.Ch2_Left)

# DADSRH inverted -> Mixer Ch5 Level CV (Kickall pumping) + Ch6 Level CV (Plateau pumping)
pb.connect(dadsr.o.Inverted_envelope, mixer.i.Ch5_Level_CV)
pb.connect(dadsr.o.Inverted_envelope, mixer.i.Ch6_Level_CV)

# Drums direct -> Mixer channels
pb.connect(drums_hat.o.CV,  mixer.i.Ch1_Left)
pb.connect(drums_rim.o.CV,  mixer.i.Ch3_Left)
pb.connect(drums_perc.o.CV, mixer.i.Ch4_Left)
pb.connect(kick.o.Kick,     mixer.i.Ch5_Left)
pb.connect(drums_acc.o.CV,  mixer.i.Ch7_Left)

# Mixer AUX1 send -> Chronoblob2 -> Mixer AUX1 return (delay)
pb.connect(mixer.o.Aux_1_Left,  delay.i.Left)
pb.connect(mixer.o.Aux_1_Right, delay.i.Right_Return)
pb.connect(delay.o.Left,        mixer.i.AUX1_Left)
pb.connect(delay.o.Right_Send,  mixer.i.AUX1_Right)

# Mixer AUX2 send -> Plateau -> Mixer AUX2 return + Ch6 direct (reverb)
pb.connect(mixer.o.Aux_2_Left,  plateau.i.Left)
pb.connect(mixer.o.Aux_2_Right, plateau.i.Right)
pb.connect(plateau.o.Left,      mixer.i.AUX2_Left)
pb.connect(plateau.o.Right,     mixer.i.AUX2_Right)
pb.connect(plateau.o.Left,      mixer.i.Ch6_Left)    # direct channel too

# Plateau -> LVCF2 (dead-end, matches original)
pb.connect(plateau.o.Left,  lvcf2.i.Signal)
pb.connect(adsr.o.Envelope, lvcf2.i.Cutoff_CV)

# Mixer main -> Pressor -> Audio
pb.connect(mixer.o.Main_Left,  pressor.i.Left_signal)
pb.connect(mixer.o.Main_Right, pressor.i.Right_signal)
pb.connect(pressor.o.Left_signal,  audio.i.Left_input)
pb.connect(pressor.o.Right_signal, audio.i.Right_input)

# ═══════════════════════════════════════════════════════════════════════════════

print(pb.status)
for w in pb.warnings:
    print("WARN:", w)

out = "/Users/palaitis/Development/vcv-rack/patches/plaits_stabs.vcv"
pb.save(out)
print(f"\nSaved: {out}")
print("Plaits model=6 (Chord) set automatically via data field.")
print("SimpleClock auto-starts (running=True in data).")
