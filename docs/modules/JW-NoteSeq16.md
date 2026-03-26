# JW-Modules / NoteSeq16

16-step grid sequencer where rows represent pitches and columns represent steps; outputs polyphonic V/OCT and GATE signals with one channel per active cell in the current column.

**Plugin:** `JW-Modules`  **Model:** `NoteSeq16`
**Graph node class:** `NoteSeq16Node` (ControllerNode)
**Discovered cache:** `vcvpatch/discovered/JW-Modules/NoteSeq16/2.0.31.json`

---

## Params

All IDs verified by `rack_introspect` against plugin version 2.0.31.

| Discovered name | ID | Range | Default | Registry.py alias | Notes |
|-----------------|----|-------|---------|-------------------|-------|
| Length | 0 | 1..16 | 16 | `LENGTH` | Number of active steps. |
| Play Mode | 1 | 0..4 | 0 | `PLAY_MODE` | 0=forward loop, 1=backward, 2=forward/backward, 3=backward/forward, 4=random. |
| Clear | 2 | 0..1 | 0 | `CLEAR` | Clears all active cells (momentary button). |
| Random Trigger | 3 | 0..1 | 0 | `RND_TRIG` | Triggers a random fill (momentary). |
| Random Amount | 4 | 0..1 | 0.1 | `RND_AMT` | Controls density of random fill. |
| Scale | 5 | 0..17 | 11 | `SCALE` | Scale quantization index. Default 11 = chromatic. |
| Root Note | 6 | 0..11 | 0 | `NOTE` | Root note for scale (0=C, 11=B). |
| Octave | 7 | -5..7 | 0 | `OCTAVE` | Global octave offset. |
| (unnamed) | 8 | 0..1 | 0 | `LOW_HIGH` | TODO: name not provided by rack_introspect. Likely Low/High range toggle. |
| Drum Mode | 9 | 0..1 | 0 | `INCLUDE_INACTIVE` | Discovered name is "Drum Mode"; registry alias is `INCLUDE_INACTIVE`. Function unclear -- TODO. |
| Start | 10 | 0..255 | 0 | `START` | Starting step offset. |
| Follow Playhead | 11 | 0..1 | 0 | `FOLLOW` | Scrolls display to follow current step. |

**Note on grid cell params:** The individual step cells (which pitches are active per column)
are stored as module state, not as rack params. They cannot be set via `pb.module()` param
arguments and must be initialized by saving a pre-configured patch or by using `set_param_live`.

---

## Inputs

IDs from registry.py.

| Name | ID | Signal | Notes |
|------|----|--------|-------|
| `CLOCK` | 0 | CLOCK | Clock input. Required (`_required_cv`). Advances the sequencer one step per pulse. |
| `RESET` | 1 | GATE | Reset to step 1. |
| `RND_TRIG` | 2 | GATE | Trigger a random fill. |
| (missing port 3) | 3 | -- | No registry entry for port 3. TODO: verify. |
| `FLIP` | 4 | GATE | Flips the grid vertically. |
| `SHIFT` | 5 | CV | Shifts active cells. |
| `LENGTH` | 6 | CV | CV control of step length. |
| `START` | 7 | CV | CV control of start step. |

---

## Outputs

| Name | ID | Signal | Notes |
|------|----|--------|-------|
| `VOCT` / `POLY_VOCT` | 0 | CV | Polyphonic V/OCT. Channel count = number of active cells in current column. |
| `GATE` / `POLY_GATE` | 1 | GATE | Polyphonic gate. High for each active cell in the current column. |
| `EOC` | 2 | GATE | End-of-cycle pulse. Fires once at the end of a full sequence. |

---

## Graph behavior

`NoteSeq16Node` is a `ControllerNode`. `_required_cv = {0: CLOCK}` -- the CLOCK input
must be connected or the node blocks proof. Output types: port 0 = CV, port 1 = GATE,
port 2 = GATE.

---

## Typical patch role

NoteSeq16 is a melody and gate source. Connect CLOCK from a master clock, V/OCT output to
a VCO or Plaits V/OCT, and GATE output to an envelope/VCA.

```python
seq = pb.module("JW-Modules", "NoteSeq16", LENGTH=8, PLAY_MODE=0, SCALE=11)
pb.cable(clock, "CLK0", seq, "CLOCK")
pb.cable(seq, "VOCT", plaits, "VOCT")
pb.cable(seq, "GATE", adsr, "GATE")
```

For monophonic use, activate exactly one cell per column. Multiple active cells per column
produce polyphonic output, which requires a polyphonic-aware downstream module.

---

## Difference from CountModula/Sequencer16

| Feature | JW-Modules/NoteSeq16 | CountModula/Sequencer16 |
|---------|----------------------|-------------------------|
| Grid type | Rows=pitches, columns=steps (piano-roll) | Linear 16-step CV + gate |
| Polyphony | Polyphonic (multiple notes per step) | Monophonic |
| Gate output | Polyphonic GATE | Separate GATE and TRIG |
| CV output | Polyphonic V/OCT | Monophonic CV and CVI |
| Step values | Grid cells (state, not params) | Per-step CV params (STEP1-16) |
| Typical use | Harmonic/melodic sequences, chord arpeggiation | Monophonic bassline or melody |

---

## Notes

- The step grid cell state is not exposed as rack params; you cannot set which cells are active via `pb.module()`. Pre-configure the grid in a saved patch file.
- Scale quantization (SCALE param) affects the V/OCT output pitch values. Default 11 = chromatic (no quantization).
- EOC output (port 2) fires once per complete loop, useful for triggering events at phrase boundaries.
- Play Mode 4 (random) picks a random step each clock tick -- not the same as a random walk.
