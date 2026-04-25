---
name: agentrack-voice-lab
description: Use when working on AgentRack drum voice fidelity, especially snare/clap/rim, and you need to render one-shots, analyze reference WAVs, compare candidates against references, or play rendered hits locally with afplay.
---

# AgentRack Voice Lab

Use this skill from the AgentRack repo root:

`/Users/palaitis/Development/vcv-rack/plugin/AgentRack`

The voice-lab CLIs live in `tests/build/` and are built by `tests/Makefile`.

## Build

Build the three core tools before use:

```bash
make -C tests build/ar-analyze build/ar-render build/ar-compare
```

## Commands

Analyze a reference WAV:

```bash
tests/build/ar-analyze <wav-path>
```

Render a deterministic hit:

```bash
cd tests && DYLD_LIBRARY_PATH=../../../vendor/rack-sdk ./build/ar-render \
  --voice snr --param tune=0.5 --param tone=1.0 --param snappy=1.0 \
  --wav /tmp/vcv/p1/snr.wav
```

Compare a rendered hit against a reference:

```bash
cd tests && DYLD_LIBRARY_PATH=../../../vendor/rack-sdk ./build/ar-compare \
  --voice snr \
  --reference /Users/palaitis/Downloads/TR-909-44.1kHz-16bit/SnareDrum/SnareDrum909-tune050-tone100-snappy100.wav \
  --param tune=0.5 --param tone=1.0 --param snappy=1.0 \
  --artifact-dir /tmp/voice_lab_snr_cmp
```

## Supported Voices

- `snr`
- `clp`
- `rim`

## Fitting Rules

When working from labeled source material such as
`tune050-tone100-snappy100.wav`:

- keep the conditioning inputs fixed to the label
- do **not** search user-facing controls during fitting
- search only internal model parameters first
- if the score improves but the sound stays wrong, fix the metric/loss
- change architecture only after parameter fitting and metric cleanup plateau

Keep the layers distinct:
- `model`
  - the DSP implementation, such as `src/Snr.cpp`
- `metric`
  - measurements extracted from audio
- `loss`
  - the weighted score built from those measurements

Do not say "the estimator values X" when the problem is really in the metric or
loss.

## Reference Map

Canonical local references are in:

`voice_lab/references/909.json`

Use those paths instead of scanning `~/Downloads`.

## Audio Input Contract

`ar-analyze` and `ar-compare` accept broader WAV inputs and normalize them to:

- mono
- float
- `44100 Hz`

The analysis core remains stable after normalization.

## Playback

To audition a rendered hit:

```bash
afplay /tmp/vcv/p1/snr.wav
```

If `afplay` fails due to device/sandbox restrictions, rerun it with escalation.

## Default Workflow

1. Pick the reference WAV from `voice_lab/references/909.json`.
2. Run `ar-analyze` once on the reference if you need feature inspection.
3. Render with `ar-render` into `/tmp/vcv/<tag>/`.
4. Play the render with `afplay` when ear-checking.
5. Run `ar-compare` to get a machine score and save artifacts.
6. Change DSP only after listening and checking the score deltas.

## Preference Loop

If the loss is clearly misaligned with listening:

1. Generate a fixed-conditioning batch in `scratch/snr-feedback/`.
2. Use `snr-batch.html` or the equivalent batch page to collect thumbs up/down.
3. Treat those labels as preference data over a local basin.
4. Adjust the loss so retained `up` examples rank below retained `down` examples.
5. Refit the model under that updated loss.

Use this loop for `rim` as well as `snr`.
