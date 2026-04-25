# Snare Feedback Workflow

This directory contains the ad hoc but now codified feedback tooling used to
fit the 909 snare by ear when the scalar loss was still wrong.

## Files

- `server.py`
  - tiny local HTTP server for static files plus `/submit`
- `index.html`
  - simple two-sound A/B page
- `manual-drop10.html`
  - first manual oscillator sweep page
- `generate_snr_batch.py`
  - generates a 100-item snare batch over a fixed osc1/osc2 grid
- `snr-batch.html`
  - manifest-driven batch page with reference/variant playback and thumbs up/down
- `snr_batch_100/`
  - generated manifest plus rendered batch WAVs

## Why This Exists

The snare fit hit a common ML-style failure mode:
- the loss improved
- the rendered snare still sounded wrong

At that point manual listening was more informative than another blind search.
The batch tooling let the user act as a preference oracle over a local basin.

## Batch Workflow

1. Generate the batch:

```bash
python3 scratch/snr-feedback/generate_snr_batch.py
```

2. Start the local server:

```bash
python3 scratch/snr-feedback/server.py
```

3. Open the page:

```text
http://127.0.0.1:8765/snr-batch.html
```

4. For each item:
- play `reference -> variant`
- mark `Thumb Up` or `Thumb Down`
- optionally write notes

5. Submit the batch:
- writes `/tmp/{hash}.txt`
- payload is JSON text containing:
  - batch id
  - conditioning inputs
  - per-variant parameters
  - thumbs
  - optional notes

## Interpretation

The batch labels are not the target themselves.
They are a debugging signal for:
- whether the local basin is promising
- whether the metric/loss agrees with the ear
- which terms are missing or overweighted

Use the labels to shape the loss first.
Only then refit the model.

## Reuse For Rimshot

For `Rim`, follow the same pattern:
- keep the reference controls fixed
- generate a local batch over the most pitch/timbre-relevant internal params
- collect thumbs
- check whether the metric ranks ups below downs
- adjust the loss if needed
- only after that run another fit pass

The rimshot should probably get its own generator page rather than reusing the
snare filenames, but the method is the same.
