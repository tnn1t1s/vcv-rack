from __future__ import annotations

from dataclasses import asdict, dataclass

from .graph.modules import NODE_REGISTRY
from .graph.node import (
    AudioMixerNode,
    AudioProcessorNode,
    AudioSinkNode,
    AudioSourceNode,
    ControllerNode,
    PassThroughNode,
    SignalType,
)
from .metadata import module_metadata


@dataclass(frozen=True)
class SurfaceEntry:
    id: int
    api_name: str
    name: str
    default: float | None = None
    min: float | None = None
    max: float | None = None
    signal_type: str | None = None


@dataclass(frozen=True)
class RequiredInput:
    id: int
    api_name: str | None
    signal_type: str


@dataclass(frozen=True)
class AttenuatorBinding:
    input_id: int
    input_api_name: str | None
    param_id: int


@dataclass(frozen=True)
class ModuleSemantics:
    kind: str
    routes: tuple[tuple[int, int], ...]
    required_inputs: tuple[RequiredInput, ...]
    attenuators: tuple[AttenuatorBinding, ...]


@dataclass(frozen=True)
class SupportedModule:
    plugin: str
    model: str
    params: tuple[SurfaceEntry, ...]
    inputs: tuple[SurfaceEntry, ...]
    outputs: tuple[SurfaceEntry, ...]
    semantics: ModuleSemantics

    def to_dict(self) -> dict:
        return asdict(self)


_KIND_NAMES = {
    AudioSourceNode: "audio_source",
    AudioProcessorNode: "audio_processor",
    AudioMixerNode: "audio_mixer",
    AudioSinkNode: "audio_sink",
    ControllerNode: "controller",
    PassThroughNode: "passthrough",
}


def _signal_name(value: SignalType) -> str:
    return value.name.lower()


def _kind_for(node_cls: type) -> str:
    for base, name in _KIND_NAMES.items():
        if issubclass(node_cls, base):
            return name
    raise ValueError(f"Unrecognized node class for supported palette: {node_cls}")


def _surface_entries(entries: list[dict], signal_types: dict[int, str] | None = None) -> tuple[SurfaceEntry, ...]:
    signal_types = signal_types or {}
    result = []
    for entry in entries:
        api_name = entry.get("api_name")
        if not api_name:
            continue
        result.append(
            SurfaceEntry(
                id=int(entry["id"]),
                api_name=api_name,
                name=entry.get("name") or api_name,
                default=entry.get("default"),
                min=entry.get("min"),
                max=entry.get("max"),
                signal_type=signal_types.get(int(entry["id"])),
            )
        )
    return tuple(result)


def _supported_from_node(key: str, node_cls: type) -> SupportedModule | None:
    plugin, model = key.split("/", 1)
    try:
        discovered = module_metadata(plugin, model)
    except ValueError:
        return None

    output_signal_types = {
        int(port_id): _signal_name(sig)
        for port_id, sig in getattr(node_cls, "_output_types", {}).items()
    }
    for port_id in getattr(node_cls, "_audio_outputs", frozenset()):
        output_signal_types.setdefault(int(port_id), "audio")
    for _, out in getattr(node_cls, "_routes", []):
        output_signal_types.setdefault(int(out), "audio")

    input_names_by_id = {
        int(entry["id"]): entry.get("api_name")
        for entry in discovered.get("inputs", [])
        if entry.get("api_name")
    }

    semantics = ModuleSemantics(
        kind=_kind_for(node_cls),
        routes=tuple(
            (int(inp), int(out))
            for inp, out in getattr(node_cls, "_routes", [])
        ),
        required_inputs=tuple(
            RequiredInput(
                id=int(port_id),
                api_name=input_names_by_id.get(int(port_id)),
                signal_type=_signal_name(sig),
            )
            for port_id, sig in getattr(node_cls, "_required_cv", {}).items()
        ),
        attenuators=tuple(
            AttenuatorBinding(
                input_id=int(port_id),
                input_api_name=input_names_by_id.get(int(port_id)),
                param_id=int(param_id),
            )
            for port_id, param_id in getattr(node_cls, "_port_attenuators", {}).items()
        ),
    )

    return SupportedModule(
        plugin=plugin,
        model=model,
        params=_surface_entries(discovered.get("params", [])),
        inputs=_surface_entries(discovered.get("inputs", [])),
        outputs=_surface_entries(discovered.get("outputs", []), output_signal_types),
        semantics=semantics,
    )


def supported_modules() -> tuple[SupportedModule, ...]:
    modules = []
    for key, node_cls in sorted(NODE_REGISTRY.items()):
        module = _supported_from_node(key, node_cls)
        if module is not None:
            modules.append(module)
    return tuple(modules)


def supported_module(plugin: str, model: str) -> SupportedModule:
    key = f"{plugin}/{model}"
    node_cls = NODE_REGISTRY.get(key)
    if node_cls is None:
        raise ValueError(f"Module '{key}' is not in the semantic graph registry.")
    module = _supported_from_node(key, node_cls)
    if module is None:
        raise ValueError(
            f"Module '{key}' is in the semantic graph registry but has no local exact surface metadata."
        )
    return module
