# SlimeChild Substation -- Sub-Oscillator

**Plugin:** `SlimeChild-Substation`  **Model:** `SlimeChild-Substation-SubOscillator`

Generates two sub-harmonic waveforms below a reference pitch. Designed for bass/drone use.

## Params

| ID | Name      | Range   | Default | Notes |
|----|-----------|---------|---------|-------|
| 0  | BASE_FREQ | -48, 48 | 0       | Semitone offset from V/OCT |
| 1  | WAVEFORM  | 0, 2    | 2       | Waveform type |
| 2  | SUBDIV1   | 1, 16   | 1       | Integer subdivision 1 (frequency = base / SUBDIV1) |
| 3  | SUBDIV2   | 1, 16   | 1       | Integer subdivision 2 |
| 4  | PWM       | 0, 1    | 0.5     | Pulse width |
| 5  | DETUNE    | -2, 2   | 0       | Detune between SUB1 and SUB2 |

## Inputs

| ID | Name  | Notes |
|----|-------|-------|
| 0  | V/OCT | Pitch CV |
| 1  | SUB1  | CV to modulate Subdivision 1 amount |
| 2  | SUB2  | CV to modulate Subdivision 2 amount |
| 3  | PWM   | Pulse width CV |

## Outputs

| ID | Name | Notes |
|----|------|-------|
| 0  | BASE | Main oscillator output at base frequency |
| 1  | SUB1 | Sub-harmonic 1 (base / SUBDIV1) |
| 2  | SUB2 | Sub-harmonic 2 (base / SUBDIV2) |

## Notes

- SUBDIV=2 gives one octave below, SUBDIV=4 gives two octaves below
- BASE output is the full-rate oscillator; useful as a root tone
- Ports confirmed from https://slimechildaudio.com/substation/manual/suboscillator/
