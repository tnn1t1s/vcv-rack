# AaronStatic / ChordCV

Takes a 1V/oct root CV and outputs four individual chord-note CVs plus one polyphonic CV carrying all four notes, based on a selectable chord type, inversion, and voicing.

**Plugin:** `AaronStatic`  **Model:** `ChordCV`
**Graph node class:** `ChordCVNode` (ControllerNode)
**Discovered cache:** `vcvpatch/discovered/AaronStatic/ChordCV/2.0.1.json`

---

## Params

All IDs verified by `rack_introspect` against plugin version 2.0.1.

| Discovered name | ID | Range | Default | Registry.py alias | Notes |
|-----------------|----|-------|---------|-------------------|-------|
| Root Note | 0 | -4..4 | 0 | `ROOT_NOTE` | Root pitch offset in octaves from A4. 0 = A4. |
| Chord Type | 1 | -4..4 | -4 | `CHORD_TYPE` | Chord quality (see table below). Default -4 = major. |
| Inversion | 2 | 0..3 | 0 | `INVERSION` | 0=root, 1=first, 2=second, 3=third inversion. |
| Voicing | 3 | 0..4 | 0 | `VOICING` | Voicing spread (0=close, 4=wide). |

### CHORD_TYPE values

| Value | Chord quality |
|-------|--------------|
| -4 | Major |
| -3 | Minor |
| -2 | Dominant 7th |
| -1 | Minor 7th |
| 0 | Major 7th |
| 1 | Sus2 |
| 2 | Sus4 |
| 3 | Diminished |
| 4 | Augmented |

---

## Inputs

IDs from registry.py.

| Name | ID | Signal | Notes |
|------|----|--------|-------|
| `ROOT` / `PITCH` / `VOCT` | 0 | CV | 1V/oct root pitch input. Transposes all chord outputs. |
| `TYPE` | 1 | CV | CV selects chord type (overrides CHORD_TYPE param). |
| `INVERSION` | 2 | CV | CV selects inversion (overrides INVERSION param). |
| `VOICING` | 3 | CV | CV selects voicing (overrides VOICING param). |

---

## Outputs

| Name | ID | Signal | Notes |
|------|----|--------|-------|
| `NOTE1` | 0 | CV | First chord note (root or inverted). 1V/oct. |
| `NOTE2` | 1 | CV | Second chord note. 1V/oct. |
| `NOTE3` | 2 | CV | Third chord note. 1V/oct. |
| `NOTE4` | 3 | CV | Fourth chord note. 1V/oct. |
| `POLY` | 4 | CV | Polyphonic output carrying all four notes (4 channels). |

---

## Graph behavior

`ChordCVNode` is a `ControllerNode`. All five outputs carry CV signal. No `_required_cv`
is declared -- the module generates chord CVs without any inputs patched, using param values
for root, type, inversion, and voicing.

---

## Typical patch role

ChordCV converts a single pitch sequence into a four-voice chord block. Connect the root
pitch from a sequencer, and route NOTE1-4 or POLY to VCOs or a polyphonic oscillator.

```python
chord = pb.module("AaronStatic", "ChordCV",
                  CHORD_TYPE=-4,  # major
                  INVERSION=0,
                  VOICING=0)
pb.cable(seq, "CV1", chord, "ROOT")
pb.cable(chord, "NOTE1", vco1, "VOCT")
pb.cable(chord, "NOTE2", vco2, "VOCT")
pb.cable(chord, "NOTE3", vco3, "VOCT")
pb.cable(chord, "NOTE4", vco4, "VOCT")
# Or use POLY with a polyphonic module:
pb.cable(chord, "POLY", plaits, "VOCT")
```

---

## Notes

- ROOT_NOTE param (id 0) is a static offset, not a 1V/oct value. The ROOT input (port 0) is the 1V/oct pitch CV from a sequencer.
- CHORD_TYPE default in the discovered file is -4 (major), which matches the registry.py comment.
- INVERSION 0 = root position (lowest note is the root). Inversions 1-3 raise the lower notes by an octave successively.
- VOICING 0 = close voicing (all notes within one octave). Higher values spread notes across octaves.
- The POLY output (port 4) is a 4-channel polyphonic cable -- downstream modules must support polyphony.
- No gate output. Pair with a gate sequencer (e.g., GateSequencer16) for rhythm.
