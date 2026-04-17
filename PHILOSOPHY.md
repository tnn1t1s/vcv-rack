# PHILOSOPHY

This repo has three orthogonal parts with three different intents.

Confusing them leads to bad design.

## Prime Directive

**Derive semantics from code/runtime objects.**

Do not duplicate system truth in prompts, wrapper layers, or parallel semantic registries unless there is no better option.

The ideal agentic system is one where the agent can inspect the same live structures that the runtime itself uses.

That principle matters more here than almost anything else.

## The Three Categories

### 1. `agent/` is the user

`agent/` is not the product.

It is the acting client of the system.
Its job is simple:

- take prompts
- reason
- inspect the system
- generate patches

The agent should not become the place where core semantic truth lives.

It is allowed to have:

- taste
- strategy
- preferences
- orchestration logic

It is **not** where we should author duplicated descriptions of module semantics if those semantics already exist elsewhere in code.

In other words:

- tools for facts and actions
- prompt/persona for taste

The agent is a user of the environment, even though it is implemented in code inside the same repo.

### 2. `vcvpatch/` is the product

`vcvpatch/` is the central product in this repo.

It is the authoring environment the agent uses.

It owns:

- patch construction
- proof and graph semantics
- metadata
- serialization
- runtime interaction
- the programming model for patch generation

If there is a “prime” layer in this repo, it belongs inside `vcvpatch`, because `vcvpatch` is the system through which the agent understands and constructs patches.

That means:

- availability
- affordance
- exact surface
- proof-relevant semantics

should ultimately be exposed through `vcvpatch` in a way that is inspectable and derived from real code/runtime objects.

Not because `vcvpatch` should narrate the world twice, but because it is the environment in which the world becomes programmable.

### 3. `plugin/AgentRack/` is a module suite

`AgentRack` is not the substrate and not the user.

It is a module suite.

Ontologically, it lives in the same category as:

- Fundamental
- Bogaudio
- SlimeChild
- Valley
- JW Modules
- other Rack module providers

It is special not because it is a different category, but because it is intentionally designed to express its affordances more clearly to agents.

That is its thesis.

If AgentRack does a better job exposing:

- coherent names
- coherent modulation semantics
- coherent signal semantics
- coherent layout semantics
- coherent machine-readable intent

then agents should prefer it over other suites for the same musical role.

So AgentRack is best understood as:

- a module suite optimized for the prime directive

not:

- the prime substrate itself

## Relationship Between The Three

The clean model is:

- `agent` is the patch author
- `vcvpatch` is the authoring environment
- `AgentRack` is one family of instruments available in that environment

That is the ontology.

And the strategic relationship is:

- `vcvpatch` defines the environment in which agents compose patches
- `AgentRack` is the first module suite explicitly optimized to thrive in that environment

This is why AgentRack matters so much without being the substrate.

## What This Implies

### For `agent/`

The agent should not be stuffed with duplicated semantic knowledge.

Instead, it should:

1. inspect the available environment
2. inspect the relevant module/runtime objects
3. choose from bounded possibilities
4. build patches

This is why bounded-palette planning is better than “search the world for ideal modules.”

### For `vcvpatch/`

`vcvpatch` should expose the world in a form that is:

- inspectable
- programmable
- semantically derived

If additional “intel” or “catalog” views are needed, they should be:

- derived views over existing truth
- not new handwritten truth

### For `AgentRack`

AgentRack should continue to optimize for:

- semantic legibility
- coherent modulation contracts
- consistent layout language
- machine-facing clarity

It wins not by being magical, but by being easier for an agent to understand and use correctly.

## Anti-Patterns

These are the mistakes this philosophy rejects:

- putting semantic truth in prompts when it already exists in code
- building wrapper tools that merely restate inspectable runtime knowledge
- treating AgentRack as the substrate instead of a module suite
- treating the agent as the product instead of the user
- duplicating affordance descriptions in multiple places

## North Star

The future direction is:

- systems expose their own structure clearly
- agents inspect that structure directly
- actions are separate from knowledge
- module suites compete on how well they express affordance to agents

This is bigger than VCV Rack.

It applies to:

- agentic software engineering
- robotics
- world-model interaction
- any environment where an agent shares a runtime with the system it is operating

This repo is an early concrete example of that belief.
