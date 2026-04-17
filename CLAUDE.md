# VCV Rack Project

## Goal

Build a **fully agentic, autonomous VCV Rack patch writer** -- an agent that can
compose, wire, and validate patches programmatically with:

- No human in the loop
- No screen scraping, no Playwright, no vision-based inspection
- No reliance on VCV Rack being open or observable at runtime

The agent should be able to reason about signal flow, prove correctness formally,
and produce `.vcv` patch files that work on first open.

## Agents

| Agent | Doc | Purpose |
|-------|-----|---------|
| `vcv_patch_builder` (root) | `agent/root_agent.py` | Builds and proves patches from musical descriptions |
| `vcv_publish` | `agent/publish_agent.md` | Screenshots, cropping, publishing |

## Architecture

`vcvpatch/` -- Python library for building and proving patches

- `Patch` -- high-level builder (modules, cables, named params)
- `graph/` -- formal signal graph with always-current proof properties
  - `SignalGraph` -- nodes + edges, properties: `audio_reachable`, `patch_proven`, `warnings`
  - `modules.py` -- one class per supported module; declares audio routing, required CV, attenuator map
  - `NODE_REGISTRY` -- plugin/model -> class, used by PatchLoader
- `registry.py` -- named param/port/output mappings (plugin/model -> {name: id})
- `serialize.py` -- `.vcv` file I/O (zstd-compressed tar)
- `discover_params.py` -- runtime param discovery via VCV Rack autosave (one-time, offline use)
- `runtime.py` -- headless Rack process management, MIDI param control, autosave readback

## Param ID Discovery

VCV Rack stores params as raw integer IDs with no names in JSON. The correct IDs
come from C++ enum order in each module's source.

### The versioning problem

Param IDs are determined by C++ enum order. If a plugin author inserts a new param,
all subsequent IDs shift. A stale registry produces silently wrong patches -- no
error, just the wrong knob set.

**Version is the invariant, not date.** Plugin versions come from `plugin.json`
in the installed plugin directory.

### Two-layer architecture

```
vcvpatch/
  discovered/               # machine-generated, never hand-edited
    Fundamental/
      VCO/
        2.6.6.json          # {params:[{id,name,default,min,max}], plugin_version, discovered_at}
  registry.py               # human layer: port/output names and aliases only
```

### Discovery flow (fully automatic)

1. At patch-build time, read installed plugin version from `plugin.json`
2. Check `discovered/<plugin>/<model>/<version>.json` -- cache hit: use it
3. Cache miss or version mismatch: run `rack_introspect <plugin> <model>` (C++ shim)
4. Shim instantiates module headlessly, dumps `{id, name, min, max, default}` as JSON
5. Cache the result; use it

### rack_introspect shim

A small C++ binary (~80 lines) that:
- Links against `libRack.dylib`
- Creates a stubbed `rack::App` context (no GUI, no engine)
- Loads the plugin dylib and calls `plugin->init()`
- Calls `model->createModule()`, reads `module->paramQuantities`
- Prints JSON to stdout

Names come from `paramQuantity->name` -- no manual annotation ever needed.
The `discovered/` files are committed to the repo so CI and machines without
VCV Rack installed can use cached metadata (version-matched).

## Module Selection Criterion: Introspectability

`is_introspectable(plugin, model)` is a first-class filter for the agent.

A module is introspectable when `rack_introspect` can headlessly instantiate it
and dump its full param metadata. Modules that crash during `createModule()`
(typically because they access the GUI or filesystem at init time) are recorded
in `discovered/<plugin>/<model>/failed.<version>.json` and flagged as
non-introspectable.

**If a module is not introspectable, the agent cannot prove its params are
correctly initialized.** Prefer alternatives:

| Non-introspectable (avoid) | Preferred alternative |
|----------------------------|-----------------------|
| ImpromptuModular/Foundry   | ImpromptuModular/Clocked-Clkd + SEQ3 |
| ImpromptuModular/Phrase-Seq-16 | Bogaudio/Bogaudio-AddrSeq |
| ImpromptuModular/Phrase-Seq-32 | Bogaudio/Bogaudio-AddrSeq |
| ImpromptuModular/Gate-Seq-64 | Bogaudio/Bogaudio-PgmrX |
| Befaco/NoisePlethora       | Fundamental/Noise |
| dbRackModules/MVerb        | Valley/Plateau |

This list grows automatically as new failures are discovered.
Run `python3 tools/populate_cache.py` after installing new plugins.

## Runtime Interaction

The agent can launch patches headlessly and interact with a running Rack process.
See `docs/runtime-interaction.md` for full details.

### Agent tools

| Tool | Description |
|------|-------------|
| `launch_patch(path, control_params_json)` | Launch Rack headlessly; optionally inject `Core/MidiMap` for live CC control |
| `set_param_live(module, param, value)` | Change a param in running Rack (MIDI CC or stop-patch-relaunch) |
| `read_live_state()` | Read all current param values from the Rack autosave |
| `stop_rack()` | Terminate the headless Rack process |

### Typical workflow

```
compile_and_save tests/my_patch.vcv
launch_patch tests/my_patch.vcv '[{"name": "vco.FREQ", "cc": 1, "min": -2, "max": 2}]'
set_param_live vco FREQ 0.5
read_live_state
stop_rack
```

### Python API example

```python
from vcvpatch.runtime import RackSession

with RackSession("tests/my_patch.vcv") as sess:
    sess.launch(timeout=15.0)
    val = sess.read_param(module_id, param_id)
    sess.set_param(module_id, param_id, 0.8, min_val=0.0, max_val=1.0)
```

### Key facts

- Readiness detection: polls `~/Library/Application Support/Rack2/autosave/patch.json`
  until module count matches; no log parsing
- `Core/MidiMap` is a `ControllerNode` with no required CV -- adding it never
  affects `patch_proven`
- MIDI live control requires `pip install mido python-rtmidi` and a one-time
  CoreMIDI driver ID calibration; the stop-patch-relaunch fallback always works
- `reset_patch` and `stop_rack` both stop any running Rack process

## Agent Behavior: Keep Reasoning in the Agent, Not in Tools

When building ADK agents, tools must be dumb primitives. The agent provides the intelligence.

**If you find yourself writing a function that calls an LLM inside a tool, stop.** That reasoning belongs in the agent. Examples of what belongs where:

| Belongs in the agent | Belongs in a tool |
|----------------------|-------------------|
| Deciding what region to crop | `crop_image(src, dst, x, y, w, h)` |
| Choosing which modules to connect | `connect_audio(from, to)` |
| Interpreting a screenshot | `screenshot_window()` |

**When testing agents, run through the agent runner -- not by importing and calling tool functions directly.** Calling tools directly bypasses the agent's reasoning loop and proves nothing about agent behavior.

**When given a choice between a more agentic and a less agentic approach, pick the more agentic one.** The whole point of the agent architecture is to put decisions in the model, not in code.

## Agent Behavior: Don't Fake Progress

When a required mechanism is unknown or unverified, **stop and investigate -- do not
implement a fallback that looks like it works but doesn't solve the actual problem.**

Specific patterns to avoid:

- **Fallback theater**: building a file-editing workaround when the goal is live
  runtime interaction, then calling it "runtime control." The fallback hides the
  unsolved problem.
- **Deferred calibration**: shipping code with "one-time setup required" that
  blocks the feature from actually working. If setup is required, do the setup
  first or declare the feature not yet implemented.
- **Planning to appear productive**: if the correct IPC mechanism is unknown,
  the right action is `AskUserQuestion` or a targeted investigation -- not
  implementing the path of least resistance.

Before implementing any new interaction mechanism, verify it works end-to-end
on this machine first. A 10-line proof-of-concept that actually runs beats
300 lines of plausible-looking code that silently does the wrong thing.

## Discord channel: #vcv-rack-devs

This project posts updates to Discord. Tools are in `~/home/bin/` - see `~/CLAUDE.md`
for full docs (Discord bot section).

**Post a message:**
```bash
discord-notify vcv-rack-devs "message"
discord-notify vcv-rack-devs --title "Title" --body "body" --color success
```

Attach a file (any type - images render inline, .vcv/.wav/etc post as downloads):
```bash
discord-notify vcv-rack-devs --file /path/to/patch.vcv --body "new patch"
discord-notify vcv-rack-devs --file /path/to/plot.png --title "Results"
```

Read the channel:
```bash
discord-read vcv-rack-devs           # last 10 messages
discord-read vcv-rack-devs -n 20 --reverse
discord-read vcv-rack-devs --json | jq '.content'
```

Colors: success (green), error (red), warning (yellow), info (blurple)

When to post unprompted: finishing a significant task, producing a plot or output
file, completing a build, or hitting an error worth surfacing. Keep it short.

## Key Constraints

- Patches must be provable without opening VCV Rack: `graph.patch_proven == True`
- No hardcoded magic numbers; use named params via `registry.py`
- Attenuator params must be opened when connecting CV (see `docs/module-param-patterns.md`)
- `UnknownNode` is opaque: blocks audio propagation, prevents proof
- When inspection outside the repo is necessary, only look in:
  - this repo
  - `/Users/palaitis/Library/Application Support/Rack2`
- Do not search unrelated user directories such as `Documents`, `Pro Tools`, or
  other music/project folders. They can contain misleading files and should be
  treated as out of scope for VCV work.

## Patch Layout Convention

**Always declare modules in signal flow order** -- left to right as they would appear
on the rack. The builder assigns positions in declaration order, so the visual layout
in VCV Rack directly reflects the signal chain.

Convention: source → pitch/gate generators → audio processors → effects → audio output

Example: `sampler → resonator → texture → ladder → saphire → audio`

Add a comment at the top of the cables section: `# Signal flow: a -> b -> c -> d`
