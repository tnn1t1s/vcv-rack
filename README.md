# vcv-rack

An agentic patch-building system for VCV Rack. The project has three layers:
a custom C++ plugin (AgentRack), a Python library for writing patches as code
(vcvpatch), and agent infrastructure for autonomous patch generation.

The design goal is a fully autonomous patch writer: an agent that can compose,
wire, and validate VCV Rack patches programmatically, with no human in the loop
and no reliance on VCV Rack being open at build time.

## Repository layout

```
plugin/AgentRack/     C++ plugin: 14 modules, ~5200 lines
vcvpatch/             Python patch builder + signal graph prover, ~4000 lines
agent/                Agent workflows, tools, and persona configs (Google ADK)
patches/              27+ Python patch scripts (dub techno, chord sequences, demos)
tests/                Python tests, patch fixtures, demo recordings
docs/                 Architecture docs, module references, pattern guides
evals/                Agent evaluation harness
tools/                rack_introspect C++ shim for headless param discovery
```

## AgentRack plugin

14 modules covering oscillators, filters, effects, utilities, and sequencing.
Each module is a single `.cpp` file in `plugin/AgentRack/src/`.

| Module | HP | What it does |
|--------|----|-------------|
| **Attenuate** | 8 | 6-channel CV/audio attenuator. OUT = IN x SCALE. |
| **ADSR** | 8 | Envelope generator with per-stage CV modulation. |
| **Cassette** | 8 | Tape loop player. 4 presets, 3 tape quality modes, variable speed. |
| **Crinkle** | 8 | Buchla 259-style wavefolder oscillator. 5-stage fold, 4x oversampled. |
| **Ladder** | 6 | TB-303-lineage Huovilainen nonlinear ladder filter. SPREAD/SHAPE pole topology. |
| **Noise** | 8 | Six spectral noise generators: white, pink, brown, blue, violet, crackle. |
| **Saphire** | 8 | Fixed-IR convolution reverb (Lex Hall). Overlap-save FFT, TIME/BEND/TONE/PRE. |
| **Sonic** | 8 | BBE-style spectral-phase maximizer. 3-band phase alignment + spectral tilt. |
| **Steel** | 8 | AI-driven wavetable stacker. Sidechain FFT feeds Gemma inference for 16 wavetable weights. |
| **BusCrush** | 12 | 8-channel summing bus with Mackie-style overload. Asymmetric rail clipping, 8x oversampled. |
| **ClockDiv** | 8 | Clock divider: /2, /4, /8, /16, /32 outputs. |
| **Tonnetz** | 12 | Trigger-addressed Tonnetz chord generator. 5x5 lattice, 32 triangles, voice-led triads. |
| **Maurizio** | 6 | Clock-syncable dub delay. Dotted/triplet/straight ratio, HP-filtered feedback, tape saturation. |
| **Inspector** | 4 | Polls AgentModules and writes state JSON for agent introspection. |

Build and install:

```bash
make -C plugin/AgentRack -j4
make -C plugin/AgentRack install
```

Design principles are documented in `plugin/AgentRack/DESIGN_PRINCIPLES.md`.
Key rules: normalize audio at boundaries (DSP in -1..1), constant-power
crossfade for mix controls, never reorder enums, oversample nonlinear DSP.

## vcvpatch library

Python library for building `.vcv` patches programmatically with formal
signal graph validation. Every patch is provably correct before it touches
VCV Rack.

**Core modules:**

- `builder.py` -- `PatchBuilder` fluent API. Declare modules in signal-flow
  order, connect ports by name, compile to `.vcv`.
- `core.py` -- `Patch`, `Module`, `Cable` data structures.
- `serialize.py` -- `.vcv` file I/O (zstd-compressed tar).
- `introspect.py` -- Headless param discovery via `rack_introspect` C++ shim.
- `runtime.py` -- `RackSession` for launching headless Rack, live param
  control via MIDI, and autosave readback.

**Signal graph (`vcvpatch/graph/`):**

- `signal_graph.py` -- `SignalGraph` with always-current properties:
  `audio_reachable`, `patch_proven`, `warnings`.
- `modules.py` -- 70+ node classes declaring audio routing per module.
  `NODE_REGISTRY` maps plugin/model to class.
- `loader.py` -- Load `.vcv` files into a `SignalGraph` for analysis.

**Param discovery (`vcvpatch/discovered/`):**

Param IDs in VCV Rack are raw integers determined by C++ enum order. They
shift if a plugin author inserts a new param. The discovery system solves this:

1. At build time, check `discovered/<plugin>/<model>/<version>.json`
2. On cache miss, run `rack_introspect` (headless C++ shim) to dump param metadata
3. Cache the result, keyed by plugin version (not date)

9 plugins currently cached. Discovery files are committed so CI works without
VCV Rack installed.

## Writing patches

Patches are Python scripts in `patches/`. Each uses `PatchBuilder` to declare
modules and connections, then saves a `.vcv` file.

```python
from vcvpatch.builder import PatchBuilder

pb = PatchBuilder()
clock = pb.module("SlimeChild-Substation", "SlimeChild-Substation-Clock",
                  TEMPO=0.32, RUN=1)
osc = pb.module("AgentRack", "Crinkle", TUNE=0.0, TIMBRE=0.05)
pb.connect(clock.o.Base_clock, osc.i.V_Oct)
pb.build().save("my_patch.vcv")
```

Modules are placed left-to-right in declaration order, matching the visual
signal flow in VCV Rack.

**Example patches:**

| Patch | Description |
|-------|-------------|
| `dub_cm.py` | Basic Channel dub in Cm. Tonnetz chord sequence, Crinkle voices, Ladder filter sweep, Saphire reverb. |
| `eiirp.py` | Radiohead "Everything In Its Right Place" via Tonnetz + Bogaudio PgmrX sequencing. |
| `coltrane.py` | Coltrane changes. |
| `interstellar.py` | Ambient/space patch. |
| `agentrack_demo.py` | Exercises all core AgentRack modules. |
| `saphire_demo.py` | Saphire convolution reverb demonstration. |
| `tonnetz_demo.py` | Tonnetz chord generator demonstration. |

## Agent

The agent layer uses Google ADK to build patches from natural language
descriptions. The root agent (`agent/agent.py`) reasons about signal flow,
selects modules, and calls tools to construct and validate patches.

Agent tools are dumb primitives; the agent provides the intelligence. If a
function would need to call an LLM, that reasoning belongs in the agent, not
the tool.

```bash
cp agent/.env.example agent/.env
# Set OPENROUTER_API_KEY and/or GOOGLE_API_KEY
```

## Recording demos

Record the VCV Rack window with audio using macOS screencapture + BlackHole:

```bash
# Get window bounds
BOUNDS=$(osascript -e 'tell application "System Events" to tell process "VCV Rack 2 Pro" to get {position, size} of front window')

# Record 30 seconds
screencapture -v -V 30 -R "x,y,w,h" -G "BlackHole2ch_UID" -x output.mov

# Convert for sharing
ffmpeg -i output.mov -vf "scale=1280:-2" -c:v libx264 -crf 23 -c:a aac -b:a 128k -movflags +faststart output.mp4
```

Requires BlackHole 2ch (`brew install blackhole-2ch`) and a Multi-Output
Device (Volt 2 + BlackHole) configured in Audio MIDI Setup. VCV Rack's
AudioInterface2 must be set to the Multi-Output Device.

Do not use ffmpeg + avfoundation for BlackHole audio capture; it produces
warbly audio. macOS native screencapture is the only working approach.

## Getting started

```bash
uv sync                              # Python dependencies
make -C plugin/AgentRack -j4         # Build plugin
make -C plugin/AgentRack install     # Install to VCV Rack
uv run pytest                        # Run tests
```

## Key constraints

- Patches must be provable without opening VCV Rack (`graph.patch_proven == True`)
- No hardcoded param IDs; use named params via the discovery system
- Attenuator params must be opened when connecting CV
- `UnknownNode` is opaque: blocks audio propagation, prevents proof
- Modules are declared in signal-flow order (source to output, left to right)
