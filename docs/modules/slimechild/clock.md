# SlimeChild Substation -- Clock

**Plugin:** `SlimeChild-Substation`  **Model:** `SlimeChild-Substation-Clock`

A simple clock with a master rate and a multiplied output.

## Params

| ID | Name   | Range          | Default | Notes |
|----|--------|----------------|---------|-------|
| 0  | TEMPO  | -1.585, 3.585  | 1.0     | log2(Hz). Formula: `log2(BPM/60)`. Default=1 → 120 BPM. |
| 1  | RUN    | 0, 1           | 0       | 0=stopped, 1=running |
| 2  | MULT   | 1, 16          | 1       | Integer multiplier for MULT output |

### BPM to TEMPO conversion

```python
import math
tempo_param = math.log2(bpm / 60)
# 120 BPM -> 1.000
# 127 BPM -> 1.082
# 140 BPM -> 1.222
```

## Inputs

| ID | Name | Notes |
|----|------|-------|
| 0  | RUN  | Gate: starts/stops the clock |
| 1  | SYNC | Sync to external clock |

## Outputs

| ID | Name | Notes |
|----|------|-------|
| 0  | BASE | Master clock at BPM rate (1 pulse/beat) |
| 1  | MULT | BASE × MULT param (e.g. MULT=4 → 16th notes) |

## Usage patterns

```python
import math

# 127 BPM, 16th note MULT output for a 16-step sequencer
clock = pb.module("SlimeChild-Substation", "SlimeChild-Substation-Clock",
                  TEMPO=math.log2(127/60), RUN=1, MULT=4)

# Clock a 16-step sequencer at 16th note rate
pb.chain(clock.o.MULT, seq.i.CLOCK)
```

## Notes

- TEMPO param replaces the Clocked-Clkd BPM approach -- no ratio table complexity
- MULT output = BASE × integer multiplier; use for subdivisions (4=16th, 2=8th, 8=32nd)
- RUN=1 in the patch file starts the clock on load
