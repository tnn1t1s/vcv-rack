# SlimeChild Substation -- Quantizer

**Plugin:** `SlimeChild-Substation`  **Model:** `SlimeChild-Substation-Quantizer`

Quantizes free CV to musical scale degrees.

## Params

| ID | Name        | Range  | Default | Notes |
|----|-------------|--------|---------|-------|
| 0  | TEMPERAMENT | 0, 1   | 0       | Tuning system |
| 1  | SCALE       | 0, 1   | 0       | Scale selection |
| 2  | ROOT        | 0, 11  | 0       | Root note (0=C, 1=C#, ..., 11=B) |
| 3  | OCTAVE      | -4, 4  | 0       | Octave offset |
| 4  | TRANSPOSE   | 0, 1   | 0       | Transpose mode |

## Inputs

| ID | Name | Notes |
|----|------|-------|
| 0  | ROOT | Root note CV |
| 1  | OCT  | Octave CV |
| 2  | IN   | Free CV input to quantize |

## Outputs

| ID | Name | Notes |
|----|------|-------|
| 0  | OUT  | Quantized V/oct CV |
