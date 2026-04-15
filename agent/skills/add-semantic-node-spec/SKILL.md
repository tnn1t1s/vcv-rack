---
name: add-semantic-node-spec
description: Add or update a vcvpatch graph semantic spec for a maintained module, preferring declarative YAML specs over hand-written Node subclasses and adding focused proof tests.
---

# Add Semantic Node Spec

Use this when a maintained patch, test, or agent flow depends on a module whose
signal semantics are not yet represented in `vcvpatch`.

## Decision Rule

Add a semantic spec only when the module is part of the maintained agent-facing
authoring surface:

- used in maintained examples or tests
- used repeatedly in generated patches
- important enough that agents should not rely on numeric escape hatches or
  explicit `cable_type=` forever

Do not add specs just because a Rack module exists.

Do not build an AgentRack clone unless the module needs stronger machine-facing
guarantees than an external module can provide.

## Preferred Representation

Prefer YAML specs in `vcvpatch/graph/specs/*.yaml`.
The current registry uses grouped files with a top-level `modules:` list.

Use a Python subclass only when the module's semantics cannot be expressed by
the existing node kinds and fields.

Current declarative node kinds:

- `audio_source`
- `audio_processor`
- `audio_mixer`
- `audio_sink`
- `controller`
- `passthrough`

Current declarative fields:

- `plugin`
- `model`
- `kind`
- `description`
- `routes`
- `audio_inputs`
- `audio_outputs`
- `outputs`
- `required_inputs`
- `attenuators`

Signal strings in YAML are exact lower-case values:

- `audio`
- `cv`
- `gate`
- `clock`

## Process

1. Decide whether the module deserves a semantic spec at all.
2. Pick the smallest node kind that fits.
3. Add or update a YAML spec under `vcvpatch/graph/specs/`.
4. Only touch Python node code if the new module reveals a missing semantic
   primitive.
5. Add one focused regression test that proves the value of the spec.
6. Keep the test at the builder/graph boundary, not at raw implementation detail.

## Good First Fit

Use YAML when the module is mostly declarative:

- fixed routes
- fixed audio inputs/outputs
- fixed control outputs
- fixed required control inputs
- simple passthrough behavior

Example:

- `vcvpatch/graph/specs/registry.yaml`

## When Python Is Justified

Use Python only when the module needs behavior that cannot be represented by the
existing declarative kinds, for example:

- output semantics depend on richer runtime conditions than static routes or
  passthrough inheritance
- the module needs a new graph-semantic primitive
- proof behavior needs custom logic beyond the current node algebra

If you need Python, first ask whether the missing behavior should become a new
reusable node kind instead of a one-off subclass.

## Testing Rule

Always add a focused regression test that demonstrates why the spec matters.

Good examples:

- a formerly explicit `cable_type=` can now be inferred correctly
- a control-gap proof now succeeds or fails correctly
- a passthrough node preserves upstream signal type across outputs

Bad examples:

- giant patch snapshots
- tests that only assert the YAML file exists

## Anti-Patterns

Avoid:

- adding a spec for a one-off module nobody maintains
- duplicating DSP or UI concepts in the graph layer
- hard-coding historical aliases or heuristics into core lookup
- introducing a custom subclass when a declarative spec is enough
- making the builder guess semantics for unknown modules
