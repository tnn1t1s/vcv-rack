# AgentRack: Formal Design Specification

## 1. The Core Insight: Models, Not Modules

A conventional VCV Rack module is designed for a human performer. It has knobs,
jacks, and a panel because a human needs to see, reach, and turn things. Its
parameter scales are musical (log-Hz, log-seconds) because they feel right under
a hand. Its defaults assume a human will configure it interactively.

An AgentRack **model** is designed for a language model acting as a composer.
It has parameters because a model needs to be specified. It has ports because
models need to exchange signals. Its parameter scales are natural (Hz, seconds,
0-1 normalized) because an agent reasons in units, not gestures.

The word "model" is chosen deliberately. In the machine learning sense, each
AgentRack model is a parameterized function:

```
output = model(input; θ)
```

where θ is a set of parameters the agent sets at patch-build time. The agent's
job is not to "tweak knobs" -- it is to **fit parameters** to a musical
specification. This changes how the agent reasons:

| Module thinking (current)     | Model thinking (proposed)               |
|-------------------------------|-----------------------------------------|
| "Set FREQ to 0.417"           | "Pitch target is F4 (0.417V)"           |
| "Set EG1_DECAY to -0.8"       | "Decay target is ~200ms"                |
| "Open FREQ_CV attenuverter"   | Not needed -- CV always active          |
| "Check if port ID is correct" | Port ID is in meta.json, always correct |

---

## 2. Ensemble Architecture

A patch is not a signal chain. It is a **multi-model ensemble**: a set of
models each making a partial estimate of the target sound, whose outputs are
combined to produce the final signal.

Each model is an expert on one musical dimension:

```
Pitch model    → estimates pitch trajectory
Timbre model   → estimates spectral character
Dynamics model → estimates amplitude envelope
Rhythm model   → estimates gate/trigger pattern
Space model    → estimates reverb/delay treatment
```

The agent assembles an ensemble by selecting models and fitting their
parameters. The ensemble is complete when every musical dimension the
specification requires is covered by at least one model.

This is analogous to ensemble methods in ML:
- Each model has a **narrow hypothesis class** (it can only represent certain
  sounds)
- Models are **composable** -- you can swap one out without disturbing others
- The agent can detect **gaps** in the ensemble ("no dynamics model connected")
- **Fitting** is the agent's primary operation, not wiring

### Ensemble completeness check

A patch is provably complete when:
1. Every model's required inputs are connected
2. An audio path exists from at least one model to the output
3. Every musical dimension in the spec is covered

The proof system extends naturally to ensemble coverage rather than just
audio reachability.

---

## 3. Core Model Set (v0.1)

A minimal set of models that can express a wide range of patches. Each is
deliberately narrow. Complexity comes from composition, not from individual
model richness.

### 3.1 Clock

**Role:** Estimates tempo. Outputs a regular pulse stream.

```
params:
  BPM       float  [20, 300]   natural units: beats per minute
  DIVISION  int    [1, 32]     clock division (1 = quarter note)
  SWING     float  [0, 0.5]    swing ratio (0 = straight)

outputs:
  CLOCK    gate   regular pulse at BPM / DIVISION
  RESET    gate   single pulse on start
```

No log scaling. BPM is BPM.

---

### 3.2 Sequence

**Role:** Estimates pitch and gate pattern over N steps.

```
params:
  LENGTH   int    [1, 16]      active step count
  STEP{N}  float  [−5, 5]      pitch in volts (1V/oct, C4 = 0V), N=1..16
  GATE{N}  float  {0, 1}       gate on/off per step, N=1..16

inputs:
  CLOCK    gate   advances step on rising edge
  RESET    gate   returns to step 1

outputs:
  CV       cv     current step pitch (volts)
  GATE     gate   held high for the full step duration
  TRIG     gate   1ms pulse at step start (fires even when GATE=0 for rests)
```

Key differences from Sequencer16:
- STEP values are in **volts directly**, not a 0-1 fraction scaled by RANGE_SW
- GATE and TRIG are always available; no per-step TRIG/GATE split
- Enum order == addOutput() order, enforced
- No voltage-addressed mode, no one-shot mode (those are separate models)

---

### 3.3 Voice

**Role:** Estimates a complete monophonic synthesis voice from pitch and gate.
Integrates oscillator, filter, and amplitude envelope in one model.

```
params:
  PITCH    float  [−4, 4]      base pitch offset (octaves, 0 = A4)
  WAVEFORM float  [0, 3]       0=sine, 1=triangle, 2=saw, 3=square
  CUTOFF   float  [20, 20000]  filter cutoff in Hz
  RES      float  [0, 1]       filter resonance (1.0 = self-oscillation)
  ATTACK   float  [0.001, 10]  envelope attack in seconds
  DECAY    float  [0.001, 10]  envelope decay in seconds
  SUSTAIN  float  [0, 1]       envelope sustain level
  RELEASE  float  [0.001, 10]  envelope release in seconds

inputs:
  VOCT     cv     1V/oct pitch (summed with PITCH param, no attenuverter)
  GATE     gate   envelope gate
  CUTOFF   cv     filter cutoff CV in Hz (added to CUTOFF param, always active)
  MORPH    cv     timbre/waveform morph CV (always active)

outputs:
  OUT      audio  filtered, enveloped audio
  ENV      cv     raw envelope output (0-10V, for use by other models)
```

No attenuverters. Every CV input is summed with its param directly. The agent
controls depth by scaling the CV source (via an Attenuate model) rather than
opening a knob on this module.

---

### 3.4 Attenuate

**Role:** Scales a signal by a fixed amount or by a CV-controlled amount.
The explicit "attenuator as a model" -- makes the modulation depth a
first-class parameter rather than a hidden knob inside another module.

```
params:
  SCALE    float  [−1, 1]      static scale factor (default 1.0)
  OFFSET   float  [−10, 10]    DC offset added after scaling

inputs:
  IN       cv/audio  signal to scale
  SCALE    cv        multiplies SCALE param (no attenuverter -- it's turtles)

outputs:
  OUT      same type as IN
```

This is how you control modulation depth explicitly:

```
LFO → Attenuate (SCALE=0.3) → Voice.CUTOFF
```

The agent sets SCALE=0.3 to mean "30% of LFO range". No mystery about why
the LFO isn't doing anything.

---

### 3.5 LFO

**Role:** Estimates a periodic modulation signal.

```
params:
  FREQ     float  [0.001, 100]  frequency in Hz
  SHAPE    float  [0, 3]        0=sine, 1=triangle, 2=saw, 3=square
  PHASE    float  [0, 1]        initial phase offset
  UNIPOLAR int    {0, 1}        0=bipolar (−5 to +5V), 1=unipolar (0 to 10V)

inputs:
  RESET    gate   resets phase to PHASE param

outputs:
  OUT      cv     LFO signal
```

One output. The shape is a param. No need to guess which of six outputs is
the sine wave.

---

### 3.6 Space

**Role:** Estimates the spatial/acoustic environment. Integrates delay and
reverb into one model.

```
params:
  DELAY    float  [0, 2]        delay time in seconds (0 = off)
  FEEDBACK float  [0, 0.99]     delay feedback (0 = single echo)
  REVERB   float  [0, 1]        reverb send amount
  SIZE     float  [0, 1]        reverb room size
  DECAY    float  [0, 1]        reverb decay time (0-1 normalized)
  MIX      float  [0, 1]        wet/dry mix (0 = dry, 1 = fully wet)

inputs:
  IN_L     audio  left input
  IN_R     audio  right input (normalized to IN_L if unpatched)

outputs:
  OUT_L    audio  processed left
  OUT_R    audio  processed right
```

---

### 3.7 Mix

**Role:** Combines ensemble outputs into a final stereo signal.

```
params:
  LEVEL{N} float  [0, 1]        per-channel level, N=1..4
  PAN{N}   float  [−1, 1]       per-channel pan, N=1..4
  MASTER   float  [0, 1]        master output level

inputs:
  IN{N}    audio  per-channel audio, N=1..4
  CV{N}    cv     per-channel level CV (added to LEVEL{N}, always active)

outputs:
  OUT_L    audio  mixed left
  OUT_R    audio  mixed right
```

---

## 4. Meta.json Specification

Every model ships a `meta.json` sidecar in its plugin directory. The agent
reads this at patch-build time. No GitHub source diving, no discovered cache
cache-miss, no guessing.

```json
{
  "plugin":  "AgentRack",
  "model":   "Voice",
  "version": "0.1.0",
  "role":    "monophonic synthesis voice",
  "params": [
    {"id": 0, "name": "PITCH",   "unit": "octaves",  "min": -4,    "max": 4,     "default": 0},
    {"id": 1, "name": "WAVEFORM","unit": "index",    "min": 0,     "max": 3,     "default": 2},
    {"id": 2, "name": "CUTOFF",  "unit": "Hz",       "min": 20,    "max": 20000, "default": 2000},
    {"id": 3, "name": "RES",     "unit": "0-1",      "min": 0,     "max": 1,     "default": 0},
    {"id": 4, "name": "ATTACK",  "unit": "seconds",  "min": 0.001, "max": 10,    "default": 0.01},
    {"id": 5, "name": "DECAY",   "unit": "seconds",  "min": 0.001, "max": 10,    "default": 0.3},
    {"id": 6, "name": "SUSTAIN", "unit": "0-1",      "min": 0,     "max": 1,     "default": 0.7},
    {"id": 7, "name": "RELEASE", "unit": "seconds",  "min": 0.001, "max": 10,    "default": 0.2}
  ],
  "inputs": [
    {"id": 0, "name": "VOCT",   "type": "cv",    "description": "1V/oct pitch, summed with PITCH param"},
    {"id": 1, "name": "GATE",   "type": "gate",  "description": "envelope gate, required"},
    {"id": 2, "name": "CUTOFF", "type": "cv",    "description": "filter cutoff offset in Hz, always active"},
    {"id": 3, "name": "MORPH",  "type": "cv",    "description": "timbre morph 0-1, always active"}
  ],
  "outputs": [
    {"id": 0, "name": "OUT", "type": "audio", "description": "filtered enveloped audio"},
    {"id": 1, "name": "ENV", "type": "cv",    "description": "envelope output 0-10V"}
  ],
  "required_inputs": ["GATE"],
  "ensemble_role":   "pitch + timbre + dynamics"
}
```

The `ensemble_role` field lets the agent check ensemble completeness: is every
musical dimension covered?

---

## 5. What This Changes for the Agent

### Before (current system)

```python
# Agent must know:
# - RANGE_SW exists and defaults to 8 (not 1)
# - FREQ CV needs TIMBRE_ATTENUVERTER=0.55 to do anything
# - Plaits param IDs are off by 1 from the registry
# - addOutput() order ≠ enum order for Sequencer16
# - SlimeChild VCA resets LEVEL to 1.0 on load

seq_params["RANGE_SW"] = 1.0          # gotcha
plaits["TIMBRE_ATTENUVERTER"] = 0.55  # gotcha
# ... 8 more gotchas before sound comes out
```

### After (AgentRack)

```python
# Agent specifies targets in natural units:
clock = model("AgentRack", "Clock",   BPM=128, DIVISION=4)
seq   = model("AgentRack", "Sequence", LENGTH=16,
              STEP1=0.417, STEP2=0.0, STEP3=1.0,  # F4, rest, C5
              GATE1=1, GATE2=0, GATE3=1)
lfo   = model("AgentRack", "LFO",     FREQ=0.07, SHAPE=0, UNIPOLAR=0)
att   = model("AgentRack", "Attenuate", SCALE=0.4)
voice = model("AgentRack", "Voice",   CUTOFF=800, RES=0.7,
              ATTACK=0.005, DECAY=0.2, SUSTAIN=0.5, RELEASE=0.15)
space = model("AgentRack", "Space",   DELAY=0.22, FEEDBACK=0.05,
              REVERB=0.6, SIZE=0.85, MIX=0.45)

# Wiring is minimal and obvious:
chain(clock.CLOCK, seq.CLOCK)
chain(seq.CV,      voice.VOCT)
chain(seq.GATE,    voice.GATE)
chain(lfo.OUT,     att.IN)
chain(att.OUT,     voice.CUTOFF)  # 40% of LFO sweeps the filter
chain(voice.OUT,   space.IN_L)
chain(voice.OUT,   space.IN_R)
chain(space.OUT_L, audio.IN_L)
chain(space.OUT_R, audio.IN_R)
```

No gotchas. No attenuverters to open. No unit conversions. The agent reasons
about the patch in musical terms and the code looks like the spec.

---

## 6. Build Plan

### Phase 1: meta.json infrastructure (no new C++ yet)

1. Extend `rack_introspect` to dump input and output port metadata (names, IDs,
   types) in addition to params. This makes every installed module
   self-describing.
2. Update `populate_cache.py` to write port metadata into `discovered/`.
3. Update `registry.py` to load from `discovered/` for port IDs instead of
   hand-coding them.

This immediately fixes the Bogaudio LFO problem and makes future port ID
bugs impossible.

### Phase 2: AgentRack plugin (C++)

A VCV Rack 2 plugin with the 7 core models above. Each model:
- Has a `meta.json` sidecar
- Enforces enum == addInput/addOutput order with static assertions
- Uses natural parameter units
- Has no attenuverters (CV always summed directly)
- Has no load-time state resets

### Phase 3: agent integration

Update the patch builder to load `meta.json` instead of registry.py for
AgentRack models. Update the proof system to check ensemble completeness
using the `ensemble_role` field. The agent can now describe a patch in
musical terms and the system verifies it is complete.

---

## 7. What We Are Not Building

- A general-purpose VCV Rack module collection. AgentRack has 7 models.
  If you need more, use Bogaudio/Fundamental with verified port IDs.
- A replacement for human-oriented modules. A human would hate this plugin:
  no visual feedback, no performance controls, boring panel.
- A module that reasons about music. The agent reasons. The model computes.
  The distinction is essential (see CLAUDE.md: "keep reasoning in the agent,
  not in tools").
