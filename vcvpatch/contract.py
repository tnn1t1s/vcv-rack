"""
AgentRack contract system.

The atomic objects are typed, semantically-grounded ports.
A module is a container for ports and params.
Composition is port-to-port, validated by signal class and semantic role.

Two entry points:
    can_connect(out_port, in_port) -> (bool, str)
    plan_patch(intent, registry)   -> PatchPlan
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Signal class compatibility
# Physical layer: what voltage ranges and signal conventions are compatible.
# Directed: output signal class -> set of acceptable input signal classes.
# ---------------------------------------------------------------------------

SIGNAL_COMPAT: dict[str, set[str]] = {
    "gate":        {"gate"},
    "trigger":     {"gate", "trigger"},           # trigger can drive a gate input
    "cv_unipolar": {"cv_unipolar", "cv"},         # unipolar drives generic cv
    "cv_bipolar":  {"cv_bipolar", "cv_unipolar", "cv"},  # bipolar drives unipolar (loses negative half); drives generic cv
    "cv":          {"cv", "cv_unipolar", "cv_bipolar"},  # generic cv is a supertype -- passthrough modules use this
    "audio":       {"audio"},
}


# ---------------------------------------------------------------------------
# Role compatibility
# Semantic layer: what musical roles can drive what other musical roles.
# Directed: output semantic role -> set of acceptable input semantic roles.
# This is the compatibility graph. It is global and explicit.
# ---------------------------------------------------------------------------

ROLE_COMPAT: dict[str, set[str]] = {
    # Control sources
    "trigger_source":    {"trigger_source"},
    "retrigger_source":  {"retrigger_source"},
    "clock_source":      {"trigger_source", "clock_source"},

    # Envelope / contour
    "envelope_contour":  {
        "amplitude_control",   # VCA cv input
        "filter_cutoff_cv",    # filter FM / cutoff cv
        "wavetable_position",  # wavetable scrub
        "fm_index",            # FM modulation depth
        "modulation_target",   # generic unipolar destination
    },

    # Oscillator / LFO output
    "modulation_source": {
        "amplitude_control",
        "filter_cutoff_cv",
        "wavetable_position",
        "fm_index",
        "pitch_cv",            # vibrato
        "modulation_target",
    },

    # Pitch
    "pitch_cv":          {"pitch_cv"},

    # Terminal roles -- consume a signal, do not pass it further
    "amplitude_control": set(),
    "filter_cutoff_cv":  set(),
    "wavetable_position":set(),
    "fm_index":          set(),
    "modulation_target": set(),
}

# passthrough: transparent to the compatibility graph.
# An Attenuate (or any pure-scaling module) preserves upstream semantics.
# OUT role is passthrough → can drive anything a direct connection could drive.
# Anything can feed IN with role passthrough.
ROLE_COMPAT["passthrough"] = set(ROLE_COMPAT.keys())   # passthrough output drives any role
for _role in list(ROLE_COMPAT.keys()):
    ROLE_COMPAT[_role].add("passthrough")               # any role accepts passthrough from upstream


# ---------------------------------------------------------------------------
# Range adapters
# When signal ranges don't match, declare what adapter is needed.
# ---------------------------------------------------------------------------

@dataclass
class AdapterHint:
    type:  str    # "attenuate" | "scale" | "offset" | "curve_map"
    notes: str


def _adapter_needed(
    out_range: tuple[float, float],
    in_range:  tuple[float, float],
) -> Optional[AdapterHint]:
    out_min, out_max = out_range
    in_min,  in_max  = in_range

    if out_max > in_max * 1.1:
        return AdapterHint(
            type="attenuate",
            notes=(
                f"Output range [{out_min}, {out_max}]V exceeds input range "
                f"[{in_min}, {in_max}]V. Route through Attenuate to scale down."
            ),
        )
    if out_min < in_min - 0.1:
        return AdapterHint(
            type="offset",
            notes=(
                f"Output min {out_min}V below input min {in_min}V. "
                "Route through Attenuate with DC offset to shift up."
            ),
        )
    return None


# ---------------------------------------------------------------------------
# Port and module specs
# ---------------------------------------------------------------------------

@dataclass
class PortSpec:
    name:          str
    direction:     str            # "input" | "output"
    signal_class:  str
    semantic_role: str
    required:      bool  = False
    range_v:       Optional[tuple[float, float]] = None  # volts, if known
    description:   str   = ""


@dataclass
class ParamPreset:
    label:       str
    value:       float
    description: str = ""


@dataclass
class ParamSpec:
    id:          int
    name:        str
    unit:        str              # "seconds" | "Hz" | "volts" | "normalized" | "semitones"
    scale:       str              # "linear" | "log" | "exponential"
    min_val:     float
    max_val:     float
    default:     float
    modulatable: bool = True
    presets:     list[ParamPreset] = field(default_factory=list)
    description: str = ""


@dataclass
class MusicalUse:
    label:       str
    params:      dict[str, float]           # param_name -> value
    routing:     Optional[str] = None       # human-readable routing note
    notes:       str = ""
    # intent transformations: which param goes which direction for this intent
    param_effects: dict[str, str] = field(default_factory=dict)  # param -> "increase"|"decrease"|"zero"|"max"


@dataclass
class ModuleSpec:
    module_id:     str
    name:          str
    version:       str
    category:      str
    summary:       str
    ensemble_role: str            # musical dimension this covers
    ports:         list[PortSpec]
    params:        list[ParamSpec]
    guarantees:    list[str] = field(default_factory=list)   # hard promises
    limitations:   list[str] = field(default_factory=list)   # known failure modes
    musical_uses:  list[MusicalUse] = field(default_factory=list)

    def outputs(self) -> list[PortSpec]:
        return [p for p in self.ports if p.direction == "output"]

    def inputs(self) -> list[PortSpec]:
        return [p for p in self.ports if p.direction == "input"]

    def required_inputs(self) -> list[PortSpec]:
        return [p for p in self.inputs() if p.required]

    def param(self, name: str) -> Optional[ParamSpec]:
        return next((p for p in self.params if p.name == name), None)

    def port(self, name: str) -> Optional[PortSpec]:
        return next((p for p in self.ports if p.name == name), None)


# ---------------------------------------------------------------------------
# can_connect
# ---------------------------------------------------------------------------

@dataclass
class ConnectionResult:
    compatible:     bool
    explanation:    str
    adapter:        Optional[AdapterHint] = None

    def __bool__(self):
        return self.compatible


def can_connect(out_port: PortSpec, in_port: PortSpec) -> ConnectionResult:
    """
    Determine whether out_port can connect to in_port.

    Checks signal class (physical) then semantic role (musical).
    Returns a ConnectionResult with explanation and optional adapter hint.
    """
    assert out_port.direction == "output", f"{out_port.name} is not an output"
    assert in_port.direction  == "input",  f"{in_port.name} is not an input"

    # 1. Signal class check
    allowed_classes = SIGNAL_COMPAT.get(out_port.signal_class, set())
    if in_port.signal_class not in allowed_classes:
        return ConnectionResult(
            compatible=False,
            explanation=(
                f"Signal class mismatch: {out_port.signal_class!r} output "
                f"cannot drive {in_port.signal_class!r} input. "
                f"({out_port.name} → {in_port.name})"
            ),
        )

    # 2. Role check
    allowed_roles = ROLE_COMPAT.get(out_port.semantic_role, set())
    if in_port.semantic_role not in allowed_roles:
        return ConnectionResult(
            compatible=False,
            explanation=(
                f"Role incompatibility: {out_port.semantic_role!r} "
                f"cannot drive {in_port.semantic_role!r}. "
                f"({out_port.name} → {in_port.name})"
            ),
        )

    # 3. Range check
    adapter = None
    if out_port.range_v and in_port.range_v:
        adapter = _adapter_needed(out_port.range_v, in_port.range_v)

    if adapter:
        return ConnectionResult(
            compatible=True,
            explanation=(
                f"Compatible with adapter: {out_port.semantic_role!r} → "
                f"{in_port.semantic_role!r}"
            ),
            adapter=adapter,
        )

    return ConnectionResult(
        compatible=True,
        explanation=(
            f"Compatible: {out_port.semantic_role!r} → {in_port.semantic_role!r} "
            f"({out_port.name} → {in_port.name})"
        ),
    )


# ---------------------------------------------------------------------------
# plan_patch
# ---------------------------------------------------------------------------

@dataclass
class WireStep:
    from_module: str
    from_port:   str
    to_module:   str
    to_port:     str
    adapter:     Optional[AdapterHint] = None


@dataclass
class ParamStep:
    module: str
    param:  str
    value:  float
    unit:   str
    reason: str


@dataclass
class PatchPlan:
    modules:     list[str]
    wires:       list[WireStep]
    params:      list[ParamStep]
    gaps:        list[str]        # ensemble roles not covered
    explanation: list[str]        # agent reasoning trace


def plan_patch(intent: dict, registry: dict[str, ModuleSpec]) -> PatchPlan:
    """
    Given a structured intent and a module registry, produce a patch plan.

    Intent schema:
    {
        "description":      "short pluck on filter cutoff from sequencer gate",
        "ensemble_roles":   ["dynamics"],          # which roles must be covered
        "source_roles":     ["trigger_source"],    # what upstream provides
        "target_roles":     ["filter_cutoff_cv"],  # what the output must drive
        "musical_use":      "pluck",               # look up presets from this label
    }

    Returns a PatchPlan with modules, wires, params, gaps, and reasoning trace.
    """
    trace = []
    modules_used = []
    wires = []
    params = []
    gaps = []

    required_roles = intent.get("ensemble_roles", [])
    target_roles   = intent.get("target_roles", [])
    source_roles   = intent.get("source_roles", [])
    use_label      = intent.get("musical_use")

    trace.append(f"Intent: {intent.get('description', '(no description)')}")
    trace.append(f"Required ensemble roles: {required_roles}")
    trace.append(f"Source roles available: {source_roles}")
    trace.append(f"Target roles needed: {target_roles}")

    # Step 1: find modules that cover required ensemble roles
    for role in required_roles:
        candidates = [
            m for m in registry.values()
            if m.ensemble_role == role
        ]
        if not candidates:
            gaps.append(f"No module found for ensemble role: {role!r}")
            trace.append(f"  GAP: no module covers {role!r}")
            continue

        # pick first candidate (agent would rank by suitability)
        module = candidates[0]
        modules_used.append(module.module_id)
        trace.append(f"  {role!r} → {module.module_id} ({module.name})")

        # Step 2: verify it accepts from source roles
        for src_role in source_roles:
            matching_inputs = [
                p for p in module.inputs()
                if p.semantic_role == src_role
            ]
            if matching_inputs:
                inp = matching_inputs[0]
                trace.append(
                    f"    accepts {src_role!r} at port {inp.name!r} ✓"
                )
                wires.append(WireStep(
                    from_module="[upstream]",
                    from_port=f"[{src_role}]",
                    to_module=module.module_id,
                    to_port=inp.name,
                ))
            else:
                gaps.append(
                    f"{module.module_id} has no input with role {src_role!r}"
                )

        # Step 3: verify output can drive target roles
        for tgt_role in target_roles:
            matching_outputs = [
                p for p in module.outputs()
                if tgt_role in ROLE_COMPAT.get(p.semantic_role, set())
            ]
            if matching_outputs:
                out = matching_outputs[0]
                # construct a synthetic in_port for the target
                in_port = PortSpec(
                    name=f"[{tgt_role}]",
                    direction="input",
                    signal_class=out.signal_class,
                    semantic_role=tgt_role,
                )
                result = can_connect(out, in_port)
                trace.append(f"    {out.name!r} → {tgt_role!r}: {result.explanation}")
                wire = WireStep(
                    from_module=module.module_id,
                    from_port=out.name,
                    to_module="[downstream]",
                    to_port=f"[{tgt_role}]",
                    adapter=result.adapter,
                )
                wires.append(wire)
                if result.adapter:
                    trace.append(
                        f"      adapter required: {result.adapter.type} -- {result.adapter.notes}"
                    )
            else:
                gaps.append(
                    f"{module.module_id} has no output compatible with {tgt_role!r}"
                )
                trace.append(f"    GAP: no output reaches {tgt_role!r}")

        # Step 4: apply musical_use preset if requested
        if use_label:
            use = next(
                (u for u in module.musical_uses if u.label == use_label),
                None
            )
            if use:
                trace.append(f"    applying preset {use_label!r}")
                for pname, pval in use.params.items():
                    ps = module.param(pname)
                    unit = ps.unit if ps else "?"
                    params.append(ParamStep(
                        module=module.module_id,
                        param=pname,
                        value=pval,
                        unit=unit,
                        reason=f"preset {use_label!r}",
                    ))
                    trace.append(f"      {pname} = {pval} {unit}")
                if use.routing:
                    trace.append(f"    routing note: {use.routing}")
            else:
                trace.append(
                    f"    no preset {use_label!r} found in {module.module_id}"
                )

    return PatchPlan(
        modules=modules_used,
        wires=wires,
        params=params,
        gaps=gaps,
        explanation=trace,
    )
