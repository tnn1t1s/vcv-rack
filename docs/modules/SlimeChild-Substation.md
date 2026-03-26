# SlimeChild-Substation Reference

Plugin: `SlimeChild-Substation`
Verified against: v2.2.6 (discovered cache + registry.py)
Introspectable: YES (all modules below pass `rack_introspect`)

---

## Standard Signal Chain

```
Clock → (sequencer) → Quantizer → SubOscillator → Mixer → Filter → VCA → Audio
                                                              ^              ^
                           Envelopes ENV2 ──────────────────(FM)            |
                           Envelopes ENV1 ──────────────────────────────(CV)|
```

The sequencer is not part of the Substation suite; use `CountModula/Sequencer16`,
`Fundamental/SEQ3`, or `SlimeChild-Substation-PolySeq` depending on needs.

---

## Clock

**Model:** `SlimeChild-Substation-Clock`
**Graph class:** `SubstationClockNode` (ControllerNode)
**Purpose:** Master clock with a BPM-rate BASE output and an integer-multiplied MULT output.

### Params (verified, v2.2.6)

| ID | Name | Range | Default | Notes |
|----|------|-------|---------|-------|
| 0 | TEMPO | [-1.58496, 3.58496] | 1.0 | log2(BPM/60); default=1 is 120 BPM |
| 1 | RUN | [0, 1] | 0 | 0=stopped, 1=running |
| 2 | MULT | [1, 16] | 1 | Integer multiplier for MULT output |

**TEMPO formula:** `TEMPO = log2(BPM / 60)`
Examples: 60 BPM = 0.0, 120 BPM = 1.0, 128 BPM ≈ 1.0948, 140 BPM ≈ 1.2224

### Inputs (verified from registry.py / manual)

| ID | Name | Purpose |
|----|------|---------|
| 0 | RUN | Gate: high starts clock, low stops it |
| 1 | SYNC | Sync to external clock |

### Outputs (verified)

| ID | Name | Type | Purpose |
|----|------|------|---------|
| 0 | BASE | CLOCK | Master rate (one pulse per beat) |
| 1 | MULT | CLOCK | BASE rate * MULT param |

> **Port ID note:** Input/output IDs 0 and 1 are taken from registry.py which cites the
> Substation manual. They have not been independently confirmed by empirical port-order
> inspection. Treat as best-effort; verify in Rack if behavior is unexpected.

### Typical connections

- `MULT` output (with `MULT=4`) -> sequencer CLOCK for 16th notes at the base BPM
- `BASE` output -> sequencer CLOCK for quarter notes
- Set `RUN=1` in params at build time to auto-start on patch open

---

## Envelopes

**Model:** `SlimeChild-Substation-Envelopes`
**Graph class:** `SubstationEnvelopesNode` (ControllerNode)
**Purpose:** Dual semi-interruptable AD envelopes (no sustain stage); HOLD mode converts to AR.

### Params (verified, v2.2.6)

| ID | Name | Range | Default | Notes |
|----|------|-------|---------|-------|
| 0 | EG1_ATTACK | [-3, 1] | -1.0 | Log scale (seconds); -3 ≈ very fast, 1 ≈ slow |
| 1 | EG1_DECAY | [-3, 1] | -1.0 | Log scale (seconds) |
| 2 | EG2_ATTACK | [-3, 1] | -1.0 | Same scale as EG1 |
| 3 | EG2_DECAY | [-3, 1] | -1.0 | Same scale as EG1 |
| 4 | HOLD | [0, 1] | 0 | 0=AD (trigger), 1=AR (gate, holds while high) |
| 5 | TRIGGER | [0, 1] | 0 | Manual trigger button (momentary) |

**Attack/Decay practical values:**
- `-5` (used in patches): extremely percussive (faster than the official -3 min -- clamp at -3)
- `-3`: very fast, punchy (~8ms)
- `-1`: moderate (~200ms)
- `0`: slow (~1s)
- `1`: very slow (~2s)

> Note: `subzero.py` sets `EG1_ATTACK=-5` which is below the -3 minimum. The param will
> clamp to -3 in practice. Use -3 for the fastest available attack.

### Inputs (verified from registry.py)

| ID | Name | Purpose |
|----|------|---------|
| 0 | TRIG1 / GATE1 | Trigger or gate for EG1 |
| 1 | TRIG2 / GATE2 | Trigger or gate for EG2 |

**Required by graph:** TRIG1 (input 0) must be connected for `patch_proven`.

### Outputs (verified)

| ID | Name | Type | Purpose |
|----|------|------|---------|
| 0 | ENV1 | CV | Envelope 1 output (0-10V) |
| 1 | ENV2 | CV | Envelope 2 output (0-10V) |

> **Port ID note:** Input IDs 0/1 are from registry.py (manual-cited). Not empirically
> confirmed by port-order inspection.

### Typical connections

- Sequencer GATE/TRIG -> TRIG1 and TRIG2 (same source is fine, wired in both patches)
- ENV1 -> VCA CV (amplitude envelope)
- ENV2 -> Filter FM (filter sweep)
- `HOLD=0` for percussive (trigger), `HOLD=1` for sustained (gate)

---

## Filter

**Model:** `SlimeChild-Substation-Filter`
**Graph class:** `SubstationFilterNode` (AudioProcessorNode)
**Purpose:** Physically-modelled 24dB/oct ladder lowpass filter with FM CV input.

### Params (verified, v2.2.6)

| ID | Name | Range | Default | Notes |
|----|------|-------|---------|-------|
| 0 | FREQ | [0, 9.96578] | 4.98289 | Log-Hz units; default ≈ mid-range |
| 1 | RES | [0, 1.2] | 0 | Resonance; above 1.0 enters self-oscillation |
| 2 | FM | [-1, 1] | 0 | FM attenuverter; scales the FM CV input |

**FREQ practical values:**
- `0` = ~1 Hz (nearly closed)
- `1.5` = ~3 Hz (very dark, used in subzero.py)
- `3.5` = ~45 Hz (dark, used in stranger_things.py)
- `4.98` = default mid-range (~1kHz)
- `9.97` = maximum (~20kHz, fully open)

**FM attenuverter behavior:** FM param gates the FM input; set FM != 0 when connecting
envelope to FM input, or the CV has no effect. This is enforced by `_port_attenuators`
in the graph: connecting port 1 (FM input) requires param 2 (FM Amount) to be set.

### Inputs (verified from registry.py / manual)

| ID | Name | Purpose |
|----|------|---------|
| 0 | VOCT / V/OCT | Pitch tracking (1V/oct); shifts cutoff frequency |
| 1 | FM | FM CV input (scaled by FM param attenuverter) |
| 2 | IN | Audio input |

**Audio route:** IN (2) -> OUT (0)

### Outputs (verified)

| ID | Name | Type | Purpose |
|----|------|------|---------|
| 0 | OUT | audio | Filtered audio |

> **Port ID note:** Input IDs from registry.py (manual-cited). Not empirically confirmed.

### Typical connections

- Mixer OUT -> Filter IN (2)
- Envelopes ENV2 -> Filter FM (1); set FM param to non-zero (e.g. 0.5-0.6)
- Quantizer OUT -> Filter VOCT (0) for pitch-tracked cutoff (optional)

---

## VCA

**Model:** `SlimeChild-Substation-VCA`
**Graph class:** `SubstationVCANode` (AudioProcessorNode)
**Purpose:** Simple linear VCA controlled by CV input.

### Params (verified, v2.2.6)

| ID | Name | Range | Default | Notes |
|----|------|-------|---------|-------|
| 0 | LEVEL | [0, 1] | 1.0 | Static level -- **defaults to 1.0 (fully open)**. Set `LEVEL=0` in the patch for envelope-controlled use. **Known quirk: module resets LEVEL to 1.0 on patch load, overwriting the saved value. Must be manually set to 0 in the GUI each time the patch is opened.** |

### Inputs (verified from registry.py)

| ID | Name | Purpose |
|----|------|---------|
| 0 | CV | Amplitude CV (0-10V scales output 0-100%) |
| 1 | IN | Audio input |

**Audio route:** IN (1) -> OUT (0)
**Required by graph:** CV (input 0) must be connected for `patch_proven`.

### Outputs (verified)

| ID | Name | Type | Purpose |
|----|------|------|---------|
| 0 | OUT | audio | Amplitude-modulated audio |

> **Port ID note:** Input IDs from registry.py. Not empirically confirmed by port-order
> inspection.

### Typical connections

- Filter OUT -> VCA IN (1)
- Envelopes ENV1 -> VCA CV (0)
- VCA OUT -> AudioInterface2 IN_L and IN_R (same cable to both)

---

## Mixer

**Model:** `SlimeChild-Substation-Mixer`
**Graph class:** `SubstationMixerNode` (AudioMixerNode)
**Purpose:** 3-channel saturating mixer with per-channel CV modulation and chain I/O.

### Params (verified, v2.2.6)

| ID | Name | Range | Default | Notes |
|----|------|-------|---------|-------|
| 0 | LEVEL1 / CH1_LEVEL | [0, 1] | 0 | Channel 1 level |
| 1 | LEVEL2 / CH2_LEVEL | [0, 1] | 0 | Channel 2 level |
| 2 | LEVEL3 / CH3_LEVEL | [0, 1] | 0 | Channel 3 level |
| 3 | MOD1 / CH1_MOD | [-1, 1] | 0 | Channel 1 CV attenuverter |
| 4 | MOD2 / CH2_MOD | [-1, 1] | 0 | Channel 2 CV attenuverter |
| 5 | MOD3 / CH3_MOD | [-1, 1] | 0 | Channel 3 CV attenuverter |
| 6 | MIX / MIX_LEVEL | [0, 1] | 1 | Master mix output level |
| 7 | CHAIN_GAIN | [0, 1] | 1 | Gain applied to CHAIN input |
| 8 | DRIVE | [0, 1] | 0 | Saturation drive amount |

**Channel level defaults are 0** -- always set LEVEL1/2/3 explicitly in patches.

### Inputs (verified from registry.py)

| ID | Name | Purpose |
|----|------|---------|
| 0 | IN1 / CH1 | Channel 1 audio |
| 1 | IN2 / CH2 | Channel 2 audio |
| 2 | IN3 / CH3 | Channel 3 audio |
| 3 | CV1 | Channel 1 level CV |
| 4 | CV2 | Channel 2 level CV |
| 5 | CV3 | Channel 3 level CV |
| 6 | CHAIN | Chain audio input (from previous mixer) |
| 7 | LEVEL | Master level CV |

**Audio inputs (graph):** IN1 (0), IN2 (1), IN3 (2)

### Outputs (verified)

| ID | Name | Type | Purpose |
|----|------|------|---------|
| 0 | CHAIN | audio | Pre-master chain output (for daisy-chaining mixers) |
| 1 | OUT | audio | Main mix output |

> **Port ID note:** Input and output IDs from registry.py. Not empirically confirmed.

### Typical connections

- SubOscillator BASE -> Mixer IN1 (0)
- SubOscillator SUB1 -> Mixer IN2 (1)
- SubOscillator SUB2 -> Mixer IN3 (2)
- Mixer OUT (1) -> Filter IN
- Set LEVEL1/2/3 to blend root vs. subharmonic content (e.g. 0.9/0.4/0.2 for melody clarity)
- DRIVE 0.1-0.2 adds warmth; higher values saturate

---

## Quantizer

**Model:** `SlimeChild-Substation-Quantizer`
**Graph class:** `SubstationQuantizerNode` (ControllerNode)
**Purpose:** Maps free 1V/oct CV to the nearest note in a selected scale.

### Params (verified, v2.2.6)

| ID | Name | Range | Default | Notes |
|----|------|-------|---------|-------|
| 0 | TEMPERAMENT | [0, 1] | 0 | TODO: exact meaning of 0/1 values unverified |
| 1 | SCALE | [0, 1] | 0 | TODO: scale selection encoding unverified (likely enum stepped) |
| 2 | ROOT | [0, 11] | 0 | Root note in semitones (0=C, 5=F, 7=G, 9=A, etc.) |
| 3 | OCTAVE | [-4, 4] | 0 | Octave offset applied to output |
| 4 | TRANSPOSE | [0, 1] | 0 | TODO: exact meaning and range unverified |

> **TEMPERAMENT and SCALE encoding is unverified.** The discovered cache gives ranges
> [0,1] for both, suggesting they may be stepped enums with values selectable only via the
> GUI. Do not rely on setting these programmatically without empirical confirmation.
> TRANSPOSE range [0,1] is also suspect for a transpose function -- verify before use.

### Inputs (verified from registry.py)

| ID | Name | Purpose |
|----|------|---------|
| 0 | ROOT | CV override for root note |
| 1 | OCT | CV offset for octave |
| 2 | IN | 1V/oct CV input to quantize |

> **Port ID note:** Input IDs from registry.py (manual-cited). Not empirically confirmed.

### Outputs (verified)

| ID | Name | Type | Purpose |
|----|------|------|---------|
| 0 | OUT | CV | Quantized 1V/oct output |

### Typical connections

- Sequencer CV -> Quantizer IN (2)
- Quantizer OUT (0) -> SubOscillator VOCT (0)
- Set ROOT to desired key (0=C, 5=F, 7=G, 9=A, 11=B)
- Scale selection must be configured in the GUI if SCALE encoding is unknown

---

## SubOscillator

**Model:** `SlimeChild-Substation-SubOscillator`
**Graph class:** `SubstationSubOscillatorNode` (AudioSourceNode)
**Purpose:** Oscillator with a main output and two independent sub-harmonic outputs at integer frequency divisions.

### Params (verified, v2.2.6)

| ID | Name | Range | Default | Notes |
|----|------|-------|---------|-------|
| 0 | BASE_FREQ | [-48, 48] | 0 | Pitch offset in semitones from VOCT input |
| 1 | WAVEFORM | [0, 2] | 2 | 0=sine(?), 1=saw(?), 2=square(?) -- exact waveform mapping unverified |
| 2 | SUBDIV1 | [1, 16] | 1 | SUB1 = base_freq / SUBDIV1 |
| 3 | SUBDIV2 | [1, 16] | 1 | SUB2 = base_freq / SUBDIV2 |
| 4 | PWM | [0, 1] | 0.5 | Pulse width (relevant when square wave selected) |
| 5 | DETUNE | [-2, 2] | 0 | Fine detune in semitones |

> **WAVEFORM value-to-waveform mapping is unverified.** Both patches use WAVEFORM=0 (sine
> for stranger_things.py) and WAVEFORM=1 (saw for subzero.py), but this is patch author
> intent, not confirmed mapping. Verify in Rack before relying on specific values.

**Subdivision examples:**
- SUBDIV1=2, SUBDIV2=4: SUB1 is one octave below, SUB2 is two octaves below
- SUBDIV1=3, SUBDIV2=5: creates minor seventh subharmonics (non-octave intervals)
- SUBDIV1=1: SUB1 = BASE (no subdivision)

### Inputs (verified from registry.py / manual)

| ID | Name | Purpose |
|----|------|---------|
| 0 | VOCT / V/OCT | 1V/oct pitch CV |
| 1 | SUB1 | CV for dynamic subdivision 1 amount |
| 2 | SUB2 | CV for dynamic subdivision 2 amount |
| 3 | PWM | PWM CV |

> **Port ID note:** Input IDs from registry.py which cites the Substation manual page
> for SubOscillator. Treated as verified; double-check if SUB1/SUB2 CV behaves unexpectedly.

### Outputs (verified)

| ID | Name | Type | Purpose |
|----|------|------|---------|
| 0 | BASE | audio | Main oscillator output |
| 1 | SUB1 | audio | Sub-harmonic 1 (freq / SUBDIV1) |
| 2 | SUB2 | audio | Sub-harmonic 2 (freq / SUBDIV2) |

### Typical connections

- Quantizer OUT -> SubOscillator VOCT (0)
- SubOscillator BASE (0) -> Mixer IN1
- SubOscillator SUB1 (1) -> Mixer IN2
- SubOscillator SUB2 (2) -> Mixer IN3
- Blend in Mixer: typically lower levels for SUB1/SUB2 than BASE

---

## PolySeq

**Model:** `SlimeChild-Substation-PolySeq`
**Graph class:** `SubstationPolySeqNode` (ControllerNode)
**Purpose:** 3-sequence polyrhythm sequencer (sequences A, B, C) with 4 independently-clocked rhythmic dividers and a routing matrix.

### Params (verified, v2.2.6)

Each sequence has 4 steps; params 0-11 are step values grouped A (0-3), B (4-7), C (8-11).

| ID | Name | Range | Default |
|----|------|-------|---------|
| 0-3 | A1, A2, A3, A4 | [-1, 1] | 0 | Sequence A step values |
| 4-7 | B1, B2, B3, B4 | [-1, 1] | 0 | Sequence B step values |
| 8-11 | C1, C2, C3, C4 | [-1, 1] | 0 | Sequence C step values |
| 12-15 | DIV1-DIV4 | [1, 16] | 1 | Rhythm divider rates |
| 16-19 | DIV1_A - DIV4_A | [0, 1] | 0 | Routing: divider N feeds sequence A |
| 20-23 | DIV1_B - DIV4_B | [0, 1] | 0 | Routing: divider N feeds sequence B |
| 24-27 | DIV1_C - DIV4_C | [0, 1] | 0 | Routing: divider N feeds sequence C |
| 28-30 | RANGE_A, RANGE_B, RANGE_C | [0, 2] | 1 | Output voltage range per sequence |
| 31 | SUM_MODE | [0, 1] | 0 | 0=replace, 1=sum (divider steps sum when multiple fire) |
| 32 | RESET | [0, 1] | 0 | Reset button |
| 33 | NEXT | [0, 1] | 0 | Manual advance button |
| 34 | STEPS | [1, 8] | 4 | Steps per sequence (1-8; default 4) |

> **Routing matrix behavior (params 16-27):** Each DIV_X_Y param is a binary toggle
> (0=disconnected, 1=connected). A divider can feed multiple sequences simultaneously.
> At least one DIV->sequence routing must be enabled for a sequence to advance.

### Inputs (verified from registry.py / manual)

| ID | Name | Purpose |
|----|------|---------|
| 0 | CLOCK | Master clock input |
| 1 | RESET | Reset all sequences to step 1 |
| 2 | DIV1 | CV for divider 1 rate |
| 3 | DIV2 | CV for divider 2 rate |
| 4 | DIV3 | CV for divider 3 rate |
| 5 | DIV4 | CV for divider 4 rate |

**Required by graph:** CLOCK (input 0) must be connected for `patch_proven`.

> **Port ID note:** DIV CV input IDs (2-5) are from registry.py with explicit "best-effort"
> comment. The CLOCK and RESET IDs (0, 1) are cited from the Substation manual and treated
> as verified. Verify DIV CV inputs empirically before use.

### Outputs (verified from registry.py / manual)

| ID | Name | Type | Purpose |
|----|------|------|---------|
| 0 | TRIG1 / TRIG_A | GATE | Trigger for sequence A advance events |
| 1 | TRIG2 / TRIG_B | GATE | Trigger for sequence B advance events |
| 2 | TRIG3 / TRIG_C | GATE | Trigger for sequence C advance events |
| 3 | TRIG4 | GATE | Fourth trigger output (purpose unverified) |
| 4 | SEQ_A / A | CV | Sequence A current step value |
| 5 | SEQ_B / B | CV | Sequence B current step value |
| 6 | SEQ_C / C | CV | Sequence C current step value |

> **Output IDs note:** Registry comment states "DIV CV inputs and exact output indices are
> best-effort; verify in Rack if needed." TRIG4 (output 3) purpose is unverified -- it
> may be a combined or end-of-cycle trigger. Do not rely on TRIG4 without verification.

### Typical connections

- Clock MULT -> PolySeq CLOCK (0)
- PolySeq SEQ_A (4) -> Quantizer IN; TRIG_A (0) -> Envelopes TRIG1
- Multiple sequences can drive independent voices (A->voice1, B->voice2, C->voice3)
- Must enable at least one DIV->sequence routing param (e.g. `DIV1_A=1`) or sequences won't advance

---

## Summary: Port IDs by Confidence Level

### Verified (registry.py cites official manual or empirically confirmed)

| Module | Verified ports |
|--------|---------------|
| SubOscillator | All inputs (0-3), all outputs (0-2) -- manual page cited |
| PolySeq | CLOCK(0), RESET(1) inputs; all 7 outputs -- manual page cited |
| Filter | Audio route IN(2)->OUT(0) confirmed by graph |
| VCA | Audio route IN(1)->OUT(0) confirmed by graph |
| Mixer | Audio inputs IN1(0)/IN2(1)/IN3(2), outputs CHAIN(0)/OUT(1) confirmed by graph |

### Best-effort (registry.py, manual-cited, not independently confirmed)

| Module | Unverified ports | Risk |
|--------|-----------------|------|
| Clock | All inputs (RUN=0, SYNC=1), outputs (BASE=0, MULT=1) | Low -- simple 2-in/2-out module |
| Envelopes | All inputs (TRIG1=0, TRIG2=1), outputs (ENV1=0, ENV2=1) | Low -- used successfully in multiple patches |
| Filter | VOCT(0) and FM(1) inputs | Low -- consistent with standard VCF convention |
| VCA | CV(0) input | Low -- used successfully in multiple patches |
| Mixer | CV1-3(3-5), CHAIN(6), LEVEL(7) inputs | Medium -- only audio inputs confirmed in use |
| Quantizer | All inputs (ROOT=0, OCT=1, IN=2) | Low for IN(2); medium for ROOT/OCT |
| PolySeq | DIV1-4 CV inputs (2-5), TRIG4 output (3) | Medium -- marked best-effort in registry |

### Semantically unverified (param encoding unknown)

| Module | Param | Issue |
|--------|-------|-------|
| Quantizer | TEMPERAMENT (0) | Value encoding unknown (0=ET?) |
| Quantizer | SCALE (1) | Enum encoding unknown; range [0,1] suspicious for a scale selector |
| Quantizer | TRANSPOSE (4) | Range [0,1] unexpected for a transpose function |
| SubOscillator | WAVEFORM (1) | 0/1/2 to waveform shape mapping unverified |

---

## Plugin and Version Info

- Plugin slug: `SlimeChild-Substation`
- All data above: v2.2.6
- Discovered cache location: `vcvpatch/discovered/SlimeChild-Substation/<Model>/2.2.6.json`
- All eight modules are introspectable at v2.2.6
