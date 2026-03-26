# CountModula / Sequencer16

## What It Does

Sequencer16 is a 16-step CV + gate sequencer. Each step has an independent pitch CV
value and two independent on/off switches: one for a 1ms trigger pulse (TRIG out) and
one for a held gate (GATE out). This makes it a self-contained 303/606-style module --
one instance handles both pitch and gate pattern without needing a separate gate
sequencer. The step count is CV-addressable, direction is configurable (forward,
reverse, pendulum, random, one-shot variants, voltage-addressed), and the CV range
scales from 1-8V via a panel switch.

---

## Input Ports

Enum: `InputIds` in `SequencerSrc.hpp`. IDs are assigned by enum order.

| ID | Name              | Registry key       | Function |
|----|-------------------|--------------------|----------|
| 0  | RUN_INPUT         | `RUN`              | Gate high = running, low = stopped |
| 1  | CLOCK_INPUT       | `CLOCK`            | Rising edge advances the sequencer |
| 2  | RESET_INPUT       | `RESET`            | Rising edge returns to step 1 |
| 3  | LENGTH_INPUT      | (not in registry)  | CV overrides LENGTH_PARAM (0-10V maps to 1-16 steps) |
| 4  | DIRECTION_INPUT   | (not in registry)  | CV selects direction when DIRECTION_PARAM = "Voltage addressed" |
| 5  | ADDRESS_INPUT     | (not in registry)  | Direct step address CV (used in voltage-addressed mode) |

**Minimum wiring:** CLOCK_INPUT only. Without RUN_INPUT the sequencer runs freely.

---

## Output Ports

Enum: `OutputIds` in `SequencerSrc.hpp`. **The enum order is the source of truth for
port IDs -- NOT the `addOutput()` call order in the widget constructor.** These two
orders differ; see the gotcha section below.

| ID | Name         | Registry key | Function |
|----|--------------|--------------|----------|
| 0  | GATE_OUTPUT  | `GATE`       | Held high for the full duration of active steps (use for ADSR sustain) |
| 1  | TRIG_OUTPUT  | `TRIG`       | 1ms trigger pulse at the start of each active step (use for percussive envelopes) |
| 2  | END_OUTPUT   | `END`        | Single pulse at the end of a one-shot cycle (useless for looping patches) |
| 3  | CV_OUTPUT    | `CV`         | Pitch CV out, 1V/oct |
| 4  | CVI_OUTPUT   | `CVI`        | Inverted pitch CV out |

---

## Params

Param IDs are determined by the `ParamIds` enum, with `ENUMS(X, 16)` macros expanding
to 16 consecutive IDs each.

```
ENUMS(STEP_PARAMS,    16)  ->  ids  0-15   legacy step on/off (dataFromJson compat only)
ENUMS(CV_PARAMS,      16)  ->  ids 16-31   per-step pitch CV  (these are STEP{N} in registry)
LENGTH_PARAM               ->  id  32
DIRECTION_PARAM            ->  id  33
ADDR_PARAM                 ->  id  34
RANGE_SW_PARAM             ->  id  35
HOLD_PARAM                 ->  id  36
ENUMS(TRIGGER_PARAMS, 16)  ->  ids 37-52   per-step trigger on/off
ENUMS(GATE_PARAMS,    16)  ->  ids 53-68   per-step gate on/off
```

### Per-step params (registry names)

| Registry name | Param ID      | Type   | Range    | Function |
|---------------|---------------|--------|----------|----------|
| `STEP{N}`     | 16 + (N-1)    | knob   | 0.0-1.0  | Step pitch CV fraction -- **actual output = STEP × RANGE_SW volts** |
| `TRIG{N}`     | 37 + (N-1)    | switch | 0.0/1.0  | 1 = this step fires TRIG output; 0 = silent |
| `GATE{N}`     | 53 + (N-1)    | switch | 0.0/1.0  | 1 = this step asserts GATE output; 0 = silent |

N runs 1-16.

> **RANGE_SW gotcha (verified empirically):** The CV output is `STEP_value × RANGE_SW`.
> With the default `RANGE_SW=8`, a `STEP` value of `0.5` outputs **4V**, not 0.5V.
> Negative STEP values (e.g. voltages below C4) are clamped to 0 -- the module cannot
> output negative CV.
>
> **Always set `RANGE_SW=1` when targeting 1V/oct notes in the C4-C5 range (0-1V).**
> Then `STEP` values map directly to volts: F4=5/12≈0.417, Ab4=8/12≈0.667, C5=1.0.
> Use a SubOscillator or transposer downstream to shift to the desired register.

### Sequencer-level params

| Registry name | Param ID | Range    | Default | Function |
|---------------|----------|----------|---------|----------|
| `LENGTH`      | 32       | 1.0-16.0 | 16.0    | Active step count |
| `RANGE_SW`    | 35       | 1.0-8.0  | **8.0** | **CV output scale -- output = STEP × RANGE_SW. Set to 1.0 for direct 1V/oct mapping.** |
| (not mapped)  | 33       | 0.0-8.0  | 0.0     | DIRECTION: 0=Forward, 1=Reverse, 2=Pendulum, 3=Random, 4-7=one-shot variants, 8=Voltage addressed |
| (not mapped)  | 34       | 0.0-10.0 | 0.0     | ADDR: direct address offset in voltage-addressed mode |
| (not mapped)  | 36       | 0.0-2.0  | 1.0     | HOLD: 0=Trigger mode, 1=Off, 2=Gate mode (see T/G note below) |

---

## T Mode vs G Mode (HOLD_PARAM)

The HOLD_PARAM (id 36) controls how the sequencer holds CV between steps:

- **Trigger mode (0):** CV output is zeroed between steps; useful when you want sharp
  CV transitions driven by the trigger.
- **Off (1, default):** CV holds the last active step's value until the next active
  step. Most common setting for melodic patches.
- **Gate mode (2):** CV is only non-zero while the step is active (GATE is high). Acts
  as a combined CV+gate.

This is separate from the per-step TRIG/GATE selection. TRIG{N} and GATE{N} determine
*which steps fire*; HOLD_PARAM determines *how CV behaves between those steps*.

---

## Voltage Conventions

- CV output: 1V/oct, C4 = 0V
- With the default RANGE_SW = 8V, `STEP{N}` knob value 0.0 = 0V, 1.0 = 8V
- To target specific pitches, compute: `voltage = octave_offset + semitones/12`
  where octave_offset is relative to C4=0V

```python
# 1V/oct reference (C4 = 0V)
C4  = 0.0
F2  = -2.0 + 5/12   # -1.5833
Ab2 = -2.0 + 8/12   # -1.3333
C3  = -1.0
```

When using a quantizer downstream, the exact STEP{N} value is less critical -- set an
approximate pitch and let the quantizer snap it to scale.

---

## Typical Usage Patterns

### 303-style melodic bassline

```
Clock (x4) -> CLOCK
CV  -> Quantizer -> VCO V/OCT
TRIG -> Envelope TRIG input   (1ms pulse per active step)
Envelope OUT -> VCA CV + Filter FM
```

Set STEP{N} to pitch voltages, TRIG{N}=1 for active steps, TRIG{N}=0 for rests.
Use TRIG output rather than GATE for percussive/303 envelopes.

### ADSR sustain (held notes)

```
GATE -> ADSR gate input
CV   -> VCO V/OCT
```

Set GATE{N}=1 for active steps. GATE stays high for the full clock period, giving
the ADSR time to sustain. Use when notes need sustain rather than re-triggering.

### Dual-mode (TRIG drives envelope, GATE drives filter)

Set both TRIG{N} and GATE{N} per step independently. Connect TRIG to a fast percussive
envelope and GATE to a slower filter sweep envelope.

### Sparse pattern (most steps silent)

Set most TRIG{N}=0, GATE{N}=0. On rest steps, the pitch value is irrelevant -- wire
through a quantizer anyway to avoid CV glitches on the rare case HOLD is in trigger mode.

---

## Key Gotcha: Enum Order vs addOutput() Order

The `addOutput()` calls in the widget constructor appear in this order:

```
GATE_OUTPUT, TRIG_OUTPUT, CV_OUTPUT, CVI_OUTPUT, END_OUTPUT
```

The `OutputIds` enum assigns IDs in this order:

```
GATE_OUTPUT=0, TRIG_OUTPUT=1, END_OUTPUT=2, CV_OUTPUT=3, CVI_OUTPUT=4
```

**END_OUTPUT has enum id 2 but is placed visually on the panel between CV and CVI.**
If you read the widget's `addOutput()` call order, you would conclude CV=2 and END=4.
This is wrong. VCV Rack assigns port IDs by enum order, not by widget call order.

**Always read the enum, never the widget.**

This same principle applies to any VCV Rack module. When in doubt, introspect with
`rack_introspect CountModula Sequencer16` or check the enum in the source header.

---

## Verified Sources

- `vcvpatch/registry.py` lines 842-882 (inline comments document the IDs and rationale)
- `SequencerSrc.hpp` master branch: `countmodula/VCVRackPlugins` on GitHub
- Memory note: `reference_countmodula_seq16_ports.md`
- Working patches: `patches/subzero.py`, `patches/seq16_debug.py`
