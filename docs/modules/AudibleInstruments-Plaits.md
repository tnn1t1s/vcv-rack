# AudibleInstruments / Plaits

Macro-oscillator with 16 synthesis models selectable via a MODEL knob; outputs main (OUT) and auxiliary (AUX) signals that vary per model.

**Plugin:** `AudibleInstruments`  **Model:** `Plaits`
**Graph node class:** `PlaitsNode` (AudioSourceNode)
**Discovered cache:** `vcvpatch/discovered/AudibleInstruments/Plaits/2.0.0.json`

---

## Params

> **ID source:** Discovered by `rack_introspect` against plugin version 2.0.0. All IDs are verified.
> Use the discovered param names and IDs below as the product truth.

| Param name | ID | Range | Default | Historical shorthand |
|------------|----|-------|---------|----------------------|
| Pitched models (model select A) | 0 | 0..1 | 0 | `MODEL` |
| Noise/percussive models (model select B) | 1 | 0..1 | 0 | — |
| Frequency | 2 | -4..4 | 0 | `FREQ` |
| Harmonics | 3 | 0..1 | 0.5 | `HARMONICS` |
| Timbre | 4 | 0..1 | 0.5 | `TIMBRE` |
| Morph | 5 | 0..1 | 0.5 | `MORPH` |
| Timbre CV | 6 | -1..1 | 0 | `TIMBRE_ATTENUVERTER` |
| Frequency CV | 7 | -1..1 | 0 | `FM_ATTENUVERTER` |
| Morph CV | 8 | -1..1 | 0 | `MORPH_ATTENUVERTER` |
| Lowpass gate response | 9 | 0..1 | 0.5 | `LPG_COLOUR` |
| Lowpass gate decay | 10 | 0..1 | 0.5 | `DECAY` |

### MODEL param note

Plaits has two separate model-select params (id 0 and id 1) rather than one knob
in the module UI. The MODULE param (id 0) selects within the pitched synthesis models
(0..1 range maps to models 0-7), and id 1 selects within noise/percussive models.
Setting both to 0 defaults to model 0 (virtual analog oscillator). The exact sub-model
mapping within each group is TODO -- consult the Mutable Instruments Plaits manual.

---

## Inputs

Current metadata surface:

| Name | ID | Signal | Notes |
|------|----|--------|-------|
| `Pitch_1V_oct_` | 0 | CV | 1V/oct pitch input. |
| `Timbre` | 2 | CV | Timbre CV input. |
| `MORPH` | 3 | CV | Morph CV input. |
| `TRIGGER` | 5 | GATE | Trigger/gate input. Triggers the internal LPG. |

---

## Outputs

| Name | ID | Signal | Notes |
|------|----|--------|-------|
| `OUT` / `Main` | 0 | AUDIO | Main audio output. Content depends on synthesis model. |
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
- Use the exact param names and IDs from the table above rather than relying on older attenuverter folklore.
