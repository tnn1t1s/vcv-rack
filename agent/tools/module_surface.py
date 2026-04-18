"""Inspect the exact semantic API surface of a VCV Rack module."""

from __future__ import annotations

from vcvpatch.metadata import module_metadata
from vcvpatch.palette import supported_module


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

    notes: list[str] = []
    try:
        module = supported_module(plugin, model)
    except ValueError:
        return {
            "status": "success",
            "plugin": plugin,
            "model": model,
            "kind": None,
            "params": [
                {
                    "id": int(entry["id"]),
                    "api_name": entry["api_name"],
                    "name": entry.get("name") or entry["api_name"],
                    "default": entry.get("default"),
                    "min": entry.get("min"),
                    "max": entry.get("max"),
                }
                for entry in discovered.get("params", [])
                if entry.get("api_name")
            ],
            "inputs": [
                {
                    "id": int(entry["id"]),
                    "api_name": entry["api_name"],
                    "name": entry.get("name") or entry["api_name"],
                }
                for entry in discovered.get("inputs", [])
                if entry.get("api_name")
            ],
            "outputs": [
                {
                    "id": int(entry["id"]),
                    "api_name": entry["api_name"],
                    "name": entry.get("name") or entry["api_name"],
                }
                for entry in discovered.get("outputs", [])
                if entry.get("api_name")
            ],
            "routes": [],
            "required_inputs": [],
            "attenuators": [],
            "notes": [
                "Not in supported module palette; exact names available, but graph proof falls back to UnknownNode."
            ],
        }

    return {
        "status": "success",
        "plugin": plugin,
        "model": model,
        "kind": module.semantics.kind,
        "params": [entry for entry in module.to_dict()["params"]],
        "inputs": [entry for entry in module.to_dict()["inputs"]],
        "outputs": [entry for entry in module.to_dict()["outputs"]],
        "routes": [list(route) for route in module.semantics.routes],
        "required_inputs": [entry for entry in module.to_dict()["semantics"]["required_inputs"]],
        "attenuators": [entry for entry in module.to_dict()["semantics"]["attenuators"]],
        "notes": notes,
    }


def describe_module_surface(plugin: str, model: str) -> dict:
    """Backward-compatible alias for inspect_module_surface()."""
    return inspect_module_surface(plugin, model)
