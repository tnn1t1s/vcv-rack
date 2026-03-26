# 303/606-Style Step Sequencer Pattern

A recipe for sparse, rhythmically irregular bass/lead lines using CountModula
Sequencer16 as the single source of both pitch CV and gate pattern.

---

## What Makes It 303-Style

A Roland TB-303 or TR-606 produces its characteristic sound through three
properties that must all be present simultaneously:

1. **Sparse, irregular gate pattern.** Not every step fires. Resting steps are
   silent -- the envelope never opens. ~40-50% density is typical.

2. **Per-step pitch and per-step gate in one sequencer.** Each step carries its
   own CV value AND its own on/off gate state. The pitch is set independently of
   whether the step fires.

3. **Percussive envelope.** Very fast attack, short decay. The envelope shape is
   punchy and rhythmic, not sustained.

### Why PolySeq/SEQ3 Cannot Do This Properly

`Fundamental/SEQ3` fires a trigger on every step unconditionally. There is no
per-step gate parameter -- every step that advances the sequencer also emits a
trigger. You can work around this with a separate gate sequencer, but that
requires two modules, manual sync, and adds wiring complexity.

`PolySeq` has the same limitation: all steps trigger.

Both are appropriate for regular arpeggios or melodies where every note plays
(see `stranger_things.py`). Neither is appropriate for a sparse, resting pattern.

### Why CountModula Sequencer16 Is the Right Tool

`CountModula/Sequencer16` has two independent params per step:

- `STEP{N}`: the CV value (pitch) for that step
- `TRIG{N}`: whether that step emits a trigger pulse (0.0 = off, 1.0 = on)

This is one module doing the job that would otherwise require a pitch sequencer
plus a synchronized gate sequencer. The gate pattern is baked directly into the
sequencer params.

---

## Signal Flow

```
Clock MULT
    |
    v
Sequencer16 CLOCK
    |
    +--[CV out]----> Quantizer IN --> Quantizer OUT --> SubOscillator VOCT
    |
    +--[TRIG out]--> Envelopes TRIG1
                 \-> Envelopes TRIG2

SubOscillator BASE --> Mixer IN1
SubOscillator SUB1 --> Mixer IN2
SubOscillator SUB2 --> Mixer IN3
Mixer OUT --> Filter IN
Filter OUT --> VCA IN
VCA OUT --> AudioInterface2 IN_L
VCA OUT --> AudioInterface2 IN_R

Envelopes ENV1 --> VCA CV       (amplitude envelope)
Envelopes ENV2 --> Filter FM    (filter envelope)
```

### Exact Port Names

| Cable | From | To |
|-------|------|----|
| Clock to sequencer | `clock.o.MULT` | `seq.i.CLOCK` |
| Pitch CV | `seq.o.CV` | `quant.i.IN` |
| Quantized pitch | `quant.o.OUT` | `subosc.i.VOCT` |
| Gate/trigger | `seq.o.TRIG` | `envs.i.TRIG1` |
| Gate/trigger | `seq.o.TRIG` | `envs.i.TRIG2` |
| Oscillator base | `subosc.o.BASE` | `mixer.i.IN1` |
| Sub octave 1 | `subosc.o.SUB1` | `mixer.i.IN2` |
| Sub octave 2 | `subosc.o.SUB2` | `mixer.i.IN3` |
| Mixer to filter | `mixer.o.OUT` | `filt.i.IN` |
| Filter envelope | `envs.o.ENV2` | `filt.i.FM` |
| Filter to VCA | `filt.o.OUT` | `vca.i.IN` |
| Amplitude envelope | `envs.o.ENV1` | `vca.i.CV` |
| VCA to audio | `vca.o.OUT` | `audio.i.IN_L` |
| VCA to audio | `vca.o.OUT` | `audio.i.IN_R` |

Use `seq.o.TRIG` (1ms pulse) not `seq.o.GATE` (held high). The 1ms pulse is
tighter and more percussive. GATE would keep the envelope open for the full step
duration, which is wrong for 303 character.

---

## Voltage Conventions (1V/oct, C4 = 0V)

```python
F2  = -2.0 + 5/12   # -1.5833V
Ab2 = -2.0 + 8/12   # -1.3333V
C3  = -1.0           # -1.0000V
C4  =  0.0           #  0.0000V (reference)
```

General formula: `note_V = (octave - 4) + semitone / 12`

where semitone is 0=C, 1=C#, 2=D, 3=D#, 4=E, 5=F, 6=F#, 7=G, 8=G#, 9=A,
10=A#, 11=B.

**REST steps:** Set `STEP{N}` to any valid pitch (e.g. the root note) and set
`TRIG{N}` to 0.0. The pitch value on a rest step is completely inaudible because
the envelope never opens. Use the root note as a safe placeholder to avoid
ambiguity when reading the pattern.

---

## Python Builder Pattern

Define the 16-step pattern as two parallel lists, then set all params in a loop:

```python
# Pitch on rest steps is inaudible (gate off). Use root note as placeholder.
REST = F2

PITCHES = [F2, REST, C3, REST, Ab2, REST, C3,  F2,
           REST, REST, C3, REST, Ab2, REST, REST, REST]
GATES   = [1,   0,    1,   0,    1,   0,    1,   1,
           0,    0,    1,   0,    1,   0,    0,   0  ]

seq_params = {}
for i, (pitch, gate) in enumerate(zip(PITCHES, GATES)):
    seq_params[f"STEP{i+1}"] = pitch
    seq_params[f"TRIG{i+1}"] = float(gate)
seq_params["LENGTH"] = 16.0

seq = pb.module("CountModula", "Sequencer16", **seq_params)
```

`TRIG{N}` must be a float. `1.0` = trigger fires on this step; `0.0` = silent.

---

## Example: Subzero Klock-Style Pattern (from subzero.py)

16-step Fm triad pattern at approximately 44% density (7 of 16 steps fire).

```
Step:  01   02   03   04   05   06   07   08   09   10   11   12   13   14   15   16
Note:  F2   --   C3   --   Ab2  --   C3   F2   --   --   C3   --   Ab2  --   --   --
Gate:  on   off  on   off  on   off  on   on   off  off  on   off  on   off  off  off
```

In Python:

```python
F2  = -2.0 + 5/12   # -1.5833V
Ab2 = -2.0 + 8/12   # -1.3333V
C3  = -1.0
REST = F2

PITCHES = [F2, REST, C3, REST, Ab2, REST, C3,  F2,
           REST, REST, C3, REST, Ab2, REST, REST, REST]
GATES   = [1,   0,    1,   0,    1,   0,   1,   1,
           0,    0,    1,   0,    1,   0,   0,   0  ]
```

The pattern is characteristic because:
- Consecutive rests (steps 9-10, 14-16) create rhythmic breath and tension.
- The syncopated hit on step 8 (F2 on the "and" of beat 2) is the hook.
- Three notes only (F2, Ab2, C3) form an Fm triad -- harmonically minimal.

---

## Envelope Settings for Percussive Character

The envelope must open and close within the duration of one 16th note. At 128 BPM
with a x4 clock multiplier, one step is approximately 117ms. These settings work:

```python
envs = pb.module(PLUGIN, "SlimeChild-Substation-Envelopes",
                 EG1_ATTACK=-5,   # very fast attack (~2ms)
                 EG1_DECAY=-3,    # short decay (~50ms)
                 EG2_ATTACK=-5,   # filter envelope: same fast attack
                 EG2_DECAY=-2,    # filter envelope: slightly shorter decay
                 HOLD=0)
```

ENV1 controls VCA amplitude. ENV2 sweeps the filter cutoff downward, producing
the characteristic 303 "blip" on each triggered note.

---

## Sequencer16 Param Reference (CountModula, v2.5.0)

| Param | IDs | Values | Purpose |
|-------|-----|--------|---------|
| `STEP{1-16}` | 16-31 | float (voltage) | Per-step pitch CV in 1V/oct |
| `TRIG{1-16}` | 37-52 | 0.0 or 1.0 | Per-step trigger enable (drives TRIG out) |
| `GATE{1-16}` | 53-68 | 0.0 or 1.0 | Per-step gate enable (drives GATE out) |
| `LENGTH` | 32 | 1.0-16.0 | Number of active steps |

| Output | Enum ID | Use for |
|--------|---------|---------|
| `GATE` | 0 | Held gate (ADSR with sustain) |
| `TRIG` | 1 | 1ms pulse (percussive envelopes) |
| `END` | 2 | 1-shot end pulse (ignore for looping) |
| `CV` | 3 | Pitch CV (1V/oct) |
| `CVI` | 4 | Inverted pitch CV |

| Input | Enum ID |
|-------|---------|
| `RUN` | 0 |
| `CLOCK` | 1 |
| `RESET` | 2 |

---

## Checklist

Before calling `pb.compile()`, verify:

- [ ] `seq_params["LENGTH"] = 16.0` is set (default is not 16)
- [ ] All `TRIG{N}` values are `float` (not `int`) -- use `float(gate)`
- [ ] Clock multiplier matches intended subdivision (x4 for 16th notes at quarter-note clock)
- [ ] `seq.o.TRIG` is connected, not `seq.o.GATE`, unless you need sustained notes
- [ ] `pb.proven` is `True` before saving -- if not, print `pb.report()` and fix
