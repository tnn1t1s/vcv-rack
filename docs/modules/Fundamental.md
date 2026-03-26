# Fundamental Module Reference

Plugin: `Fundamental` (always installed)
Discovered JSON cache: `vcvpatch/discovered/Fundamental/*/2.6.4.json`
All param IDs verified against the 2.6.4 cache files.

---

## VCO

Analog-style voltage-controlled oscillator with four simultaneous waveform
outputs, 1V/oct pitch tracking, FM, and PWM.

**Node class:** `VCONode` (AudioSourceNode)
**Graph role:** Audio source. Outputs 0-3 are all audio.

### Params

| ID | Registry name | Default | Range   | Notes |
|----|---------------|---------|---------|-------|
| 0  | (removed)     | 0       | 0..1    | Legacy slot; do not use |
| 1  | SYNC          | 1       | 0..1    | Hard/soft sync mode toggle |
| 2  | FREQ          | 0       | -54..54 | Coarse tune in semitones |
| 3  | (removed)     | 0       | 0..1    | Legacy slot; do not use |
| 4  | FM            | 0       | -1..1   | FM CV attenuator. **Must be set > 0 for FM input to have any effect.** |
| 5  | PW            | 0.5     | 0.01..0.99 | Base pulse width (0.5 = square). 0 or 1 = silence. |
| 6  | PWM           | 0       | -1..1   | PWM CV attenuator. **Must be set > 0 for PWM input to have any effect.** |
| 7  | LINEAR        | 0       | 0..1    | FM mode: 0 = 1V/oct (exponential), 1 = linear |

### Input ports

| ID | Registry name | Aliases          | Paired attenuator param | Notes |
|----|---------------|------------------|-------------------------|-------|
| 0  | PITCH         | VOCT, V_OCT      | none                    | 1V/oct pitch CV |
| 1  | FM            |                  | param 4 (FM)            | Frequency modulation CV. Attenuator defaults to 0 -- set FM param > 0. |
| 2  | SYNC          |                  | none                    | Hard sync trigger input |
| 3  | PW            | PWM              | param 6 (PWM)           | Pulse width modulation CV. Attenuator defaults to 0 -- set PWM param > 0. |

### Output ports

| ID | Registry name | Aliases  | Notes |
|----|---------------|----------|-------|
| 0  | SIN           | SINE     | Sine wave |
| 1  | TRI           | TRIANGLE | Triangle wave |
| 2  | SAW           |          | Sawtooth wave |
| 3  | SQR           | SQUARE   | Square/pulse wave (width set by PW param) |

### Attenuator warning

Both FM (port 1) and PWM (port 3) have attenuator params that default to 0.
A connected cable has zero audible effect until the corresponding param is
opened. `SignalGraph.warnings` will flag this if detected.

```python
# Correct: FM with vibrato
vco = pb.module("Fundamental", "VCO", FREQ=0, FM=0.5)
pb.chain(lfo.o.SIN, vco.i.FM)

# Correct: PWM sweep (always start PW at 0.5)
vco = pb.module("Fundamental", "VCO", FREQ=0, PW=0.5, PWM=0.5)
pb.chain(lfo.o.SIN, vco.i.PW)
```

### Typical patch role

Primary melodic or bass oscillator. Connect VOCT to SEQ3 CV output or
MIDIToCVInterface PITCH. Use SAW for filter-heavy patches; SQR for hollow
or detuned sounds.

---

## VCF

State-variable filter with simultaneous lowpass and highpass outputs.

**Node class:** `VCFNode` (AudioProcessorNode)
**Graph role:** Audio processor. Audio path: IN (port 3) -> LPF (port 0) and
HPF (port 1).

### Params

| ID | Registry name | Default    | Range           | Notes |
|----|---------------|------------|-----------------|-------|
| 0  | FREQ          | 0.5        | 0.007..0.993    | Cutoff frequency (normalized; 0.5 ≈ mid-range) |
| 1  | FINE          | 0          | 0..1            | Unnamed/unlabeled fine tune slot |
| 2  | RES           | 0          | 0..1            | Resonance (0 = none, 1 = self-oscillation) |
| 3  | FREQ_CV       | 0          | -1..1           | Cutoff CV attenuator. **Must be set > 0 for FREQ CV input to have effect.** |
| 4  | DRIVE         | 0          | -1..1           | Input drive/saturation |
| 5  | RES_CV        | 0          | -1..1           | Resonance CV attenuator |
| 6  | DRIVE_CV      | 0          | -1..1           | Drive CV attenuator |

### Input ports

| ID | Registry name | Aliases | Paired attenuator param | Notes |
|----|---------------|---------|-------------------------|-------|
| 0  | FREQ          | CUTOFF  | param 3 (FREQ_CV)       | Cutoff CV. Attenuator defaults to 0. |
| 1  | RES           |         | param 5 (RES_CV)        | Resonance CV |
| 2  | DRIVE         |         | param 6 (DRIVE_CV)      | Drive CV |
| 3  | IN            | AUDIO   | none                    | Audio input |

### Output ports

| ID | Registry name | Aliases | Notes |
|----|---------------|---------|-------|
| 0  | LPF           | LP      | Lowpass output |
| 1  | HPF           | HP      | Highpass output |

### Attenuator warning

FREQ CV (port 0) has attenuator param 3 (FREQ_CV) defaulting to 0. Connect
ADSR or LFO to FREQ input and set `FREQ_CV` to a positive value, or use
the builder's `modulates()` helper which handles this automatically.

### Typical patch role

Tone shaping between VCO and VCA. Classic subtractive path: VCO SAW -> VCF
IN -> VCF LPF -> VCA. Sweep the cutoff with an ADSR for the classic
envelope filter sound.

---

## VCA

Dual voltage-controlled amplifier. Controls audio level with a CV signal.

**Node class:** `VCANode` (AudioProcessorNode)
**Graph role:** Audio processor. The proof system requires CV on port 1 (LIN1).

### CRITICAL: Input ID order

The port layout has three inputs per channel. The audio input is port 2, not
port 0 or port 1. Getting this wrong routes the audio signal to the CV input
and produces silence.

```
Port 0: EXP1   -- exponential CV input (rarely used)
Port 1: LIN1   -- linear CV input (USE THIS for ADSR/envelope)
Port 2: IN1    -- audio input (USE THIS for audio)
```

### Params

| ID | Registry name | Default | Range | Notes |
|----|---------------|---------|-------|-------|
| 0  | LEVEL1        | 1       | 0..1  | Channel 1 static level (only applies when LIN1/EXP1 unconnected) |
| 1  | LEVEL2        | 1       | 0..1  | Channel 2 static level |

### Input ports

| ID | Registry name | Aliases        | Required | Notes |
|----|---------------|----------------|----------|-------|
| 0  | EXP1          |                | no       | Exponential CV (volume law) |
| 1  | LIN1          | CV, CV1        | **yes**  | Linear CV input. **Required by proof system.** ADSR or other envelope must be connected here. |
| 2  | IN1           | IN, AUDIO      | no       | Audio input (channel 1) |
| 3  | EXP2          |                | no       | Exponential CV for channel 2 |
| 4  | LIN2          | CV2            | no       | Linear CV for channel 2 |
| 5  | IN2           |                | no       | Audio input (channel 2) |

### Output ports

| ID | Registry name | Aliases | Notes |
|----|---------------|---------|-------|
| 0  | OUT1          | OUT     | Channel 1 output |
| 1  | OUT2          |         | Channel 2 output |

### Why CV is required

`VCANode._required_cv = {1: CV}`. Without a CV signal on LIN1, the VCA level
is controlled by LEVEL1 param only. Because LEVEL1 defaults to 1 (open), audio
passes without CV -- but the proof system still flags it as unproven. Always
connect an envelope or CV source to LIN1.

The most common patch mistake: connecting audio to port 1 (LIN1) instead of
port 2 (IN1). Audio enters IN1 (id=2); CV enters LIN1 (id=1).

```python
vca = pb.module("Fundamental", "VCA")
pb.chain(vcf.o.LPF,     vca.i.IN)   # audio to port 2
pb.chain(adsr.o.ENV,    vca.i.CV)   # CV to port 1
pb.chain(vca.o.OUT,     audio.i.IN_L)
```

### Typical patch role

Final amplitude control driven by an ADSR envelope. Sits between the VCF and
AudioInterface2 in the standard VCO -> VCF -> VCA signal chain.

---

## ADSR

Attack-Decay-Sustain-Release envelope generator. Outputs a 0-10V CV signal
that rises on gate-on and falls on gate-off.

**Node class:** `FundamentalADSRNode` (ControllerNode)
**Graph role:** CV source. `_required_cv = {4: GATE}` -- GATE input must be
connected for the proof to pass. Output type is CV.

### Params

| ID | Registry name | Default | Range | Notes |
|----|---------------|---------|-------|-------|
| 0  | ATTACK (A)    | 0.5     | 0..1  | Attack time (normalized) |
| 1  | DECAY (D)     | 0.5     | 0..1  | Decay time |
| 2  | SUSTAIN (S)   | 0.5     | 0..1  | Sustain level |
| 3  | RELEASE (R)   | 0.5     | 0..1  | Release time |
| 4  | ATTACK_CV     | 0       | -1..1 | Attack CV attenuator |
| 5  | DECAY_CV      | 0       | -1..1 | Decay CV attenuator |
| 6  | SUSTAIN_CV    | 0       | -1..1 | Sustain CV attenuator |
| 7  | RELEASE_CV    | 0       | -1..1 | Release CV attenuator |
| 8  | PUSH          | 0       | 0..1  | Manual trigger button |

### Input ports

| ID | Registry name | Required | Notes |
|----|---------------|----------|-------|
| 0  | ATTACK        | no       | Attack time CV |
| 1  | DECAY         | no       | Decay time CV |
| 2  | SUSTAIN       | no       | Sustain level CV |
| 3  | RELEASE       | no       | Release time CV |
| 4  | GATE          | **yes**  | Gate signal. High = envelope runs; low = release phase. |
| 5  | RETRIG        | no       | Re-trigger: restart attack without releasing. Feed from MIDIToCVInterface RETRIG for legato. |

### Output ports

| ID | Registry name | Aliases | Notes |
|----|---------------|---------|-------|
| 0  | ENV           | OUT     | Envelope CV output (0-10V) |

### Typical patch role

Drives the VCA CV input (amplitude shaping) and optionally the VCF cutoff CV
(timbre shaping). Gate comes from SEQ3 TRIG or MIDIToCVInterface GATE.

```python
adsr = pb.module("Fundamental", "ADSR",
                 ATTACK=0.01, DECAY=0.3, SUSTAIN=0.6, RELEASE=0.5)
pb.chain(seq.o.TRIG,  adsr.i.GATE)
pb.chain(adsr.o.ENV,  vca.i.CV)
```

---

## LFO

Low-frequency oscillator producing four simultaneous waveform outputs for
slow modulation (vibrato, filter sweep, PWM, tremolo, etc.).

**Node class:** `FundamentalLFONode` (ControllerNode)
**Graph role:** CV source. All four outputs are CV type.

### Params

| ID | Registry name | Default | Range   | Notes |
|----|---------------|---------|---------|-------|
| 0  | OFFSET        | 1       | 0..1    | Toggle: 1 = unipolar (0 to +5V), 0 = bipolar (-5V to +5V) |
| 1  | INVERT        | 0       | 0..1    | Toggle: inverts output polarity |
| 2  | FREQ          | 1       | -8..10  | Frequency (approximately Hz at the display value). 1.0 ≈ 1 Hz. |
| 3  | FM            | 0       | -1..1   | FM CV attenuator |
| 4  | (removed)     | 0       | 0..1    | Legacy slot; do not use |
| 5  | PW            | 0.5     | 0.01..0.99 | Pulse width for SQR output |
| 6  | PWM           | 0       | -1..1   | PWM CV attenuator |

### Input ports

| ID | Registry name | Notes |
|----|---------------|-------|
| 0  | FM            | Frequency modulation CV |
| 2  | RESET         | Resets phase to 0 on trigger |
| 3  | PW            | Pulse width CV |
| 4  | CLOCK         | Clock input: LFO syncs to incoming clock |

Note: input IDs 1 is a removed slot (FM2). Registry assigns FM to id 0 and
the next real inputs start at 2.

### Output ports

| ID | Registry name | Aliases  | Notes |
|----|---------------|----------|-------|
| 0  | SIN           | SINE     | Sine wave |
| 1  | TRI           | TRIANGLE | Triangle wave |
| 2  | SAW           |          | Sawtooth wave |
| 3  | SQR           | SQUARE   | Square wave (width = PW param) |

### OFFSET param behavior

When `OFFSET=1` (default), all outputs are unipolar: 0V to +5V. This is
convenient for driving VCF cutoff (no risk of closing below 0). When
`OFFSET=0`, outputs are bipolar: -5V to +5V. Use bipolar for FM/vibrato
where symmetric pitch modulation is wanted.

### Typical patch role

Modulation source. Common targets: VCF FREQ (filter wobble), VCO FM (vibrato),
VCO PW (PWM sweep), reverb SIZE, mixer level (tremolo). Set FREQ to a low
value (0.1-0.5 Hz) for slow sweeps.

---

## Noise

Generates noise signals across six spectral colors simultaneously. No inputs,
no params.

**Node class:** `NoiseNode` (AudioSourceNode)
**Graph role:** Audio source. All seven outputs are audio type.

### Output ports

| ID | Registry name | Notes |
|----|---------------|-------|
| 0  | WHITE         | Equal energy per Hz across all frequencies |
| 1  | PINK          | -3dB/octave, perceptually flat |
| 2  | RED           | -6dB/octave (Brownian motion) |
| 3  | VIOLET        | +6dB/octave |
| 4  | BLUE          | +3dB/octave |
| 5  | GRAY          | Psychoacoustically weighted |
| 6  | BLACK         | TODO: verify exact spectral slope |

### Params

None.

### Typical patch role

White or pink noise fed into a VCF for percussion (hi-hat, snare, wind).
Also useful as a randomization CV source when filtered.

---

## SEQ3

8-step, 3-row CV sequencer with a single TRIG output and independent clock
input. The canonical simple step sequencer in the Fundamental plugin.

**Node class:** `SEQ3Node` (ControllerNode)
**Graph role:** CV and gate source. `_required_cv = {1: CLOCK}` -- CLOCK input
must be connected. Output types: TRIG (port 0) = GATE, CV1-3 (ports 1-3) = CV.

### Key limitation: GATE params suppress TRIG only -- CV always advances

Setting a step's GATE param to 0 suppresses the TRIG output on that step,
but the CV rows still change every clock tick regardless. There is no way to
produce a sparse pitch sequence (some steps play, some hold) with SEQ3 alone.

**Rule:** Do not use SEQ3 for sparse gate patterns. Use
CountModula/Sequencer16 for independent per-step gate + CV control.

Source: `docs/gotchas.md`

### Params

**Global params:**

| ID | Registry name | Default | Range | Notes |
|----|---------------|---------|-------|-------|
| 0  | TEMPO         | 1       | -2..4 | Internal tempo (only used when CLOCK input disconnected) |
| 1  | RUN           | 0       | 0..1  | Run/stop toggle |
| 2  | RESET         | 0       | 0..1  | Reset button (momentary) |
| 3  | TRIG (STEPS)  | 8       | 1..8  | Number of active steps (labeled "Steps" in discovered JSON) |

**CV row params (3 rows x 8 steps):**

Formula: param ID = `4 + row * 8 + step`, where row is 0-2 and step is 0-7.
Registry name: `CV_{row}_{step}` (e.g., `CV_0_0` through `CV_2_7`).

| Row | Steps | Param IDs | Range    | Notes |
|-----|-------|-----------|----------|-------|
| 0   | 0-7   | 4-11      | -10..10  | CV row 1 (V/oct pitch) |
| 1   | 0-7   | 12-19     | -10..10  | CV row 2 |
| 2   | 0-7   | 20-27     | -10..10  | CV row 3 |

**Gate params (1 row x 8 steps):**

Formula: param ID = `28 + step`
Registry name: `GATE_{step}` (e.g., `GATE_0` through `GATE_7`).

| Step | Param ID | Default | Range | Notes |
|------|----------|---------|-------|-------|
| 0    | 28       | 0       | 0..1  | 1 = TRIG fires on this step; 0 = TRIG suppressed |
| 1    | 29       | 0       | 0..1  | |
| ...  | ...      | 0       | 0..1  | |
| 7    | 35       | 0       | 0..1  | |

**CV control params:**

| ID | Registry name | Default | Range | Notes |
|----|---------------|---------|-------|-------|
| 36 | TEMPO_CV      | 1       | 0..1  | Tempo CV attenuator |
| 37 | STEPS_CV      | 1       | 0..1  | Steps CV attenuator |
| 38 | CLOCK         | 0       | 0..1  | Internal clock enable |

### Input ports

| ID | Registry name | Required | Notes |
|----|---------------|----------|-------|
| 0  | TEMPO         | no       | External tempo CV |
| 1  | CLOCK         | **yes**  | Clock input. Each rising edge advances one step. |
| 2  | RESET         | no       | Resets to step 1 on trigger |
| 3  | STEPS         | no       | Override step count via CV |
| 4  | RUN           | no       | Run/stop gate |

### Output ports

| ID | Registry name | Aliases          | Type | Notes |
|----|---------------|------------------|------|-------|
| 0  | TRIG          |                  | GATE | Fires on each step where GATE param = 1 |
| 1  | CV1           | CV_A             | CV   | Row 1 CV output |
| 2  | CV2           | CV_B             | CV   | Row 2 CV output |
| 3  | CV3           | CV_C             | CV   | Row 3 CV output |
| 4  | STEP_0        |                  | GATE | Step 1 individual gate output |
| 5  | STEP_1        |                  | GATE | Step 2 individual gate output |
| ...| ...           |                  | GATE | (STEP_0 through STEP_7: ports 4-11) |
| 11 | STEP_7        |                  | GATE | Step 8 individual gate output |
| 12 | STEPS         |                  | CV   | Current step count output |
| 13 | CLOCK         |                  | CLOCK| Clock pass-through |
| 14 | RUN           |                  | GATE | Run state output |
| 15 | RESET         |                  | GATE | Reset pulse output |

### Typical patch role

Melodic sequencer. Set CV_0_{step} params for pitch (1V/oct; 0=C4, 1/12=C#4,
etc.). Connect TRIG to an ADSR GATE input. Set all GATE params to 1 for a
dense pattern, or selectively disable steps to create rests (understanding
that CV still advances on rested steps).

```python
seq = pb.module("Fundamental", "SEQ3", **{
    f"CV_0_{i}": v for i, v in enumerate([0, 0.25, 0.5, 0.75, 1.0, 0.75, 0.5, 0.25])
})
pb.chain(clock.o.CLK, seq.i.CLOCK)
pb.chain(seq.o.TRIG,  adsr.i.GATE)
pb.chain(seq.o.CV_A,  vco.i.VOCT)
```

---

## Mult

Passive signal splitter: one input fanned out to three copies. Two independent
splitters in a single module.

**Node class:** `MultNode` (AudioProcessorNode)
**Graph role:** Audio processor. Routes: IN1 (port 0) -> OUT1A/B/C (ports 0-2);
IN2 (port 3) -> OUT2A/B/C (ports 3-5).

### Input ports

| ID | Registry name | Aliases | Notes |
|----|---------------|---------|-------|
| 0  | IN1           | A       | First input signal |
| 3  | IN2           | B       | Second input signal |

### Output ports

| ID | Registry name | Notes |
|----|---------------|-------|
| 0  | OUT1A         | Copy 1 of IN1 |
| 1  | OUT1B         | Copy 2 of IN1 |
| 2  | OUT1C         | Copy 3 of IN1 |
| 3  | OUT2A         | Copy 1 of IN2 |
| 4  | OUT2B         | Copy 2 of IN2 |
| 5  | OUT2C         | Copy 3 of IN2 |

### Params

None (passive splitter).

### Typical patch role

Fan a single CV or audio source to multiple destinations without loading the
source signal. Common use: split a sequencer CV to drive multiple VCOs in
unison, or distribute a clock to multiple modules.

Note: VCV Rack cables are already virtual (no impedance loading), so Mult is
optional for pure software patching. Use it for explicitness or when the
patch builder requires a single output to feed multiple inputs through a named
intermediate node.
