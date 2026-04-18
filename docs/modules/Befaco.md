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

| ID | Current name | Notes |
|----|--------------|-------|
| 0 | `EXP` | Exponential FM input |
| 1 | `VOCT`, `V_OCT`, `PITCH` | 1V/octave pitch CV -- connect from sequencer |
| 2 | `PWM` | Pulse width modulation CV |
| 3 | `LIN` | Linear FM input |

**Outputs:**

| ID | Current name | Notes |
|----|---------------|-------|
| 0 | `TRI` | Triangle wave |
| 1 | `SINE` | Sine wave |
| 2 | `SAW` | Sawtooth wave |
| 3 | `PULSE` | Pulse/square wave (width set by PW param or PWM input) |
| 4 | `EVEN` | "Even" harmonic waveform -- unique to this module |

### Typical patch role

Primary melodic oscillator. Connect a sequencer V/OCT output to `VOCT` (input 1). Choose output waveform based on timbre: SAW for classic analog bass/lead, PULSE for hollow tone (adjust PW), SINE for clean sub, EVEN for bright harmonic content. All five outputs are available simultaneously.

Usage from `patches/archive/generate_dub_techno.py`:
```python
osc1 = patch.add("Befaco", "EvenVCO", position=[36, 0], OCTAVE=-2, TUNE=0.0)
osc2 = patch.add("Befaco", "EvenVCO", position=[44, 0], OCTAVE=-2, TUNE=detune / 100.0)
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

Use the discovered param names and IDs below as the product truth.

| ID | Param name | Default | Range | Historical shorthand |
|----|------------|---------|-------|----------------------|
| 0 | Tune | 75.4855 Hz | 27.5-123.471 | `FREQ` |
| 1 | Manual trigger | 0 | 0-1 | `DECAY` |
| 2 | Wave shape | 0 | 0-1 | `FM_AMOUNT` |
| 3 | VCA Envelope decay time | 0.01 | 0-1 | `TONE` |
| 4 | Pitch envelope decay time | 0 | 0-1 | `ATTACK` |
| 5 | Pitch envelope attenuator | 0 | 0-1 | `DRIVE` |

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

Usage from `patches/archive/dub_techno_rack2.py`:
```python
kick = pb.module("Befaco", "Kickall",
                 FREQ=0.3, DECAY=0.5, TONE=0.4, DRIVE=0.6)
```
These names are historical shorthand only. Prefer the exact discovered names from the table above when writing new patches.

### Gotchas

- Use the exact param names and IDs from the table above for new code. Older examples that use `DECAY`, `TONE`, `ATTACK`, or `DRIVE` are historical.
- Param 0 (`FREQ` / "Tune") is in Hz (27.5-123.471 Hz range, roughly A0 to B2). Default is ~75 Hz.
- The module has its own internal amplitude envelope -- do not route OUT through a VCA unless you need additional amplitude shaping.
- PITCH_CV (input 2) shifts the start pitch in V/OCT; useful for pitched kick sequences.
- DECAY_CV (input 1) modulates the envelope decay time from an external CV.
