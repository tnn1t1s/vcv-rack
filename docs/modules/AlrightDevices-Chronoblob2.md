# AlrightDevices / Chronoblob2

Stereo tape-delay effect with CV-controllable time, feedback, and mix.

**Plugin:** `AlrightDevices`  **Model:** `Chronoblob2`
**Graph node class:** `Chronoblob2Node` (AudioProcessorNode)
**Discovered cache:** `vcvpatch/discovered/AlrightDevices/Chronoblob2/2.1.0.json`

---

## Params

All IDs verified by `rack_introspect` against plugin version 2.1.0.

> **Warning:** The discovered param IDs do NOT match the registry.py name-to-ID mapping.
> The discovered file is the ground truth. The registry.py aliases use different names
> for some params. The table below uses discovered IDs; the registry.py name column
> shows what `pb.module()` accepts.

| Discovered name | ID | Range | Default | Registry.py alias |
|-----------------|----|-------|---------|-------------------|
| Feedback | 0 | 0..1 | 0.5 | `FEEDBACK` |
| Delay Time | 1 | 0..1 | 0.5 | `TIME` |
| Dry/Wet | 2 | 0..1 | 0.5 | `MIX` |
| Feedback CV (attenuverter) | 3 | -1..1 | 0 | (no registry alias -- TODO) |
| L Delay Time CV (attenuverter) | 4 | -1..1 | 0 | (no registry alias -- TODO) |
| R Delay Time CV (attenuverter) | 5 | -1..1 | 0 | (no registry alias -- TODO) |
| Dry/Wet CV (attenuverter) | 6 | -1..1 | 0 | (no registry alias -- TODO) |
| Loop | 7 | 0..1 | 0 | `LOOP` |
| Time Modulation Mode | 8 | 0..1 | 0 | `SLIP_MODE` (registry name differs) |
| Delay Mode | 9 | 0..1 | 0 | `PING_PONG` (registry name differs) |

**Registry.py vs discovered mismatch note:** The registry.py entries `TIME=0`, `FEEDBACK=1`,
`MIX=2`, `SLIP=3`, `SLIP_MODE=4`, `RATIO=5`, `PING_PONG=6` do not match the discovered IDs
(Feedback=0, Delay Time=1, Dry/Wet=2). Use the discovered IDs (above) when setting params
directly. The registry aliases `FEEDBACK`, `TIME`, `MIX`, `LOOP` map to the wrong IDs in
registry.py -- **TODO: registry.py needs correction for Chronoblob2.**

For safe use, set only: `FEEDBACK` (target id 0), `TIME` (target id 1), `MIX` (target id 2)
by numeric ID rather than by name until the registry is corrected.

---

## Inputs

IDs from registry.py (port order is separate from param order and is consistent).

| Name | ID | Signal | Notes |
|------|----|--------|-------|
| `TIME_CV` | 0 | CV | Delay time CV. Attenuverter param id 4 (L) and 5 (R) must be opened. |
| `FEEDBACK_CV` | 1 | CV | Feedback CV. Attenuverter param id 3 must be opened. |
| `MIX_CV` | 2 | CV | Dry/Wet CV. Attenuverter param id 6 must be opened. |
| `SLIP_CV` | 3 | CV | Slip CV (TODO: confirm port exists). |
| `RATIO_CV` | 4 | CV | Ratio CV (TODO: confirm port exists). |
| `IN_L` / `L` | 5 | AUDIO | Left audio input. |
| `IN_R` / `R` | 6 | AUDIO | Right audio input. |
| `CLOCK` | 7 | CLOCK | External clock for tempo-sync'd delay time. |

---

## Outputs

| Name | ID | Signal | Notes |
|------|----|--------|-------|
| `OUT_L` / `L` | 0 | AUDIO | Left audio output (wet + dry). |
| `OUT_R` / `R` | 1 | AUDIO | Right audio output. |

---

## Graph behavior

`Chronoblob2Node` is an `AudioProcessorNode`. Audio routes: `IN_L (5) -> OUT_L (0)`,
`IN_L (5) -> OUT_R (1)`, `IN_R (6) -> OUT_L (0)`, `IN_R (6) -> OUT_R (1)`.
No required CV inputs -- the delay runs without any CV patched.

---

## Typical patch role

Insert in the audio path after the main mix, before the reverb or final output.

```python
delay = pb.module("AlrightDevices", "Chronoblob2",
                  FEEDBACK=0.5, MIX=0.35)
pb.cable(vca, "OUT", delay, "IN_L")
pb.cable(delay, "OUT_L", reverb, "IN_L")
pb.cable(delay, "OUT_R", reverb, "IN_R")
```

---

## Notes

- Running mono-in: patch the single source to `IN_L` only. `OUT_L` and `OUT_R` both carry signal.
- `CLOCK` input enables beat-synced delay; leave unpatched for free-running time set by the TIME param.
- The PING_PONG / Delay Mode param (id 9) switches between normal and ping-pong stereo delay.
- The LOOP param (id 7) enables loop/freeze mode (delays keep repeating indefinitely at full feedback).
- **Registry.py param IDs for Chronoblob2 are incorrect** (TIME/FEEDBACK ordering is swapped vs discovered). Use numeric IDs directly for now. TODO: fix registry.py.
