# Module Param Patterns

Lessons learned about VCV Rack module initialization that are not obvious
from the patch JSON or wiring alone.

---

## The Attenuator Problem

Many VCV Rack modules have CV inputs paired with an **attenuator param**
that scales the incoming signal. The attenuator defaults to **0**, meaning:

> A cable can be physically connected and `patch_proven` can pass,
> yet the CV has zero audible effect because the attenuator is closed.

This is the most common source of "wired but silent" patches.

### Pattern

```
CV source --[cable]--> module.CV_input
                          |
                   param: attenuator  <-- defaults to 0, must be set > 0
```

### How we catch it

`Node._port_attenuators` maps `input_port_id -> param_id` for every
input that has a paired attenuator. `SignalGraph.warnings` fires if
a port is connected but its attenuator param is 0.

---

## Fundamental / VCO

**Params** (from `vcvpatch/registry.py` and C++ enum, verified 2026-03-23)

The VCO C++ enum has gaps from removed params. IDs are **not** sequential.

| Param id | Name    | Default | Meaning                              |
|----------|---------|---------|--------------------------------------|
| 1        | SYNC    | 0       | hard sync toggle                     |
| 2        | FREQ    | 0       | coarse tune (V, maps to pitch)       |
| 4        | FM      | 0       | FM CV attenuator (-1..1)             |
| 5        | PW      | 0.5     | base pulse width (0=0%, 0.5=square)  |
| 6        | PWM     | 0       | PWM CV attenuator (-1..1)            |
| 7        | LINEAR  | 0       | linear FM mode toggle                |

IDs 0 and 3 are holes left by removed params (`MODE_PARAM` and `FINE_PARAM`).
Do not use them; they exist for backward compatibility only.

**CV Inputs**

| Port id | Name     | Paired attenuator param | Notes                        |
|---------|----------|-------------------------|------------------------------|
| 0       | VOCT     | none                    | 1V/oct pitch, no attenuator  |
| 1       | FM       | param 4 (FM)            | frequency modulation         |
| 2       | SYNC     | none                    | hard sync trigger            |
| 3       | PWM      | param 6 (PWM)           | pulse width modulation       |

**Audio outputs** (as declared in `VCONode._audio_outputs`): SIN=0, TRI=1, SAW=2, SQR=3.

### PWM modulation recipe

Goal: LFO sweeps pulse width of square wave.

```python
vco = patch.add("Fundamental", "VCO",
                FREQ=0.0,    # base pitch (V from C4)
                PW=0.5,      # base pulse width = 50% (true square wave)
                PWM=0.5)     # PWM attenuator = 50% -- LFO now has effect

patch.connect(lfo.SIN, vco.i.PWM)   # LFO -> PWM CV input (port 3)
```

Both `PW` and `PWM` must be set:
- `PW=0.5` -- sets the resting pulse width to 50% (square). At 0 or 1 the wave collapses to silence.
- `PWM=0.5` -- opens the attenuator so the LFO signal actually moves the pulse width.

Without `PWM=0.5` the LFO is connected but the pulse width never moves.

### FM modulation recipe

Goal: LFO sweeps VCO pitch (vibrato / siren).

```python
vco = patch.add("Fundamental", "VCO",
                FREQ=0.0,
                FM=0.5)      # open FM attenuator to 50%

patch.connect(lfo.SIN, vco.i.FM)    # LFO -> FM CV input (port 1)
```

---

## Fundamental / VCF

**Params** (from `vcvpatch/registry.py`)

| Param id | Name     | Default | Meaning                         |
|----------|----------|---------|---------------------------------|
| 0        | FREQ     | 0.5     | Cutoff frequency                |
| 1        | FINE     | 0       | Fine tune (unnamed in older UI) |
| 2        | RES      | 0       | Resonance                       |
| 3        | FREQ_CV  | 0       | Cutoff CV attenuator (-1..1)    |
| 4        | DRIVE    | 0       | Drive                           |
| 5        | RES_CV   | 0       | Resonance CV attenuator         |
| 6        | DRIVE_CV | 0       | Drive CV attenuator             |

**CV Inputs**

| Port id | Name  | Paired attenuator param | Notes                   |
|---------|-------|-------------------------|-------------------------|
| 0       | FREQ  | param 3 (FREQ_CV)       | cutoff modulation       |
| 1       | RES   | param 5 (RES_CV)        | resonance modulation    |
| 2       | DRIVE | param 6 (DRIVE_CV)      | drive modulation        |
| 3       | IN    | none                    | audio input             |

As declared in `VCFNode._port_attenuators`: `{0: 3}` (only FREQ CV attenuator is
tracked for proof warnings; RES_CV and DRIVE_CV are not currently tracked).

---

## Fundamental / VCA

The VCA level defaults to the `LEVEL1` param (id=0), which defaults to 0.
Without a CV signal AND without setting LEVEL1 > 0, the VCA is closed.

| Port id | Name  | Paired attenuator | Notes                        |
|---------|-------|-------------------|------------------------------|
| 0       | EXP1  | none              | exponential CV input         |
| 1       | LIN1  | none (it IS the attenuator) | CV linearly controls level |
| 2       | IN1   | none              | audio input                  |

`VCANode._required_cv = {1: CV}` -- port 1 (LIN1/CV) is required.
The patch prover will flag a VCA on the audio chain with no CV connected.

---

## General Rules

1. **Always open attenuators when connecting CV.** Check `_port_attenuators`
   on the node class. If the attenuator param is 0, the connection is a no-op.
   Use the `modulate()` tool -- it auto-opens attenuators.

2. **Required vs optional CV.** `_required_cv` declares inputs without which
   the module cannot function. Optional CV (like VCO FM) is enhancement only.

3. **PW=0.5 is a square wave.** PW=0 or PW=1 collapses to silence (0% or 100%
   duty cycle). Start at 0.5 and let the LFO sweep around it.

4. **LFO rate units.** Fundamental/LFO `FREQ` param is in Hz (approximately).
   0.4 Hz = one sweep per 2.5 seconds. Good starting point for audible PWM.

5. **VCO param IDs have gaps.** The C++ enum for Fundamental/VCO has removed
   params at IDs 0 and 3. Always use named params (e.g. `FREQ`, `PW`) from
   the registry -- never hardcode integer IDs.
