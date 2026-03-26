# Befaco Module Reference

Plugin ID: `Befaco`
Discovered cache version: `2.9.1`
All param IDs verified by `rack_introspect` -- see `vcvpatch/discovered/Befaco/`.

---

## EvenVCO

Analog-modeled VCO with five simultaneous wave outputs and alias-free audio quality.

**Graph node class:** `EvenVCONode` (AudioSourceNode)
**Audio outputs:** ports 0-4 (all five waveforms)
**Required CV:** none (but V/OCT input should always be connected to track pitch)

### Params (verified, plugin 2.9.1)

| ID | Registry name | Discovered name | Default | Range | Notes |
|----|--------------|-----------------|---------|-------|-------|
| 0 | `OCTAVE` | Octave | 0 | -5 to 4 | Integer octave shift |
| 1 | `TUNE` | Tune | 0 | -7 to 7 | Fine tune in semitones (TODO: verify unit) |
| 2 | `PW` | Pulse width | 0 | -1 to 1 | Pulse width for PULSE output; 0=50% |

### Ports

**Inputs:**

| ID | Registry name | Notes |
|----|--------------|-------|
| 0 | `EXP` | Exponential FM input |
| 1 | `VOCT`, `V_OCT`, `PITCH` | 1V/octave pitch CV -- connect from sequencer |
| 2 | `PWM` | Pulse width modulation CV |
| 3 | `LIN` | Linear FM input |

**Outputs:**

| ID | Registry name | Notes |
|----|---------------|-------|
| 0 | `TRI` | Triangle wave |
| 1 | `SINE` | Sine wave |
| 2 | `SAW` | Sawtooth wave |
| 3 | `PULSE` | Pulse/square wave (width set by PW param or PWM input) |
| 4 | `EVEN` | "Even" harmonic waveform -- unique to this module |

### Typical patch role

Primary melodic oscillator. Connect a sequencer V/OCT output to `VOCT` (input 1). Choose output waveform based on timbre: SAW for classic analog bass/lead, PULSE for hollow tone (adjust PW), SINE for clean sub, EVEN for bright harmonic content. All five outputs are available simultaneously.

Usage from `patches/generate_dub_techno.py`:
```python
osc1 = patch.add("Befaco", "EvenVCO", pos=[36, 0], OCTAVE=-2, TUNE=0.0)
osc2 = patch.add("Befaco", "EvenVCO", pos=[44, 0], OCTAVE=-2, TUNE=detune / 100.0)
```

### Gotchas

- `TUNE` range is -7 to 7 -- verify whether these are semitones or another unit before setting precise intervals.
- `OCTAVE` takes integer values from -5 to 4; passing a float may work but set whole numbers for predictable pitch.
- The EVEN output waveform is a complex waveform unique to this design (emphasizes even harmonics). It behaves well through a VCF.
- No built-in attenuator on `EXP` or `LIN` inputs -- full CV amplitude is applied directly. Attenuate the CV source or use an attenuverter module before patching FM inputs.
- There is no hardwired sync input. TODO: verify if SYNC is available but not registered.

---

## Kickall

Bass drum synthesizer: a pitched sine/waveshaper oscillator with built-in pitch and amplitude envelopes, triggered by a gate.

**Graph node class:** `KickallNode` (AudioSourceNode)
**Audio outputs:** port 0 (OUT)
**Required CV:** GATE (input 0) must be connected for `patch_proven`.

### Params (verified, plugin 2.9.1)

**Note:** The registry uses different param names than the discovered JSON. The discovered JSON is authoritative. The table below shows both.

| ID | Registry name | Discovered name | Default | Range | Notes |
|----|--------------|-----------------|---------|-------|-------|
| 0 | `FREQ` | Tune | 75.4855 Hz | 27.5-123.471 | Start frequency in Hz |
| 1 | `DECAY` | Manual trigger | 0 | 0-1 | TODO: registry says DECAY but discovered says "Manual trigger" -- ID mismatch |
| 2 | `FM_AMOUNT` | Wave shape | 0 | 0-1 | Registry says FM_AMOUNT; discovered says "Wave shape" -- ID mismatch |
| 3 | `TONE` | VCA Envelope decay time | 0.01 | 0-1 | Registry says TONE; discovered says "VCA Envelope decay time" |
| 4 | `ATTACK` | Pitch envelope decay time | 0 | 0-1 | Registry says ATTACK; discovered says "Pitch envelope decay time" |
| 5 | `DRIVE` | Pitch envelope attenuator | 0 | 0-1 | Registry says DRIVE; discovered says "Pitch envelope attenuator" |

**WARNING: Registry param names do not match the discovered JSON for params 1-5.** The registry appears to use a different ordering or interpretation than what `rack_introspect` reports. Use the discovered JSON IDs and names when setting params programmatically. The registry `FREQ=0` mapping (Tune at id 0) appears correct.

### Ports

**Inputs:**

| ID | Registry name | Notes |
|----|--------------|-------|
| 0 | `GATE` | Trigger input; required -- connects from clock or gate sequencer |
| 1 | `DECAY_CV` | CV modulation for decay time |
| 2 | `PITCH_CV` | V/OCT pitch CV -- shifts the base frequency |
| 3 | `FM` | FM input |

**Outputs:**

| ID | Registry name | Notes |
|----|---------------|-------|
| 0 | `OUT` | Mono audio output |

### Typical patch role

Kick drum in a drum machine patch. Connect a gate sequencer output to GATE (input 0). Connect OUT directly to a mixer channel. The module handles its own amplitude envelope internally -- no external VCA or ADSR needed.

Usage from `patches/dub_techno_rack2.py`:
```python
kick = pb.module("Befaco", "Kickall",
                 FREQ=0.3, DECAY=0.5, TONE=0.4, DRIVE=0.6)
```
Note: these registry names may map to incorrect params given the discovered JSON mismatch. Verify audio results.

### Gotchas

- Registry names for params 1-5 differ from the discovered JSON names. Before setting any param other than FREQ, verify which physical knob you are targeting using the discovered JSON.
- Param 0 (`FREQ` / "Tune") is in Hz (27.5-123.471 Hz range, roughly A0 to B2). Default is ~75 Hz.
- The module has its own internal amplitude envelope -- do not route OUT through a VCA unless you need additional amplitude shaping.
- PITCH_CV (input 2) shifts the start pitch in V/OCT; useful for pitched kick sequences.
- DECAY_CV (input 1) modulates the envelope decay time from an external CV.
