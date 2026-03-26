# SlimeChild Substation -- VCA

**Plugin:** `SlimeChild-Substation`  **Model:** `SlimeChild-Substation-VCA`

Simple voltage-controlled amplifier.

## Params

| ID | Name  | Range | Default | Notes |
|----|-------|-------|---------|-------|
| 0  | LEVEL | 0, 1  | 1       | Base level (CV adds to this) |

## Inputs

| ID | Name | Notes |
|----|------|-------|
| 0  | CV   | Level CV (0-10V opens fully) |
| 1  | IN   | Audio input |

## Outputs

| ID | Name | Notes |
|----|------|-------|
| 0  | OUT  | Amplitude-controlled audio |

## Notes

- Level param defaults to 1 (fully open) -- audio passes without CV connected
- Connect an envelope ENV output to CV for amplitude shaping
- Unlike Fundamental VCA, this defaults open so it won't silence audio without CV
