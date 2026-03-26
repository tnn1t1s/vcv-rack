# SlimeChild Substation -- Envelopes

**Plugin:** `SlimeChild-Substation`  **Model:** `SlimeChild-Substation-Envelopes`

Dual semi-interruptable Attack-Decay envelope generators. Both envelopes share a single module.

## Params

| ID | Name       | Range  | Default | Notes |
|----|------------|--------|---------|-------|
| 0  | EG1_ATTACK | -3, 1  | -1      | log scale attack time |
| 1  | EG1_DECAY  | -3, 1  | -1      | log scale decay time |
| 2  | EG2_ATTACK | -3, 1  | -1      | |
| 3  | EG2_DECAY  | -3, 1  | -1      | |
| 4  | HOLD       | 0, 1   | 0       | 0=AD, 1=AR (sustain while gate high) |
| 5  | TRIGGER    | 0, 1   | 0       | manual trigger button |

## Inputs

| ID | Name    | Notes |
|----|---------|-------|
| 0  | TRIG1   | Gate/trigger for EG1 |
| 1  | TRIG2   | Gate/trigger for EG2 |

## Outputs

| ID | Name | Notes |
|----|------|-------|
| 0  | ENV1 | EG1 envelope CV (0-10V) |
| 1  | ENV2 | EG2 envelope CV (0-10V) |

## Notes

- "Semi-interruptable": a new trigger mid-decay retriggers from current level
- HOLD=1 turns AD into AR -- envelope sustains while gate is held high
- Both EGs share the HOLD mode setting
