# Bogaudio Module Reference

Plugin ID: `Bogaudio`
Discovered cache version: `2.6.47`
All param IDs verified by `rack_introspect` -- see `vcvpatch/discovered/Bogaudio/`.

---

## Bogaudio-ADSR

Attack-Decay-Sustain-Release envelope generator with optional linear (vs. exponential) curves.

**Graph node class:** `BogaudioADSRNode` (ControllerNode)
**Required CV:** GATE (input 0) must be connected for `patch_proven`.
**Output type:** CV (0-10V envelope)

### Params (verified, plugin 2.6.47)

| ID | Registry name | Discovered name | Default | Range | Notes |
|----|--------------|-----------------|---------|-------|-------|
| 0 | `ATTACK` | Attack | 0.141421 | 0-1 | Normalized; 0=instant, 1=max |
| 1 | `DECAY` | Decay | 0.316228 | 0-1 | |
| 2 | `SUSTAIN` | Sustain | 1.0 | 0-1 | Normalized level |
| 3 | `RELEASE` | Release | 0.316228 | 0-1 | |
| 4 | `LINEAR` | Linear | 0 | 0-1 | Toggle: 0=exponential, 1=linear |

### Ports

**Inputs:**

| ID | Registry name | Notes |
|----|--------------|-------|
| 0 | `GATE` | Gate signal; required |

**Outputs:**

| ID | Registry names | Notes |
|----|---------------|-------|
| 0 | `ENV`, `OUT` | CV envelope, 0-10V |

### Typical patch role

Used as the amplitude envelope (VCA control) and/or filter envelope (VCF cutoff modulation). Always connect a gate source (sequencer GATE, clock, etc.) to input 0 before connecting ENV to a VCA CV input.

### Gotchas

- Param values are normalized (0-1), not seconds. The actual time is nonlinear.
- Sustain is a level (0-1), not a time.
- With `LINEAR=0` (default), curves are exponential -- natural-sounding for amplitude, can sound slow for filter sweeps.

---

## Bogaudio-LFO

Low-frequency oscillator with six simultaneous waveform outputs and optional slow mode for sub-Hz rates.

**Graph node class:** `BogaudioLFONode` (ControllerNode)
**Required CV:** none
**Output types:** all CV

### Params (verified, plugin 2.6.47)

| ID | Registry name | Discovered name | Default | Range | Notes |
|----|--------------|-----------------|---------|-------|-------|
| 0 | `FREQ` | Frequency | 0 | -5 to 8 | Log-Hz-ish units; see gotchas |
| 1 | `SLOW` | Slow | 0 | 0-1 | Toggle: 1 enables sub-Hz slow mode |
| 2 | `SAMPLE` | Output sampling | 0 | 0-1 | Reduces output sample rate |
| 3 | `PW` | Pulse width | 0 | -1 to 1 | Affects SQUARE output; 0=50% |
| 4 | `OFFSET` | Offset | 0 | -1 to 1 | DC offset added to output |
| 5 | `SCALE` | Scale | 1 | 0-1 | Output amplitude multiplier |
| 6 | `SMOOTH` | Smoothing | 0 | 0-1 | Slew applied to output |

### Ports

**Inputs:**

| ID | Registry names | Notes |
|----|---------------|-------|
| 0 | `SAMPLE` | External sample trigger |
| 1 | `PW` | Pulse width CV |
| 2 | `OFFSET` | Offset CV |
| 3 | `SCALE` | Scale CV |
| 4 | `PITCH`, `VOCT` | V/OCT frequency CV |
| 5 | `RESET` | Phase reset trigger |

**Outputs:**

| ID | Registry names | Notes |
|----|---------------|-------|
| 0 | `SAW`, `RAMP`, `RAMP_UP` | Rising ramp |
| 1 | `RAMP_DOWN` | Falling ramp |
| 2 | `SQR`, `SQUARE` | Square wave |
| 3 | `TRI`, `TRIANGLE` | Triangle |
| 4 | `SIN`, `SINE` | Sine |
| 5 | `STEPPED` | Stepped random (sample-and-hold style) |

### Typical patch role

Modulation source for filter cutoff, VCA tremolo, panning, pitch vibrato. Set `SLOW=1` for slow evolving sweeps. Set `OFFSET` and `SCALE` to shift output to unipolar (0-10V) range for CV inputs that expect positive-only signals.

### Gotchas

- `FREQ` range is -5 to 8 in internal units, not Hz directly. Default 0 produces a moderate LFO rate.
- With `SLOW=0`, the LFO runs at audio-rate-capable speeds at high FREQ values.
- `OFFSET` and `SCALE` in the registry are normalized (-1 to 1). To make output unipolar: set `OFFSET=5.0` and `SCALE=5.0` (as seen in `patches/archive/generate_dub_techno.py`). This shifts the bipolar -5V..+5V wave to 0..+10V range. TODO: verify the exact scaling math against the C++ source.

---

## Bogaudio-Mix4

Four-channel stereo mixer with per-channel level, panning, and mute; plus master level, master mute, and dim.

**Graph node class:** `BogaudioMix4Node` (AudioMixerNode)
**Audio inputs:** ports 2, 5, 8, 11 (IN for CH1-CH4)
**Audio outputs:** ports 0, 1 (OUT_L, OUT_R)

### Params (verified, plugin 2.6.47)

| ID | Registry name | Discovered name | Default | Range | Notes |
|----|--------------|-----------------|---------|-------|-------|
| 0 | `LEVEL1` | Channel 1 level | 0.909091 | 0-1 | ~unity at default |
| 1 | `PAN1` | Channel 1 panning | 0 | -1 to 1 | 0=center |
| 2 | `MUTE1` | Channel 1 mute | 0 | 0-3 | 0=unmuted |
| 3 | `LEVEL2` | Channel 2 level | 0.909091 | 0-1 | |
| 4 | `PAN2` | Channel 2 panning | 0 | -1 to 1 | |
| 5 | `MUTE2` | Channel 2 mute | 0 | 0-3 | |
| 6 | `LEVEL3` | Channel 3 level | 0.909091 | 0-1 | |
| 7 | `PAN3` | Channel 3 panning | 0 | -1 to 1 | |
| 8 | `MUTE3` | Channel 3 mute | 0 | 0-3 | |
| 9 | `LEVEL4` | Channel 4 level | 0.909091 | 0-1 | |
| 10 | `PAN4` | Channel 4 panning | 0 | -1 to 1 | |
| 11 | `MUTE4` | Channel 4 mute | 0 | 0-3 | |
| 12 | `MASTER` | Master level | 0.909091 | 0-1 | |
| 13 | `MASTER_MUTE` | Master mute | 0 | 0-1 | |
| 14 | `DIM` | Master dim | 0 | 0-1 | |

### Ports

**Input port layout:** 3 ports per channel in order (LEVEL_CV, PAN_CV, IN):

| ID | Registry names | Notes |
|----|---------------|-------|
| 0 | `LEVEL_CV1`, `CV1` | Optional level modulation CH1 |
| 1 | `PAN_CV1` | Optional pan modulation CH1 |
| 2 | `IN1` | Audio input CH1 -- wire here |
| 3 | `LEVEL_CV2`, `CV2` | Optional level modulation CH2 |
| 4 | `PAN_CV2` | Optional pan modulation CH2 |
| 5 | `IN2` | Audio input CH2 |
| 6 | `LEVEL_CV3`, `CV3` | Optional level modulation CH3 |
| 7 | `PAN_CV3` | Optional pan modulation CH3 |
| 8 | `IN3` | Audio input CH3 |
| 9 | `LEVEL_CV4`, `CV4` | Optional level modulation CH4 |
| 10 | `PAN_CV4` | Optional pan modulation CH4 |
| 11 | `IN4` | Audio input CH4 |

**Outputs:**

| ID | Registry names | Notes |
|----|---------------|-------|
| 0 | `OUT_L`, `L` | Stereo left |
| 1 | `OUT_R`, `R` | Stereo right |

### Typical patch role

Final or sub-mix stage. Connect VCOs/audio sources to IN1-IN4; connect OUT_L/OUT_R to reverb, delay, or audio interface. Leave LEVEL_CV and PAN_CV unpatched unless dynamic control is needed.

### Gotchas

- MUTE params have range 0-3, not a simple boolean. Use 0 for unmuted.
- Default level (0.909091) is slightly below unity. Raise to 1.0 if you need full level.
- Audio must enter IN ports (2, 5, 8, 11) -- the LEVEL_CV and PAN_CV ports at each channel do not pass audio.

---

## Bogaudio-Pressor

Stereo compressor/gate with sidechain input, CV-controllable threshold, ratio, attack, release, and gain.

**Graph node class:** `PressurNode` (AudioProcessorNode)
**Routes:** IN_L(0) -> OUT_L(1), OUT_R(2); IN_R(4) -> OUT_L(1), OUT_R(2)

### Params (verified, plugin 2.6.47)

| ID | Registry name | Discovered name | Default | Range | Notes |
|----|--------------|-----------------|---------|-------|-------|
| 0 | `THRESHOLD` | Threshold | 0.8 | 0-1 | Normalized; higher = louder threshold |
| 1 | `RATIO` | Ratio | 0.55159 | 0-1 | Normalized compression ratio |
| 2 | `ATTACK` | Attack | 0.316228 | 0-1 | Normalized |
| 3 | `RELEASE` | Release | 0.316228 | 0-1 | Normalized |
| 4 | `OUTPUT_GAIN` | Output gain | 0 | 0-1 | Make-up gain |
| 5 | `INPUT_GAIN` | Input gain | 0 | -1 to 1 | Pre-compression trim |
| 6 | `DETECTOR_MIX` | Detector mix | 0 | -1 to 1 | -1=sidechain only, 0=mix, 1=main |
| 7 | `MODE` | Mode | 1 | 0-1 | 0=gate, 1=compressor |
| 8 | (not in registry) | Detector mode | 1 | 0-1 | TODO: verify meaning |
| 9 | `KNEE` | Knee | 1 | 0-1 | 0=hard knee, 1=soft knee |

**Note:** Param 8 ("Detector mode") is present in the discovered JSON but absent from `registry.py`. Do not use a hardcoded ID of 8 for this param -- use the discovered JSON directly until the registry is updated.

### Ports

**Inputs:**

| ID | Registry names | Notes |
|----|---------------|-------|
| 0 | `IN_L`, `LEFT`, `L` | Main audio left |
| 1 | `SIDECHAIN` | Sidechain audio input |
| 2 | `THRESHOLD_CV` | CV modulation for threshold |
| 3 | `RATIO_CV` | CV modulation for ratio |
| 4 | `IN_R`, `RIGHT`, `R` | Main audio right |
| 5 | `ATTACK_CV` | CV modulation for attack |
| 6 | `RELEASE_CV` | CV modulation for release |
| 7 | `INPUT_GAIN_CV` | CV modulation for input gain |
| 8 | `OUTPUT_GAIN_CV` | CV modulation for output gain |

**Outputs:**

| ID | Registry names | Notes |
|----|---------------|-------|
| 0 | `ENV`, `ENVELOPE` | Gain reduction CV (useful as sidechain signal) |
| 1 | `OUT_L`, `LEFT`, `L` | Processed audio left |
| 2 | `OUT_R`, `RIGHT`, `R` | Processed audio right |

### Typical patch role

Bus compressor at the end of the signal chain (e.g., Mix4 -> Plateau -> Pressor -> AudioInterface2). Also usable as a gate with `MODE=0`. The ENV output can drive other modules as a gain-reduction CV.

### Gotchas

- `MODE=1` (default) is compressor; `MODE=0` is gate -- set this explicitly.
- For mono sources, patch into IN_L only; the routing in `PressurNode` sends IN_L to both OUT_L and OUT_R.
- Param 8 (`DETECTOR_MODE`) is not in the registry; use the discovered JSON ID directly if needed.

---

## Bogaudio-AddrSeq

Eight-step voltage-addressed sequencer: advances on clock, outputs the CV value of the current step.

**Graph node class:** `BogaudioAddrSeqNode` (ControllerNode)
**Required CV:** CLOCK (input 0) must be connected for `patch_proven`.
**Output type:** CV

**Preferred over:** ImpromptuModular/Phrase-Seq-16 and Phrase-Seq-32 (non-introspectable).

### Params (verified, plugin 2.6.47)

| ID | Registry name | Discovered name | Default | Range | Notes |
|----|--------------|-----------------|---------|-------|-------|
| 0 | `STEPS` | Steps | 8 | 1-8 | Active step count |
| 1 | `DIRECTION` | Direction | 1 | 0-1 | TODO: verify 0=backward, 1=forward |
| 2 | `SELECT` | Select step | 0 | 0-7 | Manual step select (overridden by SELECT input) |
| 3 | `OUT1` | Step 1 | 0 | -1 to 1 | Per-step CV value |
| 4 | `OUT2` | Step 2 | 0 | -1 to 1 | |
| 5 | `OUT3` | Step 3 | 0 | -1 to 1 | |
| 6 | `OUT4` | Step 4 | 0 | -1 to 1 | |
| 7 | `OUT5` | Step 5 | 0 | -1 to 1 | |
| 8 | `OUT6` | Step 6 | 0 | -1 to 1 | |
| 9 | `OUT7` | Step 7 | 0 | -1 to 1 | |
| 10 | `OUT8` | Step 8 | 0 | -1 to 1 | |

### Ports

**Inputs:**

| ID | Registry name | Notes |
|----|--------------|-------|
| 0 | `CLOCK` | Clock advance; required |
| 1 | `RESET` | Reset to step 1 |
| 2 | `SELECT` | Voltage-addressed step select (overrides internal counter) |

**Outputs:**

| ID | Registry names | Notes |
|----|---------------|-------|
| 0 | `OUT`, `CV` | CV value of the current step |

### Typical patch role

Melody or chord-root sequencer. Set per-step CV values with OUT1-OUT8 params (range -1 to 1, representing roughly -1V to +1V -- scale to pitch via V/OCT convention). Use CLOCK input from a clock module. RESET input accepts a gate for loop reset.

### Gotchas

- Step CV range is -1 to 1 in normalized units. This is not directly in volts -- TODO: verify exact mapping to V/OCT at the Rack engine level.
- `DIRECTION` param range is 0-1 (binary toggle); exact semantics need verification from C++ source.
- There is no per-step gate output. Pair with a gate sequencer (e.g., CountModula/GateSequencer16) if gates are needed.
- Maximum 8 steps. For longer sequences, chain two AddrSeq modules or use CountModula/Sequencer16.

---

## Bogaudio-SampleHold

Dual sample-and-hold / track-and-hold: on each trigger, captures the input voltage and holds it.

**Graph node class:** `BogaudioSampleHoldNode` (ControllerNode)
**Required CV:** CLOCK1/GATE1 (input 0) must be connected for `patch_proven`.
**Output types:** CV (both outputs)

### Params (verified, plugin 2.6.47)

The discovered JSON and registry have different param layouts. The discovered JSON is authoritative.

**Discovered JSON params:**

| ID | Discovered name | Default | Range | Notes |
|----|-----------------|---------|-------|-------|
| 0 | Trigger 1 | 0 | 0-1 | TODO: verify meaning (may be trigger mode select) |
| 1 | Trigger 2 | 0 | 0-1 | |
| 2 | Track 1 | 0 | 0-1 | TODO: verify meaning (may be track vs. sample mode) |
| 3 | Track 2 | 0 | 0-1 | |
| 4 | Invert 1 | 0 | 0-1 | Inverts output 1 when set to 1 |
| 5 | Invert 2 | 0 | 0-1 | Inverts output 2 when set to 1 |

**Registry param names** (may not match discovered IDs -- verify before use):

| Registry name | Registry ID | Notes |
|--------------|-------------|-------|
| `TRACK1` | 0 | Maps to discovered id 0 "Trigger 1" -- name mismatch; TODO |
| `TRACK2` | 1 | Maps to discovered id 1 "Trigger 2" -- name mismatch; TODO |
| `NOISE_TYPE` | 2 | Not present in discovered JSON; TODO |
| `IN_RANGE` | 3 | Not present in discovered JSON; TODO |
| `IN_OFFSET` | 4 | Not present in discovered JSON; TODO |
| `GATE_BIAS` | 5 | Not present in discovered JSON; TODO |

**The registry param names for this module do not match the discovered JSON.** Use the discovered JSON IDs (0-5) directly until registry.py is corrected.

### Ports

**Inputs:**

| ID | Registry names | Notes |
|----|---------------|-------|
| 0 | `CLOCK1`, `GATE1` | Trigger/clock for channel 1; required |
| 1 | `IN1` | Signal to sample for channel 1 |
| 2 | `CLOCK2`, `GATE2` | Trigger/clock for channel 2 |
| 3 | `IN2` | Signal to sample for channel 2 |

**Outputs:**

| ID | Registry names | Notes |
|----|---------------|-------|
| 0 | `OUT1`, `OUT` | Held CV, channel 1 |
| 1 | `OUT2` | Held CV, channel 2 |

### Typical patch role

Random melody generator: feed an LFO or noise into IN1 and a clock into CLOCK1; OUT1 produces a stepped random voltage that changes at the clock rate. Also useful for quantized random with a downstream quantizer.

### Gotchas

- Registry param names disagree with the discovered JSON names at every ID. Do not rely on the registry for this module's params until the mismatch is resolved.
- Channel 2 inputs (CLOCK2, IN2) are optional -- leave unpatched for single-channel use.
