# PRODUCT

This repo should be treated as a product, not just as a codebase.

When we run the agent, we are not only trying to get a patch out.

We are acting like product managers studying:

- how the agent experiences the API
- where the system is legible
- where the system is confusing
- where the agent has to guess
- where the agent can inspect and know
- where prompt has to compensate for weak product design
- where tools are too many, too vague, or too sparse
- where the harness distorts behavior

The patch outcome matters, but it is not the main point.

The patch is often just the artifact produced by the study.

## What We Are Really Evaluating

When an agent runs, the primary questions are:

- What did it inspect first?
- What did it try to guess?
- What did it misunderstand?
- What did it know from the actual runtime/code surface?
- What forced repair loops?
- What caused unnecessary token spend?
- What made the workflow readable and composable?
- What made it brittle?

This means that every agent run is a form of:

- API usability testing
- agent developer experience testing
- harness/runtime testing
- semantic surface validation

Not just “can the model make a cool patch?”

## Product Manager Responsibilities

If you are acting in the product-manager role for this system, your job is to study:

### 1. The path, not just the artifact

Look at:

- planning behavior
- tool calls
- repair loops
- whether the model searched or composed
- how much prompt scaffolding was needed

Do not only look at the final patch.

### 2. Friction

Treat these as product bugs:

- repeated exact-name failures
- tool misuse caused by weak tool naming/docstrings
- module selection guesswork
- prompt bloat compensating for weak system affordances
- harness ambiguity around whether a run is slow, silent, or truly hung

### 3. Constraint handling

The agent should succeed by composing within the real system, not by hallucinating the outside world.

So ask:

- did it reason from the bounded module palette?
- did it use inspectable system truth?
- did it compose from available affordances?

That is better product behavior than free-form world search.

### 4. Cost and iteration quality

For every run, pay attention to:

- turn count
- repair count
- token usage
- long silent turns
- model/provider variance

This is part of product quality, not just operations.

## Good Product Outcomes

A good run is one where:

- the agent plans from the supported environment
- the agent inspects before guessing
- the API makes the right thing obvious
- the model converges with minimal repair
- the final patch is correct

The patch quality matters, but it is downstream of system clarity.

## Bad Product Outcomes

A bad run is one where:

- the patch works, but only after many fragile repairs
- the prompt carries knowledge that should live in code/runtime
- the agent has to guess local module names from general priors
- tool affordances are unclear
- we blame the model for a system design problem

In those cases, the patch result can hide product failure.

## What To Improve First

Prefer improving, in this order:

1. runtime/code-level semantic clarity
2. inspectability
3. tool affordance (name/docstring/schema)
4. harness observability
5. prompt policy
6. model selection

This order matters.

Too many teams do the reverse.

## Product Thesis

This repo is an experiment in agentic software engineering.

The core product question is:

**Can we build a system where an agent works by inspecting and programming a real environment, rather than by compensating for poor design with prompt tricks?**

That is what we are actually trying to answer.

## Cold-Start Recovery Harness

The repo and doc layer are themselves a product surface.

Do not ask only whether the repo is "well documented." Ask whether a fresh
agent with only the visible context surface can recover quickly and become
useful without folklore or babysitting.

That means we should maintain a repeatable cold-start recovery harness:

- give the live agent small, diagnostic orientation tasks
- score whether it can recover basic facts quickly:
  - canonical invocation
  - env path
  - entrypoints
  - workflow constraints
- harden the visible context surface until recovery is fast and reliable

This makes the repo/doc layer something we evaluate and optimize, not just
something we hope is good enough.
