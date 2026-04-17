# Sequencer16 Patterns

Saved patterns for use with `CountModula/Sequencer16`. Each entry records the
full param state so it can be restored in a patch script without re-opening Rack.

All patterns assume `RANGE_SW=1` (direct 1V/oct mapping, STEP 0-1 = 0-1V, C4=0V).
SubOsc rows show the pitch two octaves down when `SUBDIV2=4` (typical bass setting).

---

## Pattern 001 -- Ab Minor Drift (live session, 2026-03-23)

A 6-step sparse pattern that drifted from the original Subzero Klock triad into
something more chromatic. Knobs were tweaked live; Ab/G# is the gravitational
center with a triplet landing at steps 14-15-16 that bleeds into the next bar
when routed through Chronoblob2 delay.

### Context

Evolved from `patches/curated/subzero.py` (Klock F minor triad) during a live session.
The delay effect (see Chronoblob2 params below) makes the terminal triplet
(steps 14-16) feel like a syncopated pickup into the next loop cycle. Without
the delay the ending feels abrupt; with it you get an implied continuation.

### Step table

| Step | TRIG | STEP   | Note (direct) | Note (SubOsc SUB2, -2oct) |
|------|------|--------|--------------|---------------------------|
| 01   |  1   | 0.6626 | G#4 / Ab4    | G#2 / Ab2  << active      |
| 02   |  0   | 0.6826 | G#4          | G#2                       |
| 03   |  0   | 0.6861 | G#4          | G#2                       |
| 04   |  0   | 0.6927 | G#4          | G#2                       |
| 05   |  0   | 0.6667 | G#4          | G#2                       |
| 06   |  0   | 0.5281 | F#4          | F#2                       |
| 07   |  1   | 0.5092 | F#4          | F#2  << active            |
| 08   |  1   | 0.6625 | G#4          | G#2  << active            |
| 09   |  0   | 0.6912 | G#4          | G#2                       |
| 10   |  1   | 0.7083 | G#4          | G#2  << active            |
| 11   |  0   | 0.6957 | G#4          | G#2                       |
| 12   |  0   | 0.9986 | C5           | C3                        |
| 13   |  0   | 0.7337 | A4           | A2                        |
| 14   |  1   | 0.4336 | F4           | F2   << active            |
| 15   |  0   | 0.6638 | G#4          | G#2                       |
| 16   |  1   | 0.7437 | A4           | A2   << active            |

Active steps (TRIG=1): 1, 7, 8, 10, 14, 16 (6 of 16, ~38% density)

Gate pattern: `[1,0,0,0,0,0,1,1,0,1,0,0,0,1,0,1]`

Pitch summary: Ab/G# dominant, with F# (step 7) and F (step 14) as chromatic
passing tones; A (step 16) as a leading tone back to the top.

### Sequencer params

```
LENGTH   = 16.0
RANGE_SW = 1.0   # direct 1V/oct
DIRECTION = 0.0  # forward
HOLD      = 1.0  # CV holds last value (off = no trigger mode)
```

### SubOscillator params (at time of save)

| Param ID | Value  | Notes |
|----------|--------|-------|
| 0 (BASE_FREQ) | -0.5561 | Tuned down slightly from C4 |
| 1 (WAVEFORM)  | 2.0    | Waveform 2 (saw or similar) |
| 2 (SUBDIV1)   | 11.0   | SUB1 divider |
| 3 (SUBDIV2)   | 10.0   | SUB2 divider (not 4; knob was tweaked live) |
| 4 (PWM)       | 0.5020 | ~50% pulse width |
| 5 (DETUNE)    | 0.8839 | Heavy detune |

### Envelopes params (at time of save)

| Param ID | Value   | Meaning |
|----------|---------|---------|
| 0 (EG1_ATTACK) | -2.848 | Fast attack (~5ms) |
| 1 (EG1_DECAY)  | -0.372 | Medium decay |
| 2 (EG2_ATTACK) | -2.385 | Fast filter attack |
| 3 (EG2_DECAY)  | -3.000 | Minimal filter decay (at minimum) |
| 4 (HOLD)       | 0.0    | AD mode (trigger-based) |

### Filter params (at time of save)

| Param ID | Value  | Notes |
|----------|--------|-------|
| 0 (FREQ) | 3.0107 | High cutoff (open filter) |
| 1 (RES)  | 1.0857 | Resonance above self-oscillation threshold |
| 2 (FM)   | -0.004 | Minimal FM (near zero) |

### Mixer params (at time of save)

| Param ID | Value  | Notes |
|----------|--------|-------|
| 0 (LEVEL1) | 1.000 | BASE full |
| 1 (LEVEL2) | 0.750 | SUB1 at 75% |
| 2 (LEVEL3) | 0.739 | SUB2 at 74% |
| 6 (MIX_LEVEL) | 0.746 | Master ~75% |
| 8 (DRIVE) | 0.200 | Light drive |

### Chronoblob2 delay params (at time of save)

| Param ID | Value  | Notes |
|----------|--------|-------|
| 0 | 0.2274 | TIME (short-medium delay) |
| 1 | 0.0490 | FEEDBACK (very low -- single echo) |
| 2 | 0.4938 | MIX (~50% wet) |

**Key effect:** The FEEDBACK=~0 single echo of the triplet (steps 14-16) bleeds
into the start of the next 16-bar loop cycle. With 50% wet mix this creates an
implied pickup beat at bar start without muddying the pattern. The delay is
felt rhythmically but not heard as a distinct echo -- it smooths the loop seam.

### Python builder snippet

To restore this pattern in a patch script:

```python
STEPS = [0.6626, 0.6826, 0.6861, 0.6927, 0.6667, 0.5281, 0.5092, 0.6625,
         0.6912, 0.7083, 0.6957, 0.9986, 0.7337, 0.4336, 0.6638, 0.7437]
TRIGS = [1, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0, 0, 1, 0, 1]

seq_params = {}
for i, (pitch, trig) in enumerate(zip(STEPS, TRIGS)):
    seq_params[f"STEP{i+1}"] = pitch
    seq_params[f"TRIG{i+1}"] = float(trig)
seq_params["LENGTH"]    = 16.0
seq_params["RANGE_SW"]  = 1.0

seq = pb.module("CountModula", "Sequencer16", **seq_params)
```

---
