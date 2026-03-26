# AgentRack: Concept Brief

## Why does this exist?

A VCV Rack module is designed around a feedback loop:

```
human adjusts knob → hears result → adjusts again
```

Everything about conventional modules follows from this. Log-scale knobs feel
right under a hand. Attenuverters default to 0 so the human can "open" them
deliberately. The panel layout is a visual affordance. The module does not need
to explain itself because the human is listening.

An agent cannot close this loop. It reasons symbolically before the patch runs.
It needs to make a claim -- "this patch sounds like X" -- and verify that claim
without listening. The module's job is not to feel good under a hand. It is to
make a claim the agent can verify.

That is the only design requirement. Everything else follows from it.

---

## Sound as a set of independent dimensions

A musical description like "dark resonant bass with a slow filter sweep" is not
a waveform. It is a **specification across multiple independent dimensions**:

```
pitch      what notes, in what register
timbre     tonal character -- bright, dark, harmonic content
dynamics   amplitude over time -- punchy, sustained, swelling
rhythm     when notes happen, what pattern, what density
space      acoustic environment -- dry, roomy, echoing
```

These dimensions are largely **orthogonal**. Changing the pitch does not change
the timbre. Changing the rhythm does not change the space. A specification
describes a point in this multi-dimensional space, and a patch is a set of
models that together estimate that point.

This is the key reframe:

> A patch is not a signal chain. It is an ensemble of models, each making an
> estimate along one musical dimension.

---

## What a model is

A model is a parameterized function:

```
output = model(input; θ)
```

where θ is a vector of parameters the agent sets at patch-build time. The
model makes one narrow claim: "given these parameters, I produce a signal with
this musical character along my dimension."

A **pitch model** claims: "I produce voltage that traces this pitch trajectory."
A **dynamics model** claims: "I produce an envelope with this attack and decay."
A **space model** claims: "I place the signal in a room of this size and decay."

The agent fits θ by translating a musical specification into parameter values.
"Dark" → cutoff = 400Hz. "Punchy" → attack = 5ms, decay = 80ms. "Roomy" →
size = 0.8, decay = 0.7. The fitting is the agent's core reasoning task.

---

## What an ensemble is

An ensemble covers the full specification. It is complete when every dimension
of the spec is addressed by at least one model:

```
spec: "dark resonant bass, slow filter sweep, sparse rhythm, large space"

Sequence model   → rhythm dimension ✓
Voice model      → pitch + timbre + dynamics ✓
LFO + Attenuate  → modulation of timbre (the sweep) ✓
Space model      → acoustic space ✓

Ensemble: complete.
```

A patch with no dynamics model is **provably incomplete** -- not just
potentially quiet, but missing a claim the specification requires. The proof
system's job is to verify ensemble completeness, not just audio reachability.

---

## Why existing modules fail here

Existing modules are not models in this sense. They are **DSP primitives** --
VCO, VCF, VCA, ENV -- that implement specific signal processing operations.
They make no claims about musical dimensions. A VCO does not claim to cover the
pitch dimension; it just oscillates. A VCF does not claim to cover the timbre
dimension; it just filters.

The agent has to compose 5-8 DSP primitives to cover one musical dimension,
and every composition step introduces failure modes: wrong port IDs, closed
attenuverters, undocumented parameter scales, load-time state resets.

A model collapses this. One model covers one dimension. Its parameters are in
musical units (Hz, seconds, semitones). It has no hidden state. It cannot be
misconfigured in ways that silently produce the wrong sound. The agent makes
one claim per dimension and verifies it.

---

## The innovation in one sentence

> Design synthesis units around musical dimensions rather than DSP primitives,
> so that an agent can fit a multi-model ensemble to a musical specification
> and prove the ensemble is complete.

---

## What this is not

It is not a new synthesis algorithm. The DSP inside each model can be
conventional (ladder filter, ADSR envelope, delay line). The innovation is
in the **interface contract** between the model and the agent, not in the
signal processing.

It is not trying to replace Bogaudio or Fundamental for human players. A human
would hate this plugin: no expressive parameter scaling, no visual performance
controls, no interesting panel. It is deliberately boring to play and
deliberately clear to reason about.

It is not an AI that composes music. The agent composes. The model computes.
The model has no intelligence. The agent uses the model's claim-making
structure to reason about what a patch will sound like before it runs.
