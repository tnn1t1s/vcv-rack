# AgentRack: Rack-Native Design

## The invariant

This must run inside VCV Rack.

That kills any design that assumes a separate runtime, a non-Rack patch graph,
or modules that don't behave like normal Rack modules. It also kills
GUI-scraping as an integration path.

What it forces: **augment, don't replace.**

A module must be simultaneously:
- Fully normal to a human Rack user (params, cables, widgets, save/load)
- Fully legible to an agent (typed ports, semantic roles, behavioral guarantees)

That is much stronger than building a parallel system. And it is the correct
strategic bet: "self-describing VCV Rack modules for agentic composition" is
legible and adoptable. "New abstract synth language" is not.

---

## What a Rack module already has

```
configParam(id, min, max, default, label, unit)
configInput(id, label)
configOutput(id, label)
params[]     -- float values, serialized in patch JSON
inputs[]     -- port voltage arrays
outputs[]    -- port voltage arrays
```

This is the Rack surface. An agent cannot use it because:
- Labels are for human eyes, not typed semantics
- Port IDs are opaque integers derivable only from enum order
- Units are strings in the label, not queryable
- Behavior is in the DSP code, not declared anywhere
- Compatibility is not expressed at all

The missing thing is a **semantic overlay**: a second description of the same
module that speaks to agents rather than humans.

---

## The three-layer architecture

### Layer 1: Rack surface (normal, unchanged)

The usual C++ implementation. Nothing special. A human opens this module and
uses it exactly as any other Rack module.

```cpp
struct ADSR : Module {
    enum ParamId  { ATTACK, DECAY, SUSTAIN, RELEASE, NUM_PARAMS };
    enum InputId  { GATE_INPUT, RETRIG_INPUT, NUM_INPUTS };
    enum OutputId { ENV_OUTPUT, NUM_OUTPUTS };

    void process(const ProcessArgs& args) override { /* DSP */ }
};
```

The enum order *is* the port ID. That must be documented and never changed
after release. This is the one hard constraint the Rack model imposes:
port IDs are stable by convention, not by enforcement.

### Layer 2: Agent surface (the manifest)

A static JSON document compiled into the plugin (or shipped alongside it as
`agentrack.adsr.v1.manifest.json`). It describes the module's Rack surface
in agent-legible terms.

The manifest does not add new behavior. It describes existing behavior
semantically. A human user is unaffected by its presence.

```json
{
  "module_id":     "agentrack.adsr.v1",
  "rack_plugin":   "AgentRack",
  "rack_model":    "ADSR",
  "ensemble_role": "dynamics",

  "params": [
    {
      "rack_id":      0,
      "rack_label":   "Attack",
      "name":         "attack",
      "unit":         "seconds",
      "scale":        "linear",
      "min":          0.001,
      "max":          10.0,
      "default":      0.01,
      "semantic_role": "attack_time"
    }
  ],

  "inputs": [
    {
      "rack_id":      0,
      "rack_label":   "Gate",
      "name":         "gate_in",
      "signal_class": "gate",
      "semantic_role": "trigger_source",
      "required":     true
    }
  ],

  "outputs": [
    {
      "rack_id":      0,
      "rack_label":   "Env",
      "name":         "env_out",
      "signal_class": "cv_unipolar",
      "semantic_role": "envelope_contour",
      "range_v":      [0.0, 10.0]
    }
  ],

  "guarantees": [
    "output is always in [0, 10] V",
    "output is exactly 0V in idle state",
    "attack phase is strictly monotonic increasing"
  ],

  "limitations": [
    "not suitable for audio-rate modulation",
    "parameter modulation takes effect at next phase boundary"
  ]
}
```

Key: `rack_id` maps every manifest entry back to an actual Rack port/param ID.
The manifest is the bridge between the Rack integer namespace and the agent's
semantic namespace.

### Layer 3: Bridge API (runtime introspection)

A small, standard interface that an external agent (or an in-Rack helper
module) can call to query any manifest-bearing module at runtime.

Two mechanisms:

**A. Static (file-based):** The manifest lives in a known location alongside
the plugin dylib. The agent reads it before the patch runs. This is how the
Python contract system works today: read manifest, plan patch, emit `.vcv`.

**B. Dynamic (in-process):** A base class `AgentModule` exposes a virtual
method `getManifest()` that returns the manifest as a string. An in-Rack
"Inspector" module queries all other modules in the patch via the Rack engine
API and exposes a JSON endpoint (HTTP or websocket) the external agent polls.

```cpp
// Base class every AgentRack module inherits
struct AgentModule : Module {
    virtual std::string getManifest() const = 0;

    // Called by Inspector module
    json_t* getAgentJson() const {
        return json_loads(getManifest().c_str(), 0, nullptr);
    }
};
```

```cpp
// ADSR implementation
struct ADSR : AgentModule {
    std::string getManifest() const override {
        return R"({
            "module_id": "agentrack.adsr.v1",
            "rack_plugin": "AgentRack",
            ...
        })";
    }
};
```

The Inspector module (a plain Rack module with no audio jacks) periodically
writes a `manifest_dump.json` to a known path in the Rack data directory.
The external agent polls this file. No separate process, no non-Rack protocol.
This is how the autosave readback works today -- same pattern, different data.

---

## What the agent does with this

Before the patch runs (static path):
1. Load manifests for available modules from disk
2. Run `plan_patch(intent, registry)` -- already implemented in `vcvpatch/contract.py`
3. Emit `.vcv` patch file with correct Rack port IDs from `manifest.rack_id`
4. Rack IDs come from the manifest, not from guessing or source inspection

After the patch runs (dynamic path):
1. Inspector module writes `manifest_dump.json` with current param values
2. Agent reads dump: knows what every param value is in semantic terms
3. Agent calls `set_param` via MIDI or autosave reload

The two paths compose. The static path proves the patch is correctly wired.
The dynamic path reads and adjusts it at runtime.

---

## What this does NOT require

- A new patch file format (`.vcv` is unchanged)
- A new cable protocol (Rack cables work normally)
- A non-Rack runtime (everything runs in the Rack process)
- GUI scraping (manifests are machine-readable from disk or via Inspector)
- Source inspection (manifests are authored once by the module developer)

A human user opens an AgentRack patch and sees normal modules, normal cables,
normal params. The manifest is invisible to them. The Inspector module (if
present) is just another small module in the patch.

---

## The minimal viable build

Three artifacts, in order:

**1. Manifest schema** (JSON Schema for the manifest format)
So manifests can be validated and versioned. Already sketched above.

**2. AgentModule C++ base class**
`getManifest()` virtual method. Static manifest for ADSR. Compile it.

**3. Inspector module**
Polls all `AgentModule` instances in the patch, dumps their manifests plus
current param values to `~/.rack2/agentrack_state.json`. No network,
no new protocol. The external agent reads that file.

With those three, the system is end-to-end:

```
agent reads manifests → plans patch → emits .vcv → Rack runs it →
Inspector dumps state → agent reads state → agent updates params
```

That is the closed loop. Everything after that is refinement.

---

## The unchanged success criterion

"Can a real Rack plugin expose enough information for an agent to patch and
control it without source inspection or GUI scraping?"

The manifest answers the first part (patch planning).
The Inspector answers the second part (runtime state).

The ADSR pluck test already passes in the Python contract system.
The next test is the same test, but with a real `.vcv` file containing real
`rack_id` values instead of placeholder port names.
