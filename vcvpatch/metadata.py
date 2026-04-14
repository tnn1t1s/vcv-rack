"""
Public metadata access for builder clients.

This layer exposes discovered-backed module metadata without requiring callers
to know the cache layout or import vcvpatch.core internals directly.
"""

from __future__ import annotations

from copy import deepcopy

from .core import (
    _find_param_id,
    _find_port_id,
    _load_discovered,
    _param_name_by_id,
    _port_name_by_id,
)


def module_metadata(plugin: str, model: str) -> dict:
    """Return discovered metadata for a module, or raise if it is unavailable."""
    data = _load_discovered(plugin, model)
    if data is None:
        raise ValueError(
            f"Module '{plugin}/{model}' not found in local discovered metadata."
        )
    return deepcopy(data)


def _entries(plugin: str, model: str, bucket: str) -> list[dict]:
    return module_metadata(plugin, model).get(bucket, [])


def param(plugin: str, model: str, api_name: str) -> dict:
    """Return a discovered param entry by exact canonical API name."""
    params = _entries(plugin, model, "params")
    param_id_value = _find_param_id(params, api_name)
    if param_id_value is None:
        names = [p["api_name"] for p in params if p.get("api_name")]
        raise ValueError(
            f"Unknown param '{api_name}' for {plugin}/{model}. Known API params: {names}"
        )
    return next(p for p in params if p["id"] == param_id_value)


def input_port(plugin: str, model: str, api_name: str) -> dict:
    """Return a discovered input entry by exact canonical API name."""
    inputs = _entries(plugin, model, "inputs")
    port_id_value = _find_port_id(inputs, api_name)
    if port_id_value is None:
        names = [p["api_name"] for p in inputs if p.get("api_name")]
        raise ValueError(
            f"Unknown input '{api_name}' for {plugin}/{model}. Known API inputs: {names}"
        )
    return next(p for p in inputs if p["id"] == port_id_value)


def output_port(plugin: str, model: str, api_name: str) -> dict:
    """Return a discovered output entry by exact canonical API name."""
    outputs = _entries(plugin, model, "outputs")
    port_id_value = _find_port_id(outputs, api_name)
    if port_id_value is None:
        names = [p["api_name"] for p in outputs if p.get("api_name")]
        raise ValueError(
            f"Unknown output '{api_name}' for {plugin}/{model}. Known API outputs: {names}"
        )
    return next(p for p in outputs if p["id"] == port_id_value)


def param_id(plugin: str, model: str, api_name: str) -> int:
    """Return a param id by exact canonical API name."""
    return int(param(plugin, model, api_name)["id"])


def param_range(plugin: str, model: str, api_name: str) -> tuple[float, float]:
    """Return (min, max) for a discovered param by exact canonical API name."""
    entry = param(plugin, model, api_name)
    return float(entry["min"]), float(entry["max"])


def param_name(plugin: str, model: str, param_id_value: int, *, api: bool = False) -> str | None:
    """Resolve a param id to its display name or canonical API name."""
    params = _entries(plugin, model, "params")
    if api:
        for entry in params:
            if entry["id"] == param_id_value:
                return entry.get("api_name")
        return None
    return _param_name_by_id(params, param_id_value)


def port_name(
    plugin: str,
    model: str,
    port_id_value: int,
    *,
    is_output: bool,
    api: bool = False,
) -> str | None:
    """Resolve a port id to its display name or canonical API name."""
    bucket = "outputs" if is_output else "inputs"
    ports = _entries(plugin, model, bucket)
    if api:
        for entry in ports:
            if entry["id"] == port_id_value:
                return entry.get("api_name")
        return None
    return _port_name_by_id(ports, port_id_value)
