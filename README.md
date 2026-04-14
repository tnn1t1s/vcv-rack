# vcv-rack

`vcv-rack` is a working repository for building VCV Rack patches as code,
testing signal-graph behavior, and developing a custom Rack plugin named
AgentRack.

The repo has three primary layers:

- `vcvpatch/`: Python library for constructing `.vcv` patches, loading module
  metadata, and reasoning about patch structure
- `agent/`: local agent workflows for patch generation, collaboration, and
  publishing tasks
- `plugin/AgentRack/`: custom C++ Rack plugin focused on clear contracts,
  consistent DSP, and agent-friendly module design

## Repository Map

- `vcvpatch/`: patch builder, graph model, introspection, runtime helpers
- `agent/`: agent entrypoints, prompts, tools, and tests
- `plugin/AgentRack/`: plugin source, assets, unit tests, design principles
- `tests/`: Python regression tests plus `.vcv` fixture patches
- `patches/`: example patches, loop packs, and other working material
- `docs/`, `design/`, `research/`, `techniques/`: reference and design notes
- `vendor/`: Rack SDK, `llama.cpp`, and other vendored dependencies

## Getting Started

The Python side of the repo uses `uv`.

```bash
uv sync
```

If you are using the agent workflows, copy the environment template first:

```bash
cp agent/.env.example agent/.env
```

Common keys used in this repo:

- `OPENROUTER_API_KEY`
- `GOOGLE_API_KEY`

## Python Workflows

Run the default Python test suite with:

```bash
uv run pytest
```

Some tests are marked `eval` and require external services or credentials.

`vcvpatch` is the core programmatic patch layer. It is used to:

- create modules and cables in `.vcv` patches
- describe and check graph structure
- consume discovered module metadata
- support agent-written patch construction

The committed `vcvpatch/discovered/` tree is intentionally small. Treat module
metadata generation as a reproducible workflow, not a giant static cache.

## Agent Workflows

`agent/` contains local workflows for building patches, coordinating
multi-step runs, and generating publishing artifacts such as screenshots.

See `agent/README.md` for the agent-specific view.

## AgentRack Plugin

`plugin/AgentRack` is the custom VCV Rack plugin in this repo.

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

Build it with:

```bash
make -C plugin/AgentRack -j4
```

Run the focused C++ tests with:

```bash
make -C plugin/AgentRack/tests
./plugin/AgentRack/tests/test_signal_cv
./plugin/AgentRack/tests/test_fft
```

The design rules for new modules live in
`plugin/AgentRack/DESIGN_PRINCIPLES.md`.

## Project Conventions

- `uv.lock` is committed on purpose for reproducible installs.
- Rack-native metadata is preferred over handwritten parallel interface layers.
- AgentRack shared code should grow from small semantic components, not loose
  helper piles or speculative frameworks.
- The repo contains both production-facing code and active working material, so
  prefer documented entry points over guessing from every directory.
