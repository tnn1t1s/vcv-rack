# vcv-rack

This repo is for making VCV Rack patches, building a custom Rack plugin, and
supporting agent-driven patch workflows.

The main things in here are:

- `plugin/AgentRack/`: the custom C++ plugin
- `vcvpatch/`: the Python library for building `.vcv` patches as code
- `agent/`: local agent workflows and supporting tools
- `tests/`: Python tests and patch fixtures
- `patches/`: saved patches, demos, loop material, and working examples

## What This Repo Is

This is not a generic VCV Rack tutorial repo.

It is a working project for:

- writing and testing Rack patches in code
- developing AgentRack modules
- keeping patch examples, experiments, and supporting material in one place

## Getting Started

The Python side of the repo uses `uv`.

```bash
uv sync
```

If you want to use the local agent workflows:

```bash
cp agent/.env.example agent/.env
```

Common keys used here:

- `OPENROUTER_API_KEY`
- `GOOGLE_API_KEY`

## Python

Run the default Python tests with:

```bash
uv run pytest
```

`vcvpatch/` is the code layer for building `.vcv` patches, loading discovered
module data, and checking patch structure.

## AgentRack

`plugin/AgentRack/` is the custom plugin in this repo.

Current modules:

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

Run the focused C++ tests with:

```bash
make -C plugin/AgentRack/tests
./plugin/AgentRack/tests/test_signal_cv
./plugin/AgentRack/tests/test_fft
```

Design notes for AgentRack live in:

```text
plugin/AgentRack/DESIGN_PRINCIPLES.md
```

## Notes

- `uv.lock` is committed on purpose.
- `vcvpatch/discovered/` is intentionally kept small in git.
- The repo includes both stable code and active working material.
