# AlrightDevices / Chronoblob2

Stereo tape-delay effect with CV-controllable time, feedback, and mix.

**Plugin:** `AlrightDevices`  **Model:** `Chronoblob2`
**Graph node class:** `Chronoblob2Node` (AudioProcessorNode)
**Discovered cache:** `vcvpatch/discovered/AlrightDevices/Chronoblob2/2.1.0.json`

---

## Params

All IDs verified by `rack_introspect` against plugin version 2.1.0.

The discovered file is the product truth for this module's param surface. Older
prompt/config folklore used shorthand names like `TIME`, `FEEDBACK`, `MIX`,
and `LOOP`; treat those as historical notes, not as the authoritative surface.

| Param name | ID | Range | Default | Historical shorthand |
|------------|----|-------|---------|----------------------|
| Feedback | 0 | 0..1 | 0.5 | `FEEDBACK` |
| Delay Time | 1 | 0..1 | 0.5 | `TIME` |
| Dry/Wet | 2 | 0..1 | 0.5 | `MIX` |
| Feedback CV | 3 | -1..1 | 0 | — |
| L Delay Time CV | 4 | -1..1 | 0 | — |
| R Delay Time CV | 5 | -1..1 | 0 | — |
| Dry/Wet CV | 6 | -1..1 | 0 | — |
| Loop | 7 | 0..1 | 0 | `LOOP` |
| Time Modulation Mode | 8 | 0..1 | 0 | `SLIP_MODE` |
| Delay Mode | 9 | 0..1 | 0 | `PING_PONG` |

---

## Inputs

Current metadata surface:

| Name | ID | Signal | Notes |
|------|----|--------|-------|
| `L_Delay_Time_CV` | 0 | CV | Left delay time CV. |
| `Feedback_CV` | 1 | CV | Feedback CV. |
| `Mix_CV` | 2 | CV | Dry/Wet CV. |
| `Left` | 5 | AUDIO | Left audio input. |
| `Right_Return` | 6 | AUDIO | Right audio input / return. |
| `Sync_Trigger` | 7 | CLOCK | External sync trigger. |

---

## Outputs

| Name | ID | Signal | Notes |
|------|----|--------|-------|
| `Left` | 0 | AUDIO | Left audio output (wet + dry). |
| `Right_Send` | 1 | AUDIO | Right audio output / send. |

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
- Use the exact param names and IDs from the table above when setting values programmatically.
