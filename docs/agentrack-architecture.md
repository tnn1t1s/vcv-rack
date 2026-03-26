# AgentRack: Decoupled Architecture

## The problem with the previous design

The manifest contained `rack_id`, `rack_plugin`, `rack_model`.
The bridge API wrote to the Rack autosave path.
The Inspector module was Rack-specific.

VCV Rack had leaked into the contract layer.

That means the contract only works for Rack. A future runtime -- Max/MSP,
hardware, a browser-based synth, a different modular format -- would need
a new contract system. The design would have to be redone, not extended.

The fix: **separate the contract from the projection.**

---

## Monadic framing

The contract is the pure value.
The runtime is an effect context.
The adapter interprets the contract in that context.

```
contract  →  projection  →  interpreter/adapter
(pure)       (context map)  (execution in context)
```

VCV Rack is not a "projection target." It is an interpreter context. The
projection is a structure-preserving map from the pure contract into that
context -- it realizes the abstract semantic in concrete runtime terms
without modifying or coupling the contract itself.

---

## Three distinct layers

```
┌─────────────────────────────────────────────┐
│              CONTRACT LAYER                  │  ← runtime-agnostic
│  Manifest schema, port types, role graph,   │
│  can_connect, plan_patch, PatchPlan         │
└──────────────────┬──────────────────────────┘
                   │  PatchPlan (semantic)
                   ▼
┌─────────────────────────────────────────────┐
│             ADAPTER INTERFACE                │  ← abstract boundary
│  resolve(manifest, port_name) → id          │
│  emit(plan) → runtime patch format          │
│  read_state() → semantic dict               │
│  set_param(module, param, value)            │
└──────┬─────────────────────┬────────────────┘
       │                     │
       ▼                     ▼
┌─────────────┐     ┌────────────────┐
│  VCV Rack   │     │  Future        │  ← concrete projections
│  Adapter    │     │  Runtime       │
│             │     │  Adapter       │
│  .vcv JSON  │     │  (Max, SC,     │
│  rack_id    │     │  hardware...)  │
│  autosave   │     │                │
└─────────────┘     └────────────────┘
```

The contract layer does not import the adapter layer.
The adapter layer does not modify the contract layer.
The agent operates entirely in the contract layer and calls the adapter
only to emit and observe.

---

## The contract layer (runtime-agnostic)

The manifest describes what a module IS. No runtime knowledge.

```yaml
# agentrack.adsr.v1.manifest.yaml
module_id:     "agentrack.adsr.v1"
name:          "ADSR Envelope"
ensemble_role: "dynamics"

ports:
  - name:          gate_in
    direction:     input
    signal_class:  gate
    semantic_role: trigger_source
    required:      true

  - name:          env_out
    direction:     output
    signal_class:  cv_unipolar
    semantic_role: envelope_contour
    range_v:       [0.0, 10.0]

params:
  - name:    attack
    unit:    seconds
    scale:   linear
    min:     0.001
    max:     10.0
    default: 0.01

  - name:    decay
    unit:    seconds
    scale:   linear
    min:     0.001
    max:     10.0
    default: 0.2

  - name:    sustain
    unit:    normalized
    scale:   linear
    min:     0.0
    max:     1.0
    default: 0.7

  - name:    release
    unit:    seconds
    scale:   linear
    min:     0.001
    max:     20.0
    default: 0.3

guarantees:
  - "output is always in [0, 10] V"
  - "output is exactly 0V in idle state"
  - "attack phase is strictly monotonic increasing"
  - "sustain=0 makes envelope fully percussive"
```

No `rack_id`. No plugin name. No runtime path. This file works equally for
VCV Rack, Max/MSP, a hardware ADSR, or a software simulator. The contract
describes the module's semantic interface, nothing else.

---

## The adapter interface (abstract boundary)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ResolvedPort:
    """A port as understood by a specific runtime."""
    runtime_id:   Any       # int in Rack, string in Max, address in hardware
    runtime_name: str       # what the runtime calls this port


@dataclass
class ResolvedParam:
    """A param as understood by a specific runtime."""
    runtime_id:   Any
    runtime_name: str
    runtime_min:  float
    runtime_max:  float


class RuntimeAdapter(ABC):

    @abstractmethod
    def resolve_port(self, module_id: str, port_name: str) -> ResolvedPort:
        """Map a manifest port name to a runtime port identifier."""

    @abstractmethod
    def resolve_param(self, module_id: str, param_name: str) -> ResolvedParam:
        """Map a manifest param name to a runtime param identifier."""

    @abstractmethod
    def emit(self, plan: "PatchPlan") -> Any:
        """Translate a semantic PatchPlan into a runtime-specific patch artifact."""

    @abstractmethod
    def read_state(self) -> dict:
        """Read current module/param state in semantic terms (param_name → value)."""

    @abstractmethod
    def set_param(self, module_id: str, param_name: str, value: float) -> None:
        """Set a parameter by semantic name and value in declared units."""
```

The agent calls this interface. It never touches Rack-specific code.

---

## The VCV Rack projection (one concrete adapter)

The Rack projection adds the runtime-specific knowledge that the manifest
intentionally omits.

```yaml
# agentrack.adsr.v1.rack-projection.yaml
module_id:   "agentrack.adsr.v1"
runtime:     "vcv-rack"
rack_plugin: "AgentRack"
rack_model:  "ADSR"

port_map:
  gate_in:   {rack_id: 0}
  retrig_in: {rack_id: 1}
  env_out:   {rack_id: 0}

param_map:
  attack:  {rack_id: 0, rack_min: 0.001, rack_max: 10.0}
  decay:   {rack_id: 1, rack_min: 0.001, rack_max: 10.0}
  sustain: {rack_id: 2, rack_min: 0.0,   rack_max: 1.0}
  release: {rack_id: 3, rack_min: 0.001, rack_max: 20.0}
```

```python
class VCVRackAdapter(RuntimeAdapter):

    def resolve_port(self, module_id, port_name):
        projection = self._load_projection(module_id)
        entry = projection["port_map"][port_name]
        return ResolvedPort(
            runtime_id=entry["rack_id"],
            runtime_name=port_name,
        )

    def emit(self, plan):
        """Build a .vcv patch JSON from a semantic PatchPlan."""
        # Translate plan.wires using resolve_port → cable entries with rack_id
        # Translate plan.params using resolve_param → param entries with rack_id
        # Return .vcv-compatible dict
        ...

    def read_state(self):
        """Read Rack autosave, map rack param IDs back to semantic names."""
        autosave = self._read_autosave()
        # Invert param_map: rack_id → param_name → value
        ...

    def set_param(self, module_id, param_name, value):
        """Send MIDI CC or trigger autosave reload."""
        projection = self._load_projection(module_id)
        rack_id = projection["param_map"][param_name]["rack_id"]
        # dispatch via MIDI or autosave
        ...
```

A future `MaxMSPAdapter` would implement the same interface, reading a
`agentrack.adsr.v1.max-projection.yaml` that maps port names to Max patcher
inlets and param names to `[param]` objects.

---

## What the agent does

```python
# Agent operates entirely in the contract layer
registry = load_manifests("manifests/")
plan = plan_patch(intent, registry)          # pure contract, no runtime

# Only at execution time does the adapter appear
adapter = VCVRackAdapter(projections_dir="projections/vcv-rack/")
patch_file = adapter.emit(plan)             # .vcv JSON
patch_file.save("my_patch.vcv")

# Later, at runtime
state = adapter.read_state()                # semantic param names and values
adapter.set_param("agentrack.adsr.v1", "attack", 0.001)
```

The agent never sees `rack_id`. It reasons in `port_name`, `param_name`,
`signal_class`, `semantic_role`. The adapter translates silently.

---

## Why this matters beyond VCV Rack

The same manifest describes an ADSR for any modular system that builds a
projection. The contract captures what an ADSR IS. A Rack ADSR and a Max ADSR
and a hardware Eurorack ADSR all answer to the same manifest. An agent that
plans a patch in terms of `envelope_contour → filter_cutoff_cv` can emit that
plan to any of them.

This is not speculative. The invariant ("must run in VCV Rack") is satisfied
because the Rack adapter is a complete, concrete projection. But it is not the
only valid projection. The architecture is honest about that.

---

## The file structure

```
vcvpatch/
  contract.py          ← manifest schema, port types, can_connect, plan_patch
  adapter.py           ← RuntimeAdapter abstract interface
  adapters/
    vcv_rack.py        ← VCVRackAdapter
    max_msp.py         ← (future)
  models/
    adsr.py            ← manifest as Python object
manifests/
  agentrack.adsr.v1.manifest.yaml    ← canonical, runtime-agnostic
projections/
  vcv-rack/
    agentrack.adsr.v1.rack-projection.yaml   ← Rack-specific IDs
  max-msp/
    agentrack.adsr.v1.max-projection.yaml    ← (future)
```

Manifests ship once. Projections ship per runtime. The agent reads manifests.
The adapter reads projections.
