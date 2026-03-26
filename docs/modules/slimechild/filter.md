# SlimeChild Substation -- LP4 Filter

**Plugin:** `SlimeChild-Substation`  **Model:** `SlimeChild-Substation-Filter`

Physically-modelled 24dB/octave ladder lowpass filter.

## Params

| ID | Name | Range       | Default | Notes |
|----|------|-------------|---------|-------|
| 0  | FREQ | 0, 9.966    | 4.983   | log-Hz. Default ≈ mid-range cutoff |
| 1  | RES  | 0, 1.2      | 0       | Resonance; >1.0 approaches self-oscillation |
| 2  | FM   | -1, 1       | 0       | FM CV attenuverter (must open to hear FM input) |

## Inputs

| ID | Name  | Notes |
|----|-------|-------|
| 0  | V/OCT | Pitch tracking (1V/oct shifts cutoff) |
| 1  | FM    | FM CV (attenuated by FM param) |
| 2  | IN    | Audio input |

## Outputs

| ID | Name | Notes |
|----|------|-------|
| 0  | OUT  | Filtered audio |

## Notes

- FM param is an attenuverter: must be non-zero for FM input to have effect
- V/OCT input enables keyboard tracking (cutoff follows pitch)
- `_port_attenuators = {1: 2}` -- FM input port 1 uses FM param (id=2)
