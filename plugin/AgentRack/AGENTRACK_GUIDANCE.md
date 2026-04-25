# AgentRack Guidance

This file captures repo-local design guidance for AgentRack modules so future
work does not depend on thread memory.

## Knob Semantics

Use the standard VCV Rack convention unless there is a very strong reason not
to.

- **Unipolar controls** use a left-to-right domain.
  - hard left = minimum
  - hard right = maximum
  - typical range: `0..1`
  - examples: `Level`, `Drive`, `Decay`, `Tone`, `Tune` when expressed as
    "less to more" rather than signed offset

- **Bipolar controls** use a centered domain.
  - center = `0`
  - left = negative
  - right = positive
  - typical range: `-1..1`
  - examples: attenuverters, modulation depth, offset, signed trim, pan

Do **not** use centered bipolar knobs as a blanket style for all controls.
Only use them when the parameter is conceptually signed.

## AgentRack Policy

For AgentRack production modules:

- user-facing sound controls should default to **unipolar** unless the original
  instrument or control meaning is inherently signed
- CV depth / modulation trim controls should default to **bipolar**
- if a module exposes both a main parameter and a CV amount, prefer:
  - main parameter: unipolar or domain-native
  - CV amount / attenuverter: bipolar with center detent semantics

## 909 Module Policy

For the 909 family in this repo:

- preserve faithful panel semantics where possible
- do not expose internal fit parameters as production controls
- use debug/research modules for wide tuning surfaces
- if a voice is effectively solved by sample playback for our use case, prefer
  the ROMpler path over a more complex synthesis model

## Modeling Workflow

When fitting emulations:

- separate **model**, **metric**, and **loss**
- keep labeled user-facing control values fixed during fitting
- search internal parameters before changing architecture
- if the model is wrong, replace it instead of overfitting the loss

