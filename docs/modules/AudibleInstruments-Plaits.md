# AudibleInstruments / Plaits

Macro-oscillator with 16 synthesis models selectable via a MODEL knob; outputs main (OUT) and auxiliary (AUX) signals that vary per model.

**Plugin:** `AudibleInstruments`  **Model:** `Plaits`
**Graph node class:** `PlaitsNode` (AudioSourceNode)
**Discovered cache:** `vcvpatch/discovered/AudibleInstruments/Plaits/2.0.0.json`

---

## Params

> **ID source:** Discovered by `rack_introspect` against plugin version 2.0.0. All IDs are verified.
> The registry.py mapping matches the discovered IDs with two exceptions noted below.

| Discovered name | ID | Range | Default | Registry.py alias |
|-----------------|----|-------|---------|-------------------|
| Pitched models (model select A) | 0 | 0..1 | 0 | `MODEL` |
| Noise/percussive models (model select B) | 1 | 0..1 | 0 | (no registry alias -- TODO) |
| Frequency | 2 | -4..4 | 0 | `FREQ` |
| Harmonics | 3 | 0..1 | 0.5 | `HARMONICS` |
| Timbre | 4 | 0..1 | 0.5 | `TIMBRE` |
| Morph | 5 | 0..1 | 0.5 | `MORPH` |
| Timbre CV (attenuverter) | 6 | -1..1 | 0 | `TIMBRE_ATTENUVERTER` |
| Frequency CV (attenuverter) | 7 | -1..1 | 0 | `FM_ATTENUVERTER` (registry uses id 5 -- **mismatch**) |
| Morph CV (attenuverter) | 8 | -1..1 | 0 | `MORPH_ATTENUVERTER` (registry uses id 7 -- **mismatch**) |
| Lowpass gate response | 9 | 0..1 | 0.5 | `LPG_COLOUR` (registry uses id 9 -- matches) |
| Lowpass gate decay | 10 | 0..1 | 0.5 | `DECAY` (registry uses id 8 -- **mismatch**) |

**Registry.py mismatch note:** The registry.py param IDs for `FM_ATTENUVERTER` (5),
`TIMBRE_ATTENUVERTER` (6), `MORPH_ATTENUVERTER` (7), `DECAY` (8), and `LPG_COLOUR` (9)
do not align with the discovered IDs (Timbre CV=6, Frequency CV=7, Morph CV=8,
LPG response=9, LPG decay=10). The discovered IDs are authoritative. Use numeric IDs
directly when setting attenuverter params. **TODO: fix registry.py for Plaits attenuverters.**

### MODEL param note

Plaits has two separate model-select params (id 0 and id 1) rather than one knob
in the module UI. The MODULE param (id 0) selects within the pitched synthesis models
(0..1 range maps to models 0-7), and id 1 selects within noise/percussive models.
Setting both to 0 defaults to model 0 (virtual analog oscillator). The exact sub-model
mapping within each group is TODO -- consult the Mutable Instruments Plaits manual.

---

## Inputs

IDs from registry.py; verified against the standard Mutable Instruments port layout.

| Name | ID | Signal | Notes |
|------|----|--------|-------|
| `PITCH` / `VOCT` | 0 | CV | 1V/oct pitch input. |
| `HARMONICS` | 1 | CV | Harmonics CV. Open `TIMBRE_ATTENUVERTER` (id 6) to activate. |
| `TIMBRE` | 2 | CV | Timbre CV. Open `TIMBRE_ATTENUVERTER` (id 6) to activate. |
| `MORPH` | 3 | CV | Morph CV. Open `MORPH_ATTENUVERTER` (id 8 discovered) to activate. |
| `FM` | 4 | CV | FM input. Open `FM_ATTENUVERTER` (id 7 discovered) to activate. |
| `TRIGGER` / `GATE` | 5 | GATE | Trigger/gate input. Triggers the internal LPG. Required for percussive envelopes. |
| `LEVEL` | 6 | CV | Level CV (0..8V). Controls LPG amplitude. |
| `MODEL` | 7 | CV | Model CV input (selects synthesis model dynamically). |

---

## Outputs

| Name | ID | Signal | Notes |
|------|----|--------|-------|
| `OUT` / `MAIN` | 0 | AUDIO | Main audio output. Content depends on synthesis model. |
| `AUX` | 1 | AUDIO | Auxiliary output. Content varies by model (e.g., sub-oscillator, different waveform, noise). |

---

## Graph behavior

`PlaitsNode` is an `AudioSourceNode`. Audio outputs are ports 0 and 1. No `_required_cv`
is declared -- the module produces audio without any inputs patched (at fixed pitch, no envelope).
For a complete patch, connect V/OCT and TRIGGER at minimum.

---

## Typical patch role

Plaits works as a self-contained voice source. For a monophonic synth voice:

```python
plaits = pb.module("AudibleInstruments", "Plaits",
                   FREQ=0.0, HARMONICS=0.5, TIMBRE=0.5, MORPH=0.5)
pb.cable(seq, "CV1", plaits, "VOCT")
pb.cable(adsr, "GATE", plaits, "TRIGGER")
pb.cable(plaits, "OUT", vca, "IN")
```

---

## Notes

- FREQ param range is -4..4 (octave offset from A4). Default 0 = A4.
- The internal LPG (lowpass gate) is activated by the TRIGGER input. Without a trigger,
  the module outputs a continuous tone at fixed amplitude controlled by the LEVEL input.
- LEVEL input (port 6) controls amplitude into the LPG; 0V = silent, 8V = full. This
  is an alternative to an external VCA/envelope.
- AUX output content is model-dependent. For model 0 (virtual analog), AUX is typically
  a different waveform (e.g., square vs sine on OUT).
- All CV attenuverter params default to 0 -- patching a CV input without opening its
  attenuverter has no effect.
