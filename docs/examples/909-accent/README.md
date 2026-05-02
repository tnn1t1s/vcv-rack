# 909 Accent Calibration Patches

Reference VCV Rack patches that exercise the AgentRack TR-909 accent
system end-to-end. They are kept in version control so anyone (human
or agent) can load a known-good rig, sweep the controller knobs, and
verify the four accent cases (ghost / A-only / B-only / both) match
the configured `AccentMix` dB targets.

These are **examples**, not unit tests. The unit tests in
`plugin/AgentRack/tests/test_module_regressions.cpp` cover the
abstraction algebraically (peak ratios within tolerance). These
patches cover the *playable* layer — what does it sound like with a
real sequencer driving it — and serve as fixtures for ear-tuning.

## Generating

```bash
# All three variants:
python3 docs/examples/909-accent/build_test_patch.py --all

# Just one:
python3 docs/examples/909-accent/build_test_patch.py --variant basic
```

The committed `.vcv` files in this directory are the canonical output
of the script and should be regenerated (and committed) any time the
script's defaults change.

## Variants

| File                    | Pattern                                      | Use |
|-------------------------|----------------------------------------------|-----|
| `kck_basic_test.vcv`    | 4-on-floor BD, no accent rails wired         | Calibrate DEFAULT knob and per-voice `ghostDb`. |
| `kck_accent_a_test.vcv` | 4-on-floor BD + ACC-A on alternates          | Calibrate ACC A vs DEFAULT relationship. |
| `kck_dense_test.vcv`    | 16ths BD + ACC-A every 4 + ACC-B every 4     | Full 4-case coverage. |

## Tr909Ctrl knobs

Each `.vcv` includes a `Tr909Ctrl` adjacent to `Kck` so the bus chain
forms automatically. Knobs:

- **DEFAULT** — 0..1 multiplier on the ghost (no-accent) case. Useful
  for setting the global "default volume" floor while tuning.
- **ACCENT A** — 0..1 attenuator on the A-rail's contribution. At 0,
  any A-only hit is silent and the both-case collapses to B-only.
- **ACCENT B** — same shape for the B rail.
- **MASTER** — post-everything linear scalar.

## Underlying sequencer

Hora `Drumsequencer` drives the kit. The script writes the gate arrays
directly into the patch:

- `gates2P1` -> output 4 (BD) -> Kck TRIG
- `gates1P1` -> output 3 (ACC, "#4 output" in Hora UI) -> Kck TOTAL_ACC
- `gates3P1` -> output 5 (used as Local Accent in the dense variant) ->
   Kck LOCAL_ACC

Hora needs a specific baseline param set + `gate run = 0` (auto-run)
or it sits idle silently; see `docs/modules/Hora-Drumsequencer.md`.

## Known perceptual quirk

In `kck_dense_test.vcv`, when DEFAULT is turned low, the rapid
sequence of quiet ghost kicks becomes click-prominent (kick body fades
into the noise floor before the click transient does, so all you hear
is the click). This is uniform-attenuation physics, not a code bug.
Use `kck_basic_test.vcv` for clean low-volume calibration.
