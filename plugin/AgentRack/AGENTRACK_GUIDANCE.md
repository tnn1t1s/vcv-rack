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

## Debug Module Policy

A `*Dbg` variant of a synthesis voice (e.g. `KckDbg`, `TomDbg`) is not an
internal tool. It is a release-quality module aimed at power users who want
direct access to the full model surface for fitting, sound design, or
modulation experiments. The doctrine:

- Every internal `Fit::Config` field that materially affects voicing is
  exposed as a knob on the debug panel.
- Every knob has a CV input below it, scaled at the same convention used
  by the rest of AgentRack (0.1 of knob range per volt, summed with the
  knob value, clamped to the parameter's range).
- The debug panel is wider than the production panel (typical 30--36 HP)
  and uses a knob + CV-jack grid layout with comfortable spacing
  (~26 mm row spacing, ~10 mm knob-to-jack gap). Busy is OK; the
  audience is power users.
- Defaults on the debug knobs match the production module's `Fit::Config`
  defaults, so an instance fresh from the browser sounds identical to the
  production voice. Users tweak from there.

### Two legitimate use cases (do not conflate)

A debug module serves two distinct purposes, and only one of them feeds
back into production defaults:

1. **Fitting tool.** A user adjusts knobs *toward a reference* (e.g.\ a
   sample of the real instrument). When the converged settings sound
   right and a corresponding spectrum / measurement check confirms the
   match, fold the values back into the production module's
   `Fit::Config` defaults. The debug module is the design surface;
   production is what crystallises out of it.

2. **Sound-design instrument.** A user adjusts knobs *away* from any
   reference, into their own artistic vision (think Maurizio, Ben Klock,
   Hawtin given a 30-HP control surface for a kick). Those settings live
   in the user's patch as a sound-design choice, never as production
   defaults. Don't bake artistic exploration into the production module's
   voicing; doing so would steal a single user's preferences and impose
   them on every new instance.

Before folding any debug-module state into production, confirm with the
user which of the two modes they were in. The clearest signal is whether
they were comparing against a reference (fitting) or simply playing the
instrument (sound design).

## Modeling Workflow

When fitting emulations:

- separate **model**, **metric**, and **loss**
- keep labeled user-facing control values fixed during fitting
- search internal parameters before changing architecture
- if the model is wrong, replace it instead of overfitting the loss

