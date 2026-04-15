from __future__ import annotations

from pathlib import Path
from typing import Iterable

import yaml

from .node import (
    AudioMixerNode,
    AudioProcessorNode,
    AudioSinkNode,
    AudioSourceNode,
    ControllerNode,
    PassThroughNode,
    SignalType,
)


_KIND_TO_BASE = {
    "audio_source": AudioSourceNode,
    "audio_processor": AudioProcessorNode,
    "audio_mixer": AudioMixerNode,
    "audio_sink": AudioSinkNode,
    "controller": ControllerNode,
    "passthrough": PassThroughNode,
}

_SIGNAL_TYPES = {
    "audio": SignalType.AUDIO,
    "cv": SignalType.CV,
    "gate": SignalType.GATE,
    "clock": SignalType.CLOCK,
}


def _sanitize_name(text: str) -> str:
    return "".join(ch for ch in text.title() if ch.isalnum())


def _tuple_pairs(pairs: Iterable[Iterable[int]]) -> list[tuple[int, int]]:
    return [tuple(int(v) for v in pair) for pair in pairs]


def _int_set(values: Iterable[int]) -> frozenset[int]:
    return frozenset(int(v) for v in values)


def _signal_map(raw: dict | None) -> dict[int, SignalType]:
    if not raw:
        return {}
    return {
        int(port_id): _SIGNAL_TYPES[str(sig).lower()]
        for port_id, sig in raw.items()
    }


def load_semantic_node_specs() -> dict[str, type]:
    """
    Load declarative graph-node specs from YAML files and return a registry of
    dynamically generated Node subclasses.
    """
    specs_dir = Path(__file__).with_name("specs")
    registry: dict[str, type] = {}
    for path in sorted(specs_dir.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text()) or {}
        plugin = raw["plugin"]
        model = raw["model"]
        kind = raw["kind"]
        base = _KIND_TO_BASE[kind]
        attrs = {
            "PLUGIN": plugin,
            "MODEL": model,
            "__module__": __name__,
            "__doc__": raw.get("description", f"Declarative semantic spec for {plugin}/{model}."),
        }

        if "routes" in raw:
            attrs["_routes"] = _tuple_pairs(raw["routes"])
        if "audio_inputs" in raw:
            attrs["_audio_inputs"] = _int_set(raw["audio_inputs"])
        if "audio_outputs" in raw:
            attrs["_audio_outputs"] = _int_set(raw["audio_outputs"])
        if "outputs" in raw:
            attrs["_output_types"] = _signal_map(raw["outputs"])
        if "required_inputs" in raw:
            attrs["_required_cv"] = _signal_map(raw["required_inputs"])
        if "attenuators" in raw:
            attrs["_port_attenuators"] = {
                int(port_id): int(param_id)
                for port_id, param_id in raw["attenuators"].items()
            }

        class_name = f"{_sanitize_name(plugin)}{_sanitize_name(model)}Node"
        registry[f"{plugin}/{model}"] = type(class_name, (base,), attrs)
    return registry
