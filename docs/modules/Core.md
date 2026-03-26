# Core Module Reference

Plugin: `Core` (always installed, part of VCV Rack itself)

Discovered JSON cache: none -- Core modules are intrinsic to Rack and not
introspected via `rack_introspect`. Port IDs come from the Rack source.

---

## AudioInterface2

Routes patch audio to the host audio device. Every patch that produces sound
must terminate in this module.

**Node class:** `AudioInterface2Node` (AudioSinkNode)
**Graph role:** Terminal audio sink. Receiving a signal here satisfies
`audio_reachable` for the proof system.

### Input ports

| ID | Name | Aliases | Function |
|----|------|---------|----------|
| 0  | IN_L | IN1, L  | Left channel audio input |
| 1  | IN_R | IN2, R  | Right channel audio input |

### Output ports

| ID | Name   | Aliases | Function |
|----|--------|---------|----------|
| 0  | OUT_L  | OUT1    | Left channel monitor output (pass-through) |
| 1  | OUT_R  | OUT2    | Right channel monitor output (pass-through) |

### Params

| ID | Name   | Default | Range | Notes |
|----|--------|---------|-------|-------|
| 0  | VOLUME | --      | --    | Master output volume |

### Typical use

Connect the final stereo output of the patch (mixer, reverb, VCA, etc.) to
IN_L and IN_R. Mono patches typically connect the same source to both inputs:

```python
audio = pb.module("Core", "AudioInterface2")
pb.chain(vca.o.OUT, audio.i.IN_L)
pb.chain(vca.o.OUT, audio.i.IN_R)
```

The `data` dict inside the serialized module selects the audio device. When
fixing a patch for a different machine, reset `audio["data"]` to point at the
correct driver (see `patches/fix_dub_tech4.py`).

---

## MidiMap

Maps MIDI CC messages to any module param for live runtime control.

**Node class:** `MidiMapNode` (ControllerNode)
**Graph role:** Pure side-effect controller. No audio inputs, no required CV
inputs. Adding MidiMap never affects `patch_proven`.

### Port IDs

MidiMap has no signal ports. It operates entirely through its serialized `data`
block, which lists CC-to-param mappings.

### Params

None exposed through the registry (all configuration lives in `extra_data`).

### How live CC control works

1. Build a `MidiMapBuilder`, call `.map(cc=N, module_id=..., param_id=...)` for
   each param to control.
2. Pass `mmb.build()` as `extra_data` when adding the MidiMap module to the
   patch.
3. Open the patch in VCV Rack (GUI mode -- not headless; see caveat below).
4. Python opens a virtual CoreMIDI port (`vcvpatch_control`) via
   `RackConnection.connect()`.
5. Call `RackConnection.set_param()` to send CC messages; Rack updates the
   param in real time.
6. Call `RackConnection.read_state()` to read current values from the autosave.

```python
from vcvpatch.runtime import MidiMapBuilder, RackConnection

mmb = MidiMapBuilder()
mmb.map(cc=1, module_id=vco.id, param_id=2)   # CC1 -> VCO FREQ
mmb.map(cc=2, module_id=vcf.id, param_id=0)   # CC2 -> VCF FREQ
midi_map = pb.module("Core", "MidiMap", extra_data=mmb.build())
```

**Critical caveat:** MIDI live control only works when Rack is running in GUI
mode (normal launch). The headless `-h` flag skips CoreMIDI initialization on
macOS, so the virtual port is invisible to Rack. For fully headless use, fall
back to stop-patch-relaunch (stop Rack, write param to `.vcv`, relaunch).

Source: `docs/gotchas.md` "MIDI live control requires GUI mode"

---

## MIDIToCVInterface

Converts incoming MIDI messages (from a hardware controller or DAW) to CV
signals usable in the patch.

**Node class:** None registered in `vcvpatch/graph/modules.py`. Listed in
`installed.py` as a known Core module but not modelled in `NODE_REGISTRY`. If
placed on the audio path it will appear as an `UnknownNode` and block
`patch_proven`. Use it only as a CV source feeding other modules; do not place
it on the provable audio chain.

**TODO:** Add a `MIDIToCVInterfaceNode` (ControllerNode) to `modules.py` if
proof of patches using MIDI input is needed.

### Output ports

Port IDs sourced from `registry.py`. No discovered JSON exists for Core modules.

| ID | Name       | Aliases          | Function |
|----|------------|------------------|----------|
| 0  | PITCH      | VOCT             | 1V/oct pitch CV from note-on |
| 1  | GATE       |                  | Gate high while note held |
| 2  | VELOCITY   | VEL              | Note velocity (0-10V) |
| 3  | AFTERTOUCH | AT               | Channel aftertouch |
| 4  | PW         |                  | Pitch wheel |
| 5  | MOD        |                  | Mod wheel (CC1) |
| 6  | RETRIGGER  | RETRIG           | Trigger pulse on each new note |
| 7  | CLOCK      |                  | MIDI clock output |
| 8  | CLOCK_DIV  |                  | MIDI clock divided |
| 9  | START      |                  | MIDI start message |
| 10 | STOP       |                  | MIDI stop message |
| 11 | CONTINUE   |                  | MIDI continue message |

### Input ports

None (MIDI input is configured via the module's device selector UI, not by
patching a cable).

### Params

None registered. The module is configured through its panel UI (device and
channel selection), not via param IDs.

### Typical use

Feed PITCH and GATE to a VCO and VCA/ADSR to play the patch from a keyboard.
RETRIG feeds into the ADSR RETRIG input to re-trigger the envelope without
releasing between legato notes.

```python
midi_cv = pb.module("Core", "MIDIToCVInterface")
pb.chain(midi_cv.o.PITCH, vco.i.VOCT)
pb.chain(midi_cv.o.GATE,  adsr.i.GATE)
pb.chain(midi_cv.o.RETRIG, adsr.i.RETRIG)
```
