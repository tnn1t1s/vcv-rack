"""Inspect the exact semantic API surface of a VCV Rack module."""

from __future__ import annotations

from vcvpatch.graph.modules import NODE_REGISTRY
from vcvpatch.graph.node import SignalType
from vcvpatch.metadata import module_metadata


_NODE_KIND_NAMES = {
    "AudioSourceNode": "audio_source",
    "AudioProcessorNode": "audio_processor",
    "AudioMixerNode": "audio_mixer",
    "AudioSinkNode": "audio_sink",
    "ControllerNode": "controller",
    "PassThroughNode": "passthrough",
}


def _signal_name(value: SignalType) -> str:
    return value.name.lower()


def _simplify_params(entries: list[dict]) -> list[dict]:
    params = []
    for entry in entries:
        api_name = entry.get("api_name")
        if not api_name:
            continue
        params.append(
            {
                "id": int(entry["id"]),
                "api_name": api_name,
                "name": entry.get("name") or api_name,
                "default": entry.get("default"),
                "min": entry.get("min"),
                "max": entry.get("max"),
            }
        )
    return params


def _simplify_ports(entries: list[dict], signal_types: dict[int, str] | None = None) -> list[dict]:
    ports = []
    signal_types = signal_types or {}
    for entry in entries:
        api_name = entry.get("api_name")
        if not api_name:
            continue
        port = {
            "id": int(entry["id"]),
            "api_name": api_name,
            "name": entry.get("name") or api_name,
        }
        signal_type = signal_types.get(int(entry["id"]))
        if signal_type is not None:
            port["signal_type"] = signal_type
        ports.append(port)
    return ports


def inspect_module_surface(plugin: str, model: str) -> dict:
    """
    Inspect a module before patching with it.

    Use this to learn the exact canonical params, inputs, outputs, signal
    types, routes, and proof-relevant requirements for a module before writing
    patch code. This avoids guessing names like Lowpass vs LPF or Frequency vs
    Cutoff_frequency.

    This merges discovered metadata (params/ports) with graph semantics
    (node kind, signal types, routes, required inputs, attenuator mapping).
    """
    key = f"{plugin}/{model}"
    try:
        discovered = module_metadata(plugin, model)
    except ValueError as exc:
        return {"status": "error", "message": str(exc)}

    node_cls = NODE_REGISTRY.get(key)

    kind = None
    routes: list[list[int]] = []
    required_inputs: list[dict] = []
    attenuators: list[dict] = []
    output_signal_types: dict[int, str] = {}
    notes: list[str] = []

    input_names_by_id = {
        int(entry["id"]): entry.get("api_name")
        for entry in discovered.get("inputs", [])
        if entry.get("api_name")
    }

    if node_cls is None:
        notes.append("Not in semantic graph registry; exact names available, but graph proof falls back to UnknownNode.")
    else:
        for base in node_cls.__mro__:
            mapped = _NODE_KIND_NAMES.get(base.__name__)
            if mapped is not None:
                kind = mapped
                break

        routes = [
            [int(inp), int(out)]
            for inp, out in getattr(node_cls, "_routes", [])
        ]

        output_signal_types = {
            int(port_id): _signal_name(sig)
            for port_id, sig in getattr(node_cls, "_output_types", {}).items()
        }

        for port_id in getattr(node_cls, "_audio_outputs", frozenset()):
            output_signal_types.setdefault(int(port_id), "audio")
        for _, out in getattr(node_cls, "_routes", []):
            output_signal_types.setdefault(int(out), "audio")

        required_inputs = [
            {
                "id": int(port_id),
                "api_name": input_names_by_id.get(int(port_id)),
                "signal_type": _signal_name(sig),
            }
            for port_id, sig in getattr(node_cls, "_required_cv", {}).items()
        ]

        attenuators = [
            {
                "input_id": int(port_id),
                "input_api_name": input_names_by_id.get(int(port_id)),
                "param_id": int(param_id),
            }
            for port_id, param_id in getattr(node_cls, "_port_attenuators", {}).items()
        ]

        audio_inputs = sorted(int(port_id) for port_id in getattr(node_cls, "_audio_inputs", frozenset()))
        audio_outputs = sorted(int(port_id) for port_id in getattr(node_cls, "_audio_outputs", frozenset()))
        if audio_inputs:
            notes.append(f"Audio inputs: {audio_inputs}")
        if audio_outputs:
            notes.append(f"Audio outputs: {audio_outputs}")

    return {
        "status": "success",
        "plugin": plugin,
        "model": model,
        "kind": kind,
        "params": _simplify_params(discovered.get("params", [])),
        "inputs": _simplify_ports(discovered.get("inputs", [])),
        "outputs": _simplify_ports(discovered.get("outputs", []), output_signal_types),
        "routes": routes,
        "required_inputs": required_inputs,
        "attenuators": attenuators,
        "notes": notes,
    }


def describe_module_surface(plugin: str, model: str) -> dict:
    """Backward-compatible alias for inspect_module_surface()."""
    return inspect_module_surface(plugin, model)
