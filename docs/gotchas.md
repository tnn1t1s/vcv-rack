# VCV Rack Patch Builder -- Gotchas

Running log of lessons learned building VCV Rack patches programmatically.
Each entry cites the source file where the lesson was established.

---

## Port IDs come from C++ enum order, NOT addOutput() call order

**What happened:** CountModula/Sequencer16 port IDs were mapped incorrectly by reading the widget constructor's `addOutput()` call sequence instead of the module's `enum OutputIds` block.

**Why:** VCV Rack assigns port IDs by the order entries appear in the `enum OutputIds` (or `enum InputIds`) block in the C++ source. The widget constructor's `addOutput()` calls place ports visually on screen and can appear in a completely different order. The two orderings do not have to match and often do not.

**Rule:** Always read the `enum InputIds` / `enum OutputIds` block in the module's C++ source -- not the widget code. The enum value is the port ID, full stop. For Sequencer16 specifically: `GATE=0, TRIG=1, END=2, CV=3, CVI=4`.

**Source:** `/Users/palaitis/.claude/projects/-Users-palaitis-Development-vcv-rack/memory/reference_countmodula_seq16_ports.md`; inline comment at `/Users/palaitis/Development/vcv-rack/vcvpatch/registry.py` line 844.

---

## Fundamental/SEQ3 GATE params suppress TRIG output only -- CV still advances

**What happened:** Setting SEQ3 GATE params to 0 for some steps was expected to produce a sparse rhythmic pattern (gate fires on some steps, not others). But the pitch CV output still changes on every clock tick regardless of the GATE param state. Only the TRIG output is suppressed on steps where GATE is 0.

**Why:** SEQ3 has a single TRIG output (port 0) and separate CV outputs. The GATE params (ids 28-35) control whether a step fires the TRIG output. They do not hold the CV row outputs steady -- the sequencer advances the CV every clock regardless. So there is no way to use SEQ3 alone to produce both sparse gate patterns and meaningful pitch CVs.

**Rule:** Do not use SEQ3 for sparse gate patterns. Use CountModula/Sequencer16 instead, which has independent per-step gate select params (`GATE{N}`) and a proper held GATE output that controls both the gate signal and pitch advancement. If you need irregular rhythms with SEQ3, pair it with a separate gate sequencer (e.g., CountModula/GateSequencer16).

**Source:** `/Users/palaitis/Development/vcv-rack/vcvpatch/registry.py` SEQ3 entry (params section comment); `/Users/palaitis/Development/vcv-rack/patches/archive/generate_dub_techno.py` (drives ADSR from `seq.TRIG` while setting gate params per step).

---

## MIDI live control requires GUI mode -- headless Rack (-h) does not initialize CoreMIDI

**What happened:** `Core/MidiMap` MIDI-based param control was attempted while Rack ran headlessly with the `-h` flag. The virtual CoreMIDI port opened by Python (`mido.open_output(..., virtual=True)`) was never seen by Rack, so no param changes were delivered.

**Why:** Rack's `-h` (headless) flag skips GUI and audio driver initialization. On macOS this means CoreMIDI is not initialized, so virtual MIDI ports are invisible to Rack even though they exist in the OS MIDI stack.

**Rule:** MIDI live control via `Core/MidiMap` only works when Rack is running in GUI mode (normal launch, not `-h`). The `RackConnection` class is designed for this case: the user opens the patch in Rack normally, then Python connects via the virtual port. For fully headless use (automated tests, CI), use the stop-patch-relaunch fallback: stop Rack, edit the param in the `.vcv` file, relaunch. See `vcvpatch/runtime.py` `RackSession` for the fallback implementation.

**Source:** `/Users/palaitis/Development/vcv-rack/vcvpatch/runtime.py` docstring (lines 1-23, primary workflow note); `/Users/palaitis/Development/vcv-rack/docs/runtime-interaction.md` Caveats section; `CLAUDE.md` Runtime Interaction key facts.

---

## PolySeq DIV-based gates are always regular subdivisions -- cannot produce irregular sparse patterns

**What happened:** PolySeq (SlimeChild-Substation) was chosen to produce a sparse, irregular gate pattern. The module fires its TRIG outputs on every N-th clock tick, where N is the DIV param value. There is no mechanism to skip individual steps.

**Why:** PolySeq's design is polyrhythmic, not step-sequenced. Each divider fires at a fixed integer subdivision of the master clock -- every 1 tick, every 2 ticks, every 3 ticks, etc. The TRIG outputs are always periodic. There are no per-step on/off toggles on the TRIG outputs.

**Rule:** Use PolySeq for polyrhythmic patterns (3:4, 5:7, etc.) where all dividers fire regularly. For sparse or irregular gate patterns (some steps fire, some do not), use CountModula/Sequencer16 (per-step GATE params) or CountModula/GateSequencer16 (8-track × 16-step gate matrix). PolySeq's SEQ outputs are useful for CV sequences that follow polyrhythmic timing.

**Source:** `/Users/palaitis/Development/vcv-rack/docs/modules/slimechild/polyseq.md`; `/Users/palaitis/Development/vcv-rack/vcvpatch/registry.py` PolySeq entry (DIV params 12-15, no per-step gate toggles).

---

## File editing is not live runtime control (don't fake progress)

**What happened:** The runtime param control feature was implemented as "stop Rack, edit the `.vcv` file, relaunch Rack" and presented as live control. The real mechanism -- MIDI CC via `Core/MidiMap` -- had an unsolved prerequisite (CoreMIDI driver ID calibration). Instead of stopping to solve that or declaring the feature unimplemented, a fallback was built that passed surface-level inspection but was useless for the actual goal of real-time parameter adjustment.

**Why:** The fallback hid the unsolved problem. It looked like working code, required no explanation of what was missing, and was easy to build. But it does not deliver the feature (live, no-restart param changes).

**Rule:** If the correct mechanism is unknown or unverified, investigate or say so -- do not build a fallback and call it done. "One-time setup required" is a red flag that the feature does not actually work yet. Before implementing any new integration, run a 10-line proof-of-concept that confirms it works end-to-end. A small proof beats 300 lines of plausible-looking code that silently does the wrong thing.

**Source:** `/Users/palaitis/.claude/projects/-Users-palaitis-Development-vcv-rack/memory/feedback_no_fake_progress.md`; `CLAUDE.md` "Agent Behavior: Don't Fake Progress" section.

---

## UnknownNode blocks audio proof propagation

**What happened:** A module was used in a patch that was not registered in `vcvpatch/graph/modules.py` (not in `NODE_REGISTRY`). The patch builder created an `UnknownNode` for it. `patch_proven` was `False` even though the module was physically wired in the audio chain.

**Why:** `UnknownNode.audio_out_for()` always returns `frozenset()` -- it propagates no audio signal regardless of what is wired to it. The proof system is conservative: it only asserts `audio_reachable` when every node on the audio path is fully modelled. An opaque node on the path means the path is unproven.

**Rule:** Every module on the audio path must have a registered node class in `vcvpatch/graph/modules.py` with correct `_routes` or `_output_types`. If a module you want to use is not registered, add it before building the patch. Do not rely on `UnknownNode` being transparent. Check `graph.unknown_nodes` after loading a patch to surface gaps.

**Source:** `/Users/palaitis/Development/vcv-rack/vcvpatch/graph/node.py` `UnknownNode` class; `/Users/palaitis/Development/vcv-rack/vcvpatch/graph/signal_graph.py` (propagation stops at `UnknownNode`); `CLAUDE.md` Key Constraints.

---

## Attenuator params default to 0 -- a connected CV cable has no effect until the attenuator is opened

**What happened:** An LFO was connected to a VCO FM input. The patch proved (`patch_proven == True`) and the cable was physically wired, but the LFO had no audible effect on the pitch. The FM attenuator param (VCO param id 4) was at its default value of 0, silently blocking the signal.

**Why:** Many VCV Rack modules have CV inputs paired with an attenuator (or attenuverter) param that scales the incoming signal. The attenuator defaults to 0, meaning the CV is connected but multiplied by zero. The patch prover only checks that a required cable is present; it does not verify that the attenuator is open. `SignalGraph.warnings` fires if a port is wired but its paired attenuator is 0.

**Rule:** Always set attenuator params explicitly when connecting CV. Check `Node._port_attenuators` for the module to find which param id is paired with which input port. For VCO FM: set `FM=0.5` (or your desired depth). For VCO PWM: set `PWM=0.5`. Always check `graph.warnings` after building -- a zero-attenuator warning means a connection that looks wired is acoustically a no-op.

**Source:** `/Users/palaitis/Development/vcv-rack/docs/module-param-patterns.md` "The Attenuator Problem" section; `CLAUDE.md` Key Constraints.

---

## Param IDs are version-specific -- a stale registry silently sets the wrong knob

**What happened:** A plugin was updated by the user. The param IDs in a cached `discovered/` file (or hand-written registry entry) no longer matched the installed version because the plugin author inserted a new param in the middle of the C++ enum, shifting all subsequent IDs.

**Why:** VCV Rack stores params as raw integer IDs with no names. Param IDs are determined by C++ enum order. Inserting a new param anywhere but the end shifts every subsequent ID by 1. A stale registry produces no error -- the patch loads, the wrong knobs are set, and everything sounds wrong with no diagnostic.

**Rule:** The invariant is plugin version, not date. Cache files live in `discovered/<plugin>/<model>/<version>.json`. At patch-build time, read the installed plugin version from its `plugin.json` and verify the cache matches. On a cache miss or version mismatch, re-run `rack_introspect` to regenerate the cache. Never hand-edit `discovered/` files. Run `python3 tools/populate_cache.py` after installing or updating plugins.

**Source:** `CLAUDE.md` "Param ID Discovery -- The versioning problem" section; `vcvpatch/registry.py` file-level comment.

---

## Non-introspectable modules cannot be param-proven -- use verified alternatives

**What happened:** A module from ImpromptuModular (e.g., Foundry, Phrase-Seq-16) was selected for a patch. `rack_introspect` crashed during `createModule()` because the module accesses the GUI or filesystem at init time. The module was flagged as non-introspectable. `patch_proven` cannot be `True` for any patch that relies on its params being correctly set.

**Why:** `rack_introspect` runs headlessly with a stubbed `rack::App` context. Some modules assume a full GUI context exists during `createModule()` and crash (segfault or assertion) without it. These modules cannot have their param metadata extracted, so the agent cannot verify param initialization.

**Rule:** Check `is_introspectable(plugin, model)` before selecting a module. Prefer the verified alternatives listed in `CLAUDE.md`: Bogaudio/Bogaudio-AddrSeq instead of ImpromptuModular/Phrase-Seq-16 or Phrase-Seq-32; Valley/Plateau instead of dbRackModules/MVerb; Fundamental/Noise instead of Befaco/NoisePlethora. The non-introspectable list grows automatically as failures are discovered -- check `discovered/<plugin>/<model>/failed.<version>.json`.

**Source:** `CLAUDE.md` "Module Selection Criterion: Introspectability" section.

---

## Build patches through the agent, not by running Python scripts directly

**What happened:** A patch was built by running a Python script directly (e.g., `python3 patches/my_patch.py`). This bypassed the agent's reasoning loop: no plan was generated, no proof was checked interactively, and the agentic workflow was defeated.

**Why:** The agent is the intended interface. It handles the full workflow: generating the construction plan, calling `add_module` / `connect_audio` / etc., proving correctness, compiling, and saving the `.vcv` file. Running scripts directly short-circuits this and proves nothing about agent behavior.

**Rule:** When a user asks to "build a patch" or "create a patch that does X", run the agent (`python3 agent/main.py` or `adk web`) and prompt it with the musical description. Tests (`test_agent_tools.py`) are still run directly -- they test the tool layer, not patch construction.

**Source:** `/Users/palaitis/.claude/projects/-Users-palaitis-Development-vcv-rack/memory/feedback_patch_workflow.md`.

---

## CountModula/Sequencer16: addOutput() call order in the widget differs from enum order

**What happened:** The port IDs for Sequencer16 were mapped by reading the widget constructor call sequence: `addOutput(GATE), addOutput(TRIG), addOutput(CV), addOutput(CVI), addOutput(END)`. This would give `CV=2, CVI=3, END=4`. The actual enum order is `GATE=0, TRIG=1, END=2, CV=3, CVI=4` -- END comes before CV.

**Why:** The widget constructor places END visually between TRIG and CV on screen, which matches the enum order for visual layout. But the call order in the source was `GATE, TRIG, CV, CVI, END` -- differing from the enum. Reading call order instead of enum order produces wrong IDs for CV and CVI.

**Rule:** This is the same lesson as "port IDs come from enum order," applied to a concrete case. For Sequencer16: CV output id is 3 and CVI is 4, not 2 and 3. Always verify against the C++ enum, not the widget code.

**Source:** `/Users/palaitis/.claude/projects/-Users-palaitis-Development-vcv-rack/memory/reference_countmodula_seq16_ports.md`; `/Users/palaitis/Development/vcv-rack/vcvpatch/registry.py` Sequencer16 block comment.

---

## Keep reasoning in the agent, not in tools

**What happened:** A tool function was written that internally called an LLM to decide which modules to connect or how to interpret a result. This put decision-making inside a primitive and made the agent architecture incoherent.

**Why:** Tools must be dumb primitives. The agent provides intelligence. A tool that reasons internally cannot be tested, debugged, or replaced as part of the agent loop. It also defeats the purpose of the agentic architecture -- the model's reasoning must be visible and auditable at the agent level.

**Rule:** If you find yourself writing a function that calls an LLM inside a tool, stop. Move that reasoning into the agent. Tools should do exactly one concrete operation: `crop_image(src, dst, x, y, w, h)`, `connect_audio(from, to)`, `screenshot_window()`. The agent decides what to call and why.

**Source:** `CLAUDE.md` "Agent Behavior: Keep Reasoning in the Agent, Not in Tools" section.

---

## SlimeChild VCA LEVEL defaults to 1 (fully open)

**What happened:** The SlimeChild VCA `LEVEL` param defaults to `1.0`, meaning audio passes through at full gain even with no CV signal. A patch with ENV → VCA CV played continuously because the VCA was always open -- the envelope just added on top of a permanently open gate.

**Why:** Most hardware VCAs are "normally closed" (0V CV = silence). The SlimeChild VCA is "normally open" (LEVEL knob sets a static gain floor, CV modulates on top). If LEVEL=1 and you connect an envelope to CV, you get: constant audio + envelope bump, not: silence → envelope opens → silence.

**Rule:** Always set `LEVEL=0` on SlimeChild VCA when the VCA is envelope-controlled. The envelope CV then becomes the sole source of gain.

**Source:** Empirically discovered while building `patches/curated/subzero.py`.
