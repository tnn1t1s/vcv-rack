# ImpromptuModular / Clocked-Clkd

Master clock module with one BPM-locked master output and three ratio-configurable sub-clocks.

**Plugin:** `ImpromptuModular`  **Model:** `Clocked-Clkd`
**Graph node class:** `ClockedNode` (ControllerNode)
**Preferred over:** `ImpromptuModular/Foundry` (non-introspectable)
**Discovered cache:** `vcvpatch/discovered/ImpromptuModular/Clocked-Clkd/2.5.0.json`

---

## Params

All IDs verified by `rack_introspect` against plugin version 2.5.0.

| Name | ID | Range | Default | Notes |
|------|----|-------|---------|-------|
| `RATIO1` | 0 | -34..34 | 0 | CLK1 ratio. 0 = same as master. Positive = faster, negative = slower. See ratio table below. |
| `RATIO2` | 1 | -34..34 | 0 | CLK2 ratio. |
| `RATIO3` | 2 | -34..34 | 0 | CLK3 ratio. |
| `BPM` | 3 | 30..300 | 120 | Master BPM. Set to the literal BPM value (e.g., 126). |
| `RESET` | 4 | 0..1 | 0 | Reset button. |
| `RUN` | 5 | 0..1 | 0 | 0 = stopped, 1 = running. Set to 1 to start clock on patch load. |
| `BPMMODE_DOWN` | 6 | 0..1 | 0 | BPM display mode (prev). Leave at default. |
| `BPMMODE_UP` | 7 | 0..1 | 0 | BPM display mode (next). Leave at default. |
| `DISPLAY_PREV` | 8 | 0..1 | 0 | Display mode (prev). Leave at default. |
| `DISPLAY_NEXT` | 9 | 0..1 | 0 | Display mode (next). Leave at default. |

### Ratio values

The RATIO param uses an internal lookup table, not a direct multiplier. Common values:

| RATIO value | CLK rate relative to master |
|-------------|----------------------------|
| 0 | x1 (same as master) |
| 2 | x2 (double speed / eighth notes if master = quarter notes) |
| 4 | x4 |
| -2 | /2 (half speed) |
| -4 | /4 |

The exact table covers -34..34. Consult the ImpromptuModular source for the full mapping if you need non-power-of-two ratios.

---

## Inputs

IDs from registry.py (cross-referenced against Clkd.cpp enum order).

| Name | ID | Signal | Notes |
|------|----|--------|-------|
| `RESET` | 0 | GATE | External reset trigger. |
| `RUN` | 1 | GATE | External run/stop gate. |
| `BPM_INPUT` | 2 | CV | External BPM CV (overrides BPM param when patched). |

---

## Outputs

| Name | ID | Signal | Notes |
|------|----|--------|-------|
| `CLK0` / `MASTER` | 0 | CLOCK | Master clock. One pulse per beat at BPM rate. |
| `CLK1` | 1 | CLOCK | Sub-clock 1. Rate determined by RATIO1 param. |
| `CLK2` | 2 | CLOCK | Sub-clock 2. Rate determined by RATIO2 param. |
| `CLK3` | 3 | CLOCK | Sub-clock 3. Rate determined by RATIO3 param. |
| `RESET` | 4 | GATE | Reset gate out (mirrors reset state). |
| `RUN` | 5 | GATE | Run gate out (high while running). |
| `BPM` | 6 | CV | BPM as CV. |

---

## Graph behavior

`ClockedNode` is a `ControllerNode`. It has no `_required_cv` -- the module runs standalone without any inputs patched. All outputs carry `CLOCK` signal except `RESET` (GATE) and `BPM` (CV).

---

## Typical patch role

```
Clocked-Clkd CLK0 -> SEQ3 CLOCK         # quarter-note trigger for sequencer
Clocked-Clkd CLK1 -> GateSequencer16 CLOCK  # sub-clock for gate pattern
```

Typical params for a 120 BPM patch running immediately:

```python
clock = pb.module("ImpromptuModular", "Clocked-Clkd",
                  BPM=120, RUN=1, RATIO1=0, RATIO2=2)
```

---

## Notes

- `BPM` param value is the literal BPM (120.0 = 120 BPM). No conversion needed.
- RATIO1/2/3 default to 0 (same as master). If you want a sub-clock at a different rate, set the ratio explicitly.
- `Clocked` (without `-Clkd`) is a different, wider module. Use `Clocked-Clkd` for the compact standalone version.
- `ImpromptuModular/Foundry` is non-introspectable and should not be used. Use Clocked-Clkd for clocking and SEQ3 for sequencing instead.
