# AgentRack Test Plan

AgentRack now has enough shared internal structure that tests should be
organized by subsystem, not by historical accident.

The current test strategy should distinguish between four layers:

1. Component contract tests
   Cover small shared `Signal` and `Infrastructure` types directly.
   These should not depend on Rack and should be cheap to run.

2. DSP math / kernel tests
   Cover extracted DSP kernels where the behavior is stable and numerical.
   These may depend on FFT backends or other pure DSP code, but still avoid
   Rack module wiring.

3. Module regression tests
   Cover important module-level invariants after the DSP or UI structure has
   stabilized. Use these sparingly and only for behaviors that matter.

4. Manual smoke tests
   Real Rack patch-loading and listening passes remain valuable, but should
   sit on top of the automated layers above rather than replace them.

## Current coverage

### Component contract tests

- `test_signal_cv.cpp`
  - `Signal::CV::toBipolarUnit()`
  - `Signal::CV::Parameter`
  - `Signal::CV::VoctParameter`

- `test_signal_audio.cpp`
  - `Signal::Audio::fromRackVolts()`
  - `Signal::Audio::toRackVolts()`
  - `Signal::Audio::ConstantPowerMix`

### DSP math / kernel tests

- `test_fft.cpp`
  - round-trip correctness
  - impulse spectrum
  - convolution identity
  - linearity
  - Parseval
  - boundary safety

- `test_partitioned_convolution.cpp`
  - zero IR silence
  - delta IR identity after block latency
  - reload/state reset behavior
  - stereo channel independence

## Current gaps

### Shared component gaps

- no tests yet for future `Signal::Audio` helpers beyond boundary conversion
- no tests yet for future `Interface` layout primitives
- no direct tests yet around semantic naming / exactness of layout families

### DSP kernel gaps

- no tests yet for BusCrush-specific signal path behavior
- no tests yet for Cassette engine internals
- no tests yet for remaining reverb/tape infrastructure beyond partitioned
  convolution

### Module regression gaps

- no module-level regression tests yet for AgentRack modules
- no stable harness yet for asserting process-level module behavior without
  dragging Rack UI concerns into the tests

## First module regression harness

The initial harness should stay deliberately small:

- instantiate deterministic module classes directly
- set params and input voltages
- call `process()` for a controlled number of samples
- assert stable output/state invariants

First module targets:
- `Attenuate`
- `ADSR`
- `Ladder`

These are good first candidates because they are deterministic, have clear
behavioral contracts, and do not depend on heavyweight runtime infrastructure.

## Coverage policy going forward

When shared code is extracted:
- add a focused standalone test in `plugin/AgentRack/tests`
- prefer component tests over module tests when the behavior can be isolated
- only add module-level regression tests when the behavior is important and
  stable enough to justify the harness cost

When module refactors land:
- if the refactor extracts reusable behavior, the extracted type should bring
  its own test
- if the refactor only rearranges UI/layout code, prefer review/manual smoke
  unless there is a stable geometry contract worth asserting

## Next recommended additions

1. Cassette engine coverage after the next infrastructure extraction.
2. BusCrush signal-path coverage if its voltage-domain semantics are
   standardized.
3. A small layout-contract test layer once `PanelLayout` geometry stabilizes
   enough to treat as an API.
