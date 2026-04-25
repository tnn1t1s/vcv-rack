## Summary

Define and enforce the fitting method for `Snr` so we stop conflating:

- user-facing 909 controls
- internal model calibration
- architectural/model changes

The immediate problem is that we were informally searching both the source-conditioned control space (`Tune`, `Tone`, `Snappy`) and the internal implementation space. That makes it too easy to "move the target" instead of improving the estimator.

## Core Framing

Treat the snare implementation as an unfitted estimator.

- **Estimator**: `src/Snr.cpp`
- **Trainable/internal fit parameters**: internal constants and coefficients in the current snare model
- **Conditioning inputs**: `Tune`, `Tone`, `Snappy`
- **Targets**: labeled reference WAVs such as `SnareDrum909-tune050-tone100-snappy100.wav`
- **Loss**: feature distance between rendered output and the labeled target

For a labeled target sample, the user-facing controls are **fixed inputs**, not search variables.

## Rules

1. **Do not move the target**
   - If the target file is `tune050-tone100-snappy100`, evaluation happens at exactly:
   - `tune=0.50`
   - `tone=1.00`
   - `snappy=1.00`

2. **Do not search user-facing controls during fitting**
   - `Tune`, `Tone`, and `Snappy` are part of the supervised label for the training example.
   - They are not free optimization variables during fitting.

3. **Search internal fit parameters first**
   - Example internal fit parameters:
   - oscillator base frequencies
   - oscillator balance
   - body decay times
   - body filter cutoff
   - pitch bend depth / decay
   - noise clock rate
   - low/high noise filter cutoffs
   - low/high noise balance
   - click amount
   - saturation amount

4. **Only after fit-parameter convergence do we consider model changes**
   - If loss plateaus above acceptable error after internal calibration, then the model architecture is likely wrong.
   - Only then should we change topology or voice structure.

## Optimization Ladder

This should be the explicit annealing / escalation path:

1. Fix conditioning inputs from the labeled target.
2. Optimize only internal fit parameters.
3. Re-evaluate across a set of labeled targets.
4. If loss converges well enough, keep the model and continue calibration.
5. If loss stalls materially above the target threshold, escalate to architectural change.

## Score / Loss Requirements

The score should reflect time-varying timbral structure, not only global averages.

At minimum the loss should include:

- windowed FFT band trajectory distance
- global FFT band energy distance
- envelope distance
- attack difference
- duration / decay difference

We already compute per-window band energies in the voice lab. Those should remain a first-class part of the score because they are the most direct way to evaluate whether the rendered snare matches the target's evolving frequency composition.

## Tooling Direction

Voice-lab tooling should separate:

- **conditioning vars**: `tune`, `tone`, `snappy`
- **fit vars**: internal `Snr` model constants
- **model vars**: architectural choices

Planned workflow:

1. Choose a labeled snare target WAV.
2. Render `Snr` with the exact labeled control values.
3. Search internal fit vars only.
4. Score against the fixed target.
5. Repeat across multiple labeled target samples.

## Acceptance Criteria

- `Snr` fitting never searches `Tune`, `Tone`, or `Snappy` for a labeled target sample.
- Voice-lab score prominently includes windowed FFT band trajectory distance.
- We can fit `Snr` against multiple labeled 909 snare references with one shared model.
- Architectural changes are only made after internal fit-parameter search stops yielding meaningful score improvement.

## Why This Matters

If the loss remains high for a `tone100` reference when evaluated at `tone=1.0`, that is evidence of:

- bad control-law calibration
- bad internal fit parameters
- or a bad model

It is **not** evidence that the target should be reinterpreted or that the user-facing control should be moved during fitting.

The method needs to make that distinction explicit so we do not accidentally optimize for a flattering workaround instead of a faithful emulation.
