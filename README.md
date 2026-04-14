# vcv-rack

This repo is a working environment for building, testing, and reasoning about
VCV Rack patches programmatically.

It has three main parts:

- `vcvpatch/`: a Python library for constructing `.vcv` patches, inspecting
  module metadata, and proving signal-graph structure
- `agent/`: agent-oriented workflows for building patches and related outputs
- `plugin/AgentRack/`: a custom Rack plugin with modules designed around clear
  contracts, DSP consistency, and machine-legible structure

This is not just a tutorial repo anymore. The older tutorial material still
exists under `tutorial/`, but the top-level project is now primarily a patch
construction and AgentRack development workspace.

## Layout

- `vcvpatch/`: patch builder, graph model, introspection, and runtime helpers
- `agent/`: patch-building and publishing agents plus local collaboration tools
- `plugin/AgentRack/`: C++ Rack plugin and module assets
- `tests/`: Python tests, fixture patches, and a few rendered demo artifacts
- `patches/`: curated example patches and supporting media
- `docs/`, `design/`, `techniques/`, `research/`: notes, architecture, and
  working documents
- `vendor/`: third-party dependencies such as Rack SDK and `llama.cpp`

## Setup

The repo uses `uv` as a first-class Python workflow.

```bash
uv sync
```

If you are working on the agent flows, copy the local env template and fill in
the keys you actually need:

```bash
cp agent/.env.example agent/.env
```

Key dependencies currently include:

- `OPENROUTER_API_KEY` for some agent/eval workflows
- `GOOGLE_API_KEY` for Gemini-backed flows such as TTS

## Python Tests

Run the Python test suite with:

```bash
uv run pytest
```

Some tests are live or environment-sensitive. The default local regression path
is still plain `pytest`, but treat eval-marked tests as opt-in unless the
required services and keys are configured.

## AgentRack Plugin

`plugin/AgentRack` is the custom C++ plugin in this repo. Current modules are:

- `Attenuate`
- `ADSR`
- `Cassette`
- `Crinkle`
- `Ladder`
- `Noise`
- `Saphire`
- `Sonic`
- `Steel`
- `BusCrush`
- `ClockDiv`
- `Tonnetz`
- `Maurizio`

Build the plugin with:

```bash
make -C plugin/AgentRack -j4
```

Run the focused AgentRack unit tests with:

```bash
make -C plugin/AgentRack/tests
./plugin/AgentRack/tests/test_signal_cv
./plugin/AgentRack/tests/test_fft
```

The AgentRack design rules live in
`plugin/AgentRack/DESIGN_PRINCIPLES.md`.

## vcvpatch

`vcvpatch` is the Python layer for building `.vcv` patches as code. It is used
for:

- module creation and connection
- graph description and proof-oriented checks
- loading cached/discovered module metadata
- driving patch-generation workflows from agents

The project description in `pyproject.toml` is accurate: this is a
programmatic patch builder with a formal signal-graph emphasis, not just a
collection of saved patches.

## Agent System

The `agent/` directory contains local agent workflows and supporting tools for
patch construction, collaboration, and publishing. See `agent/README.md` for
the current agent-specific view.

At a high level, the agent layer exists to:

- write and execute patch-building code
- coordinate multi-step generation flows
- capture screenshots and publishing artifacts
- support local collaboration without hiding the underlying patch code

## Notes

- `uv.lock` is committed on purpose for reproducible local installs.
- `vcvpatch/discovered/` is intentionally kept minimal in git. Treat metadata
  generation as a recipe/workflow, not a giant static cache.
- The repo contains both experimental and production-oriented material. Prefer
  the documented entry points above over inferring intent from every directory.
