# Part 2: Core Concepts -- VCO, VCF, VCA, ADSR

The foundation of subtractive synthesis is a four-module signal chain:

```
VCO -> VCF -> VCA -> Output
```

- **VCO** (Voltage Controlled Oscillator): generates the raw sound
- **VCF** (Voltage Controlled Filter): shapes the tone
- **VCA** (Voltage Controlled Amplifier): controls the volume
- **ADSR** (Envelope): shapes how sound starts and stops over time

This is not just a VCV Rack thing -- this is the architecture of nearly every analog synthesizer ever built.

---

## The VCO: Generating Sound

### What it does

An oscillator produces a repeating waveform at a set frequency (pitch). Different waveforms have different timbres:

| Waveform | Sound character | Harmonics |
|----------|-----------------|-----------|
| Sine | Pure, smooth, flute-like | Fundamental only |
| Triangle | Soft, hollow | Odd harmonics, weak |
| Sawtooth | Bright, buzzy, string/brass-like | All harmonics |
| Square | Hollow, woody, clarinet-like | Odd harmonics only |
| Pulse | Thin or nasal (varies by pulse width) | Odd harmonics, variable |

### VCV VCO-1

Add **VCO-1** from the Module Browser. Key parameters:

- **FREQ** -- base frequency (pitch). Center = C4 (middle C) at 0V
- **FINE** -- fine-tune in cents (+/- 100 cents = 1 semitone)
- **V/OCT** input -- pitch CV input. Each +1V raises pitch by one octave
- **FM** input -- frequency modulation input (with attenuator knob)
- **PW** -- pulse width for the pulse wave output (0.5 = perfect square)
- **PWM** input -- modulate pulse width via CV
- **SYNC** input -- hard-sync: resets oscillator phase from another oscillator

Outputs: **SIN, TRI, SAW, SQR, SUB** (one octave below square)

### Pitch and 1V/oct

The **V/OCT** standard means: every +1V raises pitch by exactly one octave.
- 0V = C4 (middle C, ~261 Hz)
- +1V = C5 (~523 Hz)
- -1V = C3 (~130 Hz)
- +1/12 V per semitone (about 83mV per semitone)

This is how MIDI-CV connects to VCO-1: MIDI note 60 (C4) sends 0V, note 72 (C5) sends 1V.

---

## The VCF: Shaping Tone

A filter removes certain frequencies from a signal, carving the tone.

### Filter types

- **Low-pass filter (LPF)**: lets low frequencies through, cuts highs. Most common in synthesis. Makes sounds "darker" or "warmer".
- **High-pass filter (HPF)**: cuts lows, lets highs through. Thins out a sound.
- **Band-pass filter (BPF)**: only lets a band of frequencies through. Nasal, resonant tone.
- **Notch filter**: cuts a specific band, lets everything else through.

### Key parameters

- **FREQ** (cutoff frequency): the frequency at which the filter starts cutting. High cutoff = bright. Low cutoff = dark/muffled.
- **RES** (resonance / Q): boosts frequencies right at the cutoff. At high resonance, the filter self-oscillates (produces its own sine tone at the cutoff frequency).
- **FREQ CV input**: modulate the cutoff with a CV signal -- this is how filter sweeps work.

### VCV VCF-1

Add **VCF-1**. Patch it between VCO-1 and your output:

```
VCO-1 SAW out -> VCF-1 IN
VCF-1 LPF out -> AUDIO-8 input
```

Turn the **FREQ** knob slowly from left to right. Hear the sound go from dark/muffled to bright and buzzy -- that's the filter opening. This is "filter cutoff sweep", the most classic sound in synthesizer history.

Now turn up **RES** with the cutoff around 40-60%. That resonant peak adds a singing quality.

### Filter envelope (the magic)

The power of the VCF comes from modulating its cutoff with an envelope (covered below). Patching ADSR -> VCF FREQ CV creates the "wah" sound where the filter opens on note attack and closes as the note sustains.

---

## The VCA: Controlling Volume

Without a VCA, the oscillator plays continuously at full volume regardless of whether you're playing a note. The VCA is a gate: it lets signal through only when its CV input says to.

### VCV VCA-1

Add **VCA-1**. Patch it after the filter:

```
VCF-1 LPF out -> VCA-1 IN
VCA-1 OUT -> AUDIO-8 input
```

The **CV** input on VCA-1 controls gain: 0V = silent, 10V = full volume.

Right now, with nothing patched to CV, the VCA is closed -- no sound. We need an envelope.

---

## The ADSR: Shaping Over Time

An **envelope generator** outputs a voltage shape when triggered by a gate signal. The classic shape is ADSR:

- **A** (Attack): time to rise from 0V to peak when gate opens
- **D** (Decay): time to fall from peak to sustain level
- **S** (Sustain): voltage level held while gate remains open (this is a level, not a time)
- **R** (Release): time to fall back to 0V after gate closes

```
     /\
    /  \
   /    \____
  /          \
 /            \
A   D    S    R
```

### VCV ADSR-1

Add **ADSR-1**. Wire it up:

```
MIDI-CV GATE out -> ADSR-1 GATE in
ADSR-1 OUT -> VCA-1 CV in
```

Now playing a key: GATE goes high -> ADSR rises (attack), decays to sustain level, holds there while key is held, then releases when key is released. The VCA opens and closes with the envelope shape -- the note has a natural start and end.

### Common ADSR settings

| Sound type | A | D | S | R |
|------------|---|---|---|---|
| Plucked string | Very fast | Short | 0 | Short |
| Piano | Fast | Medium | 60% | Medium |
| Pad/strings | Slow | Med | 80% | Slow |
| Organ | Fast | 0 | 100% | Fast |
| Brass | Med | Short | 90% | Med |

---

## The Complete Basic Patch

Here's the full signal chain:

```
[MIDI-CV]
  V/OCT out ─────────────────────────────► VCO-1 V/OCT in
  GATE out  ─► ADSR-1 GATE in
               ADSR-1 OUT ────────────────► VCA-1 CV in

[VCO-1]
  SAW out ──► VCF-1 IN
              VCF-1 LPF out ──► VCA-1 IN
                                VCA-1 OUT ─► AUDIO-8
```

To build it:
1. Add: MIDI-CV, VCO-1, VCF-1, VCA-1, ADSR-1, AUDIO-8
2. Set MIDI-CV driver to "Computer keyboard"
3. Wire as shown above
4. Set VCF-1 FREQ to about 50%, RES to about 30%
5. Set ADSR-1: A=fast, D=medium, S=70%, R=medium
6. Press keys on your keyboard

You now have a complete subtractive synthesizer voice.

---

## Adding Filter Envelope Modulation

The patch above has the filter at a fixed cutoff. To add dynamic tone shaping, modulate the filter with the envelope:

```
ADSR-1 OUT ──► VCF-1 FREQ CV in  (in addition to VCA CV)
```

Adjust the **attenuator** knob on VCF-1's FREQ CV input to control how much the envelope opens the filter. Now the filter sweeps open on attack and closes on release -- much more expressive.

You can use a second ADSR for the filter (separate from the VCA envelope), or the same one.

---

## Two Oscillators (Detuning)

A classic thickening technique: add a second VCO, detune it slightly, and mix both into the filter.

1. Add a second **VCO-1**
2. Connect the same **MIDI-CV V/OCT** to both VCOs' V/OCT inputs
3. Set VCO-2's **FINE** knob to +5 to +15 cents (very slight detune)
4. Connect both VCOs' SAW outputs to **VCF-1** (you may need a **VCV Mixer** module, or use the filter's second input if available)

The slight pitch difference between the two oscillators creates **beating** -- a gentle wavering that gives synthesizer sounds their characteristic richness.

---

## Summary

| Module | Role | Key input | Key output |
|--------|------|-----------|------------|
| MIDI-CV | Note to voltage | Computer keyboard / MIDI | V/OCT, GATE |
| VCO-1 | Sound generation | V/OCT (pitch CV) | SAW, SIN, SQR, TRI |
| VCF-1 | Tone shaping | Audio in, FREQ CV | LPF, HPF, BPF |
| ADSR-1 | Envelope over time | GATE | Envelope voltage |
| VCA-1 | Volume gating | Audio in, CV | Audio out |
| AUDIO-8 | Sound card bridge | Audio in | (speakers) |

---

**Next:** [Part 3: Modulation](03-modulation.md) -- LFOs, CV routing, and making patches move.
