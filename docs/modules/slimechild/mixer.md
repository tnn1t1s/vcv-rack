# SlimeChild Substation -- Saturating Mixer

**Plugin:** `SlimeChild-Substation`  **Model:** `SlimeChild-Substation-Mixer`

3-channel mixer with per-channel CV modulation, saturation drive, and chain I/O for cascading.

## Params

| ID | Name        | Range  | Default | Notes |
|----|-------------|--------|---------|-------|
| 0  | LEVEL1      | 0, 1   | 0       | Channel 1 level |
| 1  | LEVEL2      | 0, 1   | 0       | Channel 2 level |
| 2  | LEVEL3      | 0, 1   | 0       | Channel 3 level |
| 3  | MOD1        | -1, 1  | 0       | Ch1 level CV attenuverter |
| 4  | MOD2        | -1, 1  | 0       | Ch2 level CV attenuverter |
| 5  | MOD3        | -1, 1  | 0       | Ch3 level CV attenuverter |
| 6  | MIX_LEVEL   | 0, 1   | 1       | Master output level |
| 7  | CHAIN_GAIN  | 0, 1   | 1       | Gain for chained input |
| 8  | DRIVE       | 0, 1   | 0       | Saturation drive |

## Inputs

| ID | Name  | Notes |
|----|-------|-------|
| 0  | IN1   | Channel 1 audio |
| 1  | IN2   | Channel 2 audio |
| 2  | IN3   | Channel 3 audio |
| 3  | CV1   | Channel 1 level CV |
| 4  | CV2   | Channel 2 level CV |
| 5  | CV3   | Channel 3 level CV |
| 6  | CHAIN | Chained audio from another mixer |
| 7  | LEVEL | Master level CV |

## Outputs

| ID | Name  | Notes |
|----|-------|-------|
| 0  | CHAIN | Pass-through for chaining to next mixer |
| 1  | OUT   | Final stereo mix output |

## Notes

- Channel level params default to 0 -- set LEVEL1/2/3 to hear audio
- CHAIN output/input allow multiple mixers to be linked in series
- DRIVE adds harmonic saturation to the mix bus
