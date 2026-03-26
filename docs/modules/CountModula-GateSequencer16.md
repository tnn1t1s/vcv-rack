# CountModula / GateSequencer16

8-track x 16-step gate/trigger sequencer with no CV output; each track produces an independent GATE and TRIG output driven by a 16-step on/off pattern.

**Plugin:** `CountModula`  **Model:** `GateSequencer16`
**Graph node class:** `CountModulaGateSequencer16Node` (ControllerNode)
**Discovered cache:** `vcvpatch/discovered/CountModula/GateSequencer16/2.5.0.json`

---

## Params

All IDs verified by `rack_introspect` against plugin version 2.5.0.

### Step params (128 total)

Step params follow a strict linear layout: Track N, Step S has param ID `(N-1) * 16 + (S-1)`.

| Param name convention | ID formula | Range | Default |
|-----------------------|------------|-------|---------|
| T{N}_S{S} (Track N, Step S) | (N-1)*16 + (S-1) | 0..1 | 0 |

Full track boundaries:

| Track | First step ID | Last step ID |
|-------|--------------|-------------|
| 1 | 0 | 15 |
| 2 | 16 | 31 |
| 3 | 32 | 47 |
| 4 | 48 | 63 |
| 5 | 64 | 79 |
| 6 | 80 | 95 |
| 7 | 96 | 111 |
| 8 | 112 | 127 |

Registry.py names: `T1_S1` through `T1_S16` for track 1, `T2_S1` through `T2_S16` for track 2.
Only track 1 and track 2 aliases are defined in registry.py. For tracks 3-8, use numeric IDs directly.

### Control params

| Discovered name | ID | Range | Default | Registry.py alias | Notes |
|-----------------|----|-------|---------|-------------------|-------|
| Length | 128 | 1..16 | 16 | `LENGTH` | Active step count for all tracks. |
| Track 1 mute | 129 | 0..1 | 0 | (TODO) | Mutes track 1 output. |
| Track 2 mute | 130 | 0..1 | 0 | (TODO) | |
| Track 3 mute | 131 | 0..1 | 0 | (TODO) | |
| Track 4 mute | 132 | 0..1 | 0 | (TODO) | |
| Track 5 mute | 133 | 0..1 | 0 | (TODO) | |
| Track 6 mute | 134 | 0..1 | 0 | (TODO) | |
| Track 7 mute | 135 | 0..1 | 0 | (TODO) | |
| Track 8 mute | 136 | 0..1 | 0 | (TODO) | |
| Direction | 137 | 0..8 | 0 | (TODO) | Playback direction (forward, backward, random, etc.). |
| Address | 138 | 0..10 | 0 | (TODO) | TODO: function unclear. |

---

## Inputs

IDs from registry.py.

| Name | ID | Signal | Notes |
|------|----|--------|-------|
| `CLOCK` | 0 | CLOCK | Clock input. Required (`_required_cv`). Advances all tracks one step per pulse. |
| `RESET` | 1 | GATE | Resets all tracks to step 1. |
| `RUN` | 2 | GATE | Run/stop gate. High = running. |

---

## Outputs

| Name | ID | Signal | Notes |
|------|----|--------|-------|
| `GATE1` | 0 | GATE | Track 1 gate output. High while step is active (held for full clock period). |
| `GATE2` | 1 | GATE | Track 2. |
| `GATE3` | 2 | GATE | Track 3. |
| `GATE4` | 3 | GATE | Track 4. |
| `GATE5` | 4 | GATE | Track 5. |
| `GATE6` | 5 | GATE | Track 6. |
| `GATE7` | 6 | GATE | Track 7. |
| `GATE8` | 7 | GATE | Track 8. |
| `TRIG1` | 8 | GATE | Track 1 trigger output. 1ms pulse per active step. |
| `TRIG2` | 9 | GATE | Track 2. |
| `TRIG3` | 10 | GATE | Track 3. |
| `TRIG4` | 11 | GATE | Track 4. |
| `TRIG5` | 12 | GATE | Track 5. |
| `TRIG6` | 13 | GATE | Track 6. |
| `TRIG7` | 14 | GATE | Track 7. |
| `TRIG8` | 15 | GATE | Track 8. |
| `END` | 16 | GATE | End-of-cycle pulse. Fires once per complete sequence. |

---

## Graph behavior

`CountModulaGateSequencer16Node` is a `ControllerNode`. `_required_cv = {0: CLOCK}` --
CLOCK must be connected or the node blocks proof. All 16 gate/trig outputs (ids 0-15) are
declared as `GATE` type. Output id 16 (END) is not in the `_output_types` dict -- treat as GATE.

---

## Typical patch role

GateSequencer16 provides gate patterns for drum tracks or per-voice envelope triggers.
Combine with Sequencer16 or NoteSeq16 for a pitch+gate voice, or use standalone for
all-gate drum sequences.

```python
gates = pb.module("CountModula", "GateSequencer16",
                  T1_S1=1, T1_S3=1, T1_S5=1, T1_S7=1,  # kick on beats 1,3,5,7
                  T2_S3=1, T2_S7=1,                      # snare on beats 3,7
                  LENGTH=8)
pb.cable(clock, "CLK0", gates, "CLOCK")
pb.cable(gates, "TRIG1", kick, "GATE")
pb.cable(gates, "GATE2", adsr, "GATE")
```

---

## Relationship to CountModula/Sequencer16

| Feature | GateSequencer16 | Sequencer16 |
|---------|-----------------|-------------|
| Tracks | 8 independent gate tracks | 1 track |
| CV output | None | Monophonic CV (pitch) |
| Gate output | GATE1-8 (held) + TRIG1-8 (pulse) | GATE + TRIG |
| Step params | Per-step binary on/off | Per-step CV value (pitch) |
| Typical use | Multi-track drum/rhythm patterns | Melodic or bassline sequencing |

Use GateSequencer16 when you need independent gate patterns across multiple voices.
Use Sequencer16 when you need pitch CV + gate from a single module.

---

## Notes

- Step params default to 0 (off). Set to 1 to activate a step: `T1_S1=1`.
- Only tracks 1-2 have named registry aliases (T1_S1..T1_S16, T2_S1..T2_S16). For tracks 3-8, compute the param ID directly: `id = (track - 1) * 16 + (step - 1)`.
- GATE outputs stay high for the full clock period; TRIG outputs fire a 1ms pulse. Use GATE for ADSR sustain-stage envelopes; use TRIG for percussive (AD) envelopes.
- LENGTH param (id 128) sets the active sequence length for all tracks simultaneously. Per-track length control is not available.
- Mute params (ids 129-136) silence individual track outputs without affecting the step counter.
- The Direction param (id 137, range 0-8) controls playback direction. Value 0 = forward. The full mapping for values 1-8 is TODO.
