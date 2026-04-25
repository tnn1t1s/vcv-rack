# Voice Lab

Offline render / analyze / compare tooling for AgentRack drum voices.

This exists to make voice development agentic and repeatable:
- render a deterministic one-shot directly from module DSP
- analyze a rendered or reference `.wav`
- compare a candidate render against a reference sample
- fit internal model parameters against fixed labeled targets
- collect preference labels when the scalar loss is not perceptually aligned

The current analysis core is intentionally narrow:
- voices:
  - `snr`
  - `clp`
  - `rim`
- commands:
  - `ar-render`
  - `ar-analyze`
  - `ar-compare`

Input ingestion is broader than the internal representation:
- mono or multi-channel `.wav`
- PCM 8/16/24/32-bit
- 32-bit float `.wav`
- arbitrary sample rate

All input audio is normalized to:
- mono
- float
- 44.1 kHz

All commands are JSON-first. The JSON emitted today is the contract that later
search / tuning tools should consume.

## Build

```bash
make -C tests build/ar-render build/ar-analyze build/ar-compare
```

## Terminology

Keep these distinctions explicit:
- `model` / `estimator`
  - the DSP implementation that generates sound
  - example: `src/Snr.cpp`
- `parameters`
  - adjustable internal values of that model
  - example: oscillator base Hz, decay constants, filter cutoffs
- `conditioning inputs`
  - the fixed user-facing controls implied by a labeled sample
  - example: `Tune`, `Tone`, `Snappy`
- `metric` / `measurement`
  - features extracted from audio
  - example: envelope windows, body-pitch trajectory, FFT bands
- `loss` / `objective`
  - the weighted scalar built from those measurements

The workflow depends on not confusing these layers.

## Fitting Method

For a labeled target like `tune050-tone100-snappy100`:
- evaluate only at `tune=0.5`, `tone=1.0`, `snappy=1.0`
- do **not** search user-facing controls during fitting
- search only internal model parameters
- if fit converges but the sound is still wrong, inspect the metric/loss
- change architecture only after parameter fitting and metric cleanup stop helping

In short:
1. fix conditioning inputs from the labeled target
2. compare reference and candidate under those exact inputs
3. optimize internal parameters only
4. if the score is misleading, fix the metric/loss
5. only then consider a model change

This is the method that got the 909 snare from "clearly wrong" to "passable close".

## Commands

### `ar-render`

Render a deterministic hit from a voice without opening Rack.

```bash
tests/build/ar-render \
  --voice snr \
  --frames 8192 \
  --param tune=0.50 \
  --param tone=1.00 \
  --param snappy=1.00 \
  --wav /tmp/snr.wav
```

### `ar-analyze`

Analyze a reference `.wav`, normalize it to the lab representation, and emit
onset-trimmed envelope and spectral features.

```bash
tests/build/ar-analyze \
  ~/Downloads/TR-909-44.1kHz-16bit/SnareDrum/SnareDrum909-tune050-tone100-snappy100.wav
```

### `ar-compare`

Render a candidate voice, analyze it, analyze the reference, then emit a
weighted distance score.

```bash
tests/build/ar-compare \
  --voice snr \
  --reference ~/Downloads/TR-909-44.1kHz-16bit/SnareDrum/SnareDrum909-tune050-tone100-snappy100.wav \
  --param tune=0.50 \
  --param tone=1.00 \
  --param snappy=1.00 \
  --artifact-dir /tmp/voice-lab-snr
```

## Current Feature Set

The current analysis payload includes:
- onset trim start/end
- peak / RMS
- duration
- attack time
- decay to -20 dB / -40 dB
- zero crossing rate
- global FFT band energy
- per-window envelope
- per-window spectral centroid
- per-window FFT band energy
- per-window low-body pitch estimate
- per-window upper-body mode estimate

This is enough to drive render/analyze/compare loops and preference-guided loss
updates without introducing a full optimizer framework yet.

## Preference Loop

The current snare workflow also has a preference-label sidecar in
`scratch/snr-feedback/`.

Use it when:
- the scalar loss looks good but the sound is still wrong
- a local basin sounds promising by ear but scores worse
- the remaining disagreement is subtle and best captured by human ranking

Workflow:
1. generate a batch of fixed-conditioning candidates
2. present `reference -> variant` playback pairs
3. collect thumbs-up / thumbs-down labels
4. inspect which metric terms disagree with the labels
5. update the loss
6. refit the model under the new loss

Important rule:
- preference labels should challenge the loss, not overwrite the target controls

## Snare Lessons

What mattered on `Snr`:
- fixed conditioning inputs were essential
- broad search over user-facing `Tune/Tone/Snappy` was a mistake
- the first loss underweighted tonal center and body placement
- a windowed body-pitch trajectory term was necessary
- later, an upper-body mode measurement was needed to explain local ear judgments
- after that, preference labels were useful for loss shaping

This is the template to reuse for `Rim`:
- start with fixed labeled targets
- search internal fit params first
- listen early
- if the score disagrees with the ear, fix the metric before rewriting the model

## References

Canonical reference paths for local 909 sample packs live in:

`voice_lab/references/909.json`
