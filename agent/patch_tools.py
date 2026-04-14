"""
Tool functions for the VCV Rack patch agent.

All functions accept an optional `tool_context` last parameter -- ADK injects
the ToolContext object there at call time. All return a dict with at least
{"status": "ok"} or {"status": "error", "message": str}.

Port notation accepted by connect_* tools:
  "vco1.SAW"      -- auto-detect direction (output preferred)
  "vco1.i.PWM"    -- force input
  "vco1.o.SAW"    -- force output
"""

from __future__ import annotations

import json
from typing import Any

from vcvpatch.builder import PatchBuilder, PatchCompileError
from vcvpatch.core import _load_discovered, _param_name_by_id
from vcvpatch.graph.modules import NODE_REGISTRY

from . import state as _state


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sid(tool_context) -> str:
    """Extract session id from any context flavour, or return a default."""
    if tool_context is None:
        return "__default__"
    if hasattr(tool_context, "session"):
        return tool_context.session.id   # real ADK ToolContext
    return tool_context.session_id       # FakeContext used in tests


def _session(tool_context) -> dict:
    """Return the state dict for this session, creating it if needed."""
    return _state.get(_sid(tool_context))


def _resolve_port(port_str: str, modules: dict):
    """
    Parse dot-notation port string and return a Port object.

    "vco1.SAW"     -> modules["vco1"]._module._lookup_port("SAW", prefer_output=True)
    "vco1.i.PWM"   -> prefer_output=False
    "vco1.o.SAW"   -> prefer_output=True
    """
    parts = port_str.split(".")
    if len(parts) == 2:
        mod_name, port_name = parts
        prefer_output = True
    elif len(parts) == 3:
        mod_name, direction, port_name = parts
        if direction == "i":
            prefer_output = False
        elif direction == "o":
            prefer_output = True
        else:
            raise ValueError(
                f"Unknown direction '{direction}' in port '{port_str}'. Use 'i' or 'o'."
            )
    else:
        raise ValueError(
            f"Cannot parse port '{port_str}'. "
            "Expected 'module.PORT', 'module.i.PORT', or 'module.o.PORT'."
        )

    if mod_name not in modules:
        known = ", ".join(sorted(modules)) or "(none)"
        raise KeyError(f"Module '{mod_name}' not found. Known modules: {known}")

    handle = modules[mod_name]
    return handle._module._lookup_port(port_name, prefer_output=prefer_output)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def new_patch(tool_context=None) -> dict:
    """Reset the session and start a fresh PatchBuilder."""
    _state.reset(_sid(tool_context))
    return {"status": "ok", "message": "New patch started."}


def reset_patch(tool_context=None) -> dict:
    """Alias for new_patch -- reset the session and start fresh."""
    return new_patch(tool_context)


def add_module(name: str, plugin: str, model: str,
               params_json: str = "{}", tool_context=None) -> dict:
    """
    Add a module to the patch and register it under a friendly name.

    Args:
        name:        Friendly name used in subsequent port references (e.g. "vco1").
        plugin:      Plugin slug (e.g. "Fundamental", "Valley").
        model:       Model slug (e.g. "VCO", "Plateau").
        params_json: JSON object of param overrides: '{"FREQ": 0.4, "PW": 0.5}'.
    """
    try:
        params = json.loads(params_json)
    except json.JSONDecodeError as exc:
        return {"status": "error", "message": f"Invalid params_json: {exc}"}

    sess = _session(tool_context)
    pb: PatchBuilder = sess["pb"]
    modules: dict = sess["modules"]

    try:
        handle = pb.module(plugin, model, **params)
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    modules[name] = handle
    key = f"{plugin}/{model}"
    introspectable = key in NODE_REGISTRY
    return {
        "status": "ok",
        "name": name,
        "plugin": plugin,
        "model": model,
        "introspectable": introspectable,
        "params_set": params,
    }


def connect_audio(from_port: str, to_port: str,
                  tool_context=None) -> dict:
    """
    Connect one audio output to one audio input.

    Cable color is auto-detected from the source port's signal type.

    Args:
        from_port: Output port in dot-notation, e.g. "vco1.SAW".
        to_port:   Input port in dot-notation, e.g. "vcf1.i.IN".
    """
    sess = _session(tool_context)
    pb: PatchBuilder = sess["pb"]
    modules: dict = sess["modules"]

    try:
        src = _resolve_port(from_port, modules)
        dst = _resolve_port(to_port, modules)
        pb._add_cable(src, dst)
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    return {"status": "ok", "from": from_port, "to": to_port}


def fan_out_audio(from_port: str, to_ports: list[str],
                  tool_context=None) -> dict:
    """
    Connect one audio output to multiple inputs (fan-out).

    Cable color is auto-detected from the source port's signal type.

    Args:
        from_port: Source output port, e.g. "reverb.o.OUT_L".
        to_ports:  List of destination input ports, e.g. ["audio.i.IN_L", "audio.i.IN_R"].
    """
    sess = _session(tool_context)
    pb: PatchBuilder = sess["pb"]
    modules: dict = sess["modules"]

    try:
        src = _resolve_port(from_port, modules)
        destinations = [_resolve_port(p, modules) for p in to_ports]
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    for dst in destinations:
        pb._add_cable(src, dst)

    return {"status": "ok", "from": from_port, "to": to_ports}


def modulate(src_port: str, dst_port: str,
             attenuation: float = 0.5,
             tool_context=None) -> dict:
    """
    Connect a CV modulation cable and auto-open the destination attenuator.

    Cable color is always CV (blue).

    Args:
        src_port:    Source output port, e.g. "lfo1.SIN".
        dst_port:    Destination input port, e.g. "vcf1.i.FREQ".
        attenuation: Attenuator value 0..1 (default 0.5). Written to the
                     destination module's attenuator param if one exists.
    """
    sess = _session(tool_context)
    modules: dict = sess["modules"]

    # Parse module name from src_port to get the ModuleHandle.
    src_parts = src_port.split(".")
    if len(src_parts) < 2:
        return {"status": "error", "message": f"Cannot parse src_port '{src_port}'"}
    src_mod_name = src_parts[0]
    via = src_parts[-1]  # port name, ignoring direction marker if any

    if src_mod_name not in modules:
        return {"status": "error",
                "message": f"Module '{src_mod_name}' not found."}

    src_handle = modules[src_mod_name]
    try:
        dst = _resolve_port(dst_port, modules)
        src_handle.modulates(
            dst,
            via=via,
            attenuation=attenuation,
            open_attenuator=True,
        )
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    return {
        "status": "ok",
        "from": src_port,
        "to": dst_port,
        "attenuation": attenuation,
    }


def connect_cv(src_port: str, dst_port: str,
               tool_context=None) -> dict:
    """
    Connect a clock, gate, or plain CV cable (no attenuator handling).

    Cable type is auto-detected from the source port's signal type.

    Args:
        src_port: Source output port, e.g. "clock1.o.CLK0".
        dst_port: Destination input port, e.g. "seq1.i.CLOCK".
    """
    sess = _session(tool_context)
    pb: PatchBuilder = sess["pb"]
    modules: dict = sess["modules"]

    try:
        src = _resolve_port(src_port, modules)
        dst = _resolve_port(dst_port, modules)
        pb.connect(src, dst)
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    return {"status": "ok", "from": src_port, "to": dst_port}


def get_status(tool_context=None) -> dict:
    """Return the current patch status, routing description, and proof report."""
    sess = _session(tool_context)
    pb: PatchBuilder = sess["pb"]
    modules: dict = sess["modules"]

    return {
        "status": "ok",
        "proven": pb.proven,
        "summary": pb.status,
        "routing": pb.describe(),
        "report": pb.report(),
        "named_modules": list(modules.keys()),
    }


def compile_and_save(output_path: str, tool_context=None) -> dict:
    """
    Build the patch (raises if not proven) and save it to a .vcv file.

    Args:
        output_path: Destination path, e.g. "tests/cm_drone.vcv".
    """
    sess = _session(tool_context)
    pb: PatchBuilder = sess["pb"]

    try:
        pb.save(output_path)
    except PatchCompileError as exc:
        return {"status": "error", "message": str(exc)}
    except Exception as exc:
        return {"status": "error", "message": f"Save failed: {exc}"}

    return {"status": "ok", "path": output_path, "proven": True}


def list_modules(tool_context=None) -> dict:
    """
    List all modules known to the system, grouped by plugin.

    Returns modules from the discovered/ directory and the NODE_REGISTRY.
    """
    import os
    import glob as _glob
    from vcvpatch.core import DISCOVERED_DIR

    by_plugin: dict[str, list[str]] = {}
    total = 0
    for plugin_dir in sorted(os.listdir(DISCOVERED_DIR)):
        plugin_path = os.path.join(DISCOVERED_DIR, plugin_dir)
        if not os.path.isdir(plugin_path):
            continue
        for model_dir in sorted(os.listdir(plugin_path)):
            model_path = os.path.join(plugin_path, model_dir)
            if not os.path.isdir(model_path):
                continue
            # Only include if a non-failed JSON exists
            success = [
                f for f in os.listdir(model_path)
                if f.endswith(".json") and not f.startswith("failed")
            ]
            if success:
                by_plugin.setdefault(plugin_dir, []).append(model_dir)
                total += 1

    introspectable = sorted(NODE_REGISTRY.keys())

    return {
        "status": "ok",
        "by_plugin": by_plugin,
        "introspectable": introspectable,
        "total": total,
    }


def describe_module(plugin: str, model: str, tool_context=None) -> dict:
    """
    Return the param, input, and output port names for a specific module.

    Args:
        plugin: Plugin slug, e.g. "Fundamental".
        model:  Model slug, e.g. "VCO".
    """
    key = f"{plugin}/{model}"
    discovered = _load_discovered(plugin, model)
    if discovered is None:
        return {
            "status": "error",
            "message": (
                f"Module '{key}' not found in local discovered cache. "
                f"Generate it with `python -m vcvpatch.introspect {plugin} {model}`."
            ),
        }

    node_cls = NODE_REGISTRY.get(key)
    notes = []
    if node_cls is None:
        notes.append("Not in NODE_REGISTRY -- UnknownNode; proof will be blocked.")
    if hasattr(node_cls, "_port_attenuators") and node_cls._port_attenuators:
        atn = node_cls._port_attenuators
        notes.append(
            f"Has attenuator params: {atn} -- use modulate() to auto-open them."
        )
    if hasattr(node_cls, "_required_cv") and node_cls._required_cv:
        notes.append(f"Required CV inputs: {node_cls._required_cv}")

    return {
        "status": "ok",
        "plugin": plugin,
        "model": model,
        "params": discovered.get("params", []),
        "inputs": discovered.get("inputs", []),
        "outputs": discovered.get("outputs", []),
        "notes": notes,
    }


# ---------------------------------------------------------------------------
# Runtime tools (live param control via MIDI + autosave readback)
# ---------------------------------------------------------------------------

def connect_to_rack(
    midi_specs_json: str = "[]",
    tool_context=None,
) -> dict:
    """
    Open a virtual MIDI port to connect to a running VCV Rack instance.

    The user must already have the patch open in Rack (GUI mode). The patch
    must contain a Core/MidiMap module pre-configured for the 'vcvpatch_control'
    port (done at build time via MidiMapBuilder).

    Args:
        midi_specs_json:
            JSON array of CC->param mappings already in the patch.
            Each item: {"module_id": 123, "param_id": 0, "cc": 1, "min": -2.0, "max": 2.0}
            Omit (or pass "[]") if only using read_live_state.
    """
    sess = _session(tool_context)

    existing = sess.get("rack_connection")
    if existing is not None:
        existing.disconnect()
        sess["rack_connection"] = None

    try:
        raw_specs = json.loads(midi_specs_json)
    except json.JSONDecodeError as exc:
        return {"status": "error", "message": f"Invalid midi_specs_json: {exc}"}

    from vcvpatch.runtime import MidiMapSpec, RackConnection

    try:
        midi_specs = [
            MidiMapSpec(
                cc=int(s["cc"]),
                module_id=int(s["module_id"]),
                param_id=int(s["param_id"]),
                min_val=float(s.get("min", 0.0)),
                max_val=float(s.get("max", 1.0)),
            )
            for s in raw_specs
        ]
    except (KeyError, TypeError, ValueError) as exc:
        return {"status": "error", "message": f"Invalid spec entry: {exc}"}

    try:
        conn = RackConnection(midi_specs)
        conn.connect()
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    sess["rack_connection"] = conn
    return {
        "status": "ok",
        "midi_mappings": len(midi_specs),
        "message": (
            "Virtual MIDI port 'vcvpatch_control' opened. "
            "Ensure the patch is open in Rack and Core/MidiMap is configured for this port."
        ),
    }


def set_param_live(
    module_id: int,
    param_id: int,
    value: float,
    tool_context=None,
) -> dict:
    """
    Send a MIDI CC to set a param in the running Rack instance.

    Requires connect_to_rack to have been called with a MidiMapSpec for this
    (module_id, param_id).

    Args:
        module_id:  Integer module ID (from Module.id or the patch JSON).
        param_id:   Integer param ID.
        value:      New value in the param's natural range (uses the spec's min/max for scaling).
    """
    sess = _session(tool_context)
    conn = sess.get("rack_connection")

    if conn is None:
        return {"status": "error", "message": "Not connected. Call connect_to_rack first."}

    try:
        conn.set_param(module_id, param_id, value)
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    return {"status": "ok", "module_id": module_id, "param_id": param_id, "value": value}


def read_live_state(tool_context=None) -> dict:
    """
    Read the current patch state from the VCV Rack autosave.

    Returns param values for all modules, with IDs resolved to names where
    the registry has them. Does not require connect_to_rack -- can be called
    anytime Rack has a patch open.
    """
    from vcvpatch.runtime import AUTOSAVE_JSON

    try:
        with open(AUTOSAVE_JSON, "r", encoding="utf-8") as f:
            state = json.load(f)
    except FileNotFoundError:
        return {
            "status": "error",
            "message": f"Autosave not found at {AUTOSAVE_JSON}. Open a patch in Rack first.",
        }
    except json.JSONDecodeError as exc:
        return {"status": "error", "message": f"Autosave JSON malformed: {exc}"}

    result_modules = []
    for mod in state.get("modules", []):
        plugin = mod.get("plugin", "")
        model = mod.get("model", "")
        discovered = _load_discovered(plugin, model)
        param_list = discovered.get("params", []) if discovered else []
        params_out = {}
        for p in mod.get("params", []):
            pid = p.get("id")
            pval = p.get("value")
            label = _param_name_by_id(param_list, pid) or str(pid)
            params_out[label] = pval
        result_modules.append({
            "id": mod.get("id"),
            "plugin": plugin,
            "model": model,
            "params": params_out,
        })

    return {
        "status": "ok",
        "rack_version": state.get("version"),
        "modules": result_modules,
    }


def disconnect_from_rack(tool_context=None) -> dict:
    """
    Close the virtual MIDI port connection to Rack.

    Safe to call even if not currently connected.
    """
    sess = _session(tool_context)
    conn = sess.get("rack_connection")

    if conn is None:
        return {"status": "ok", "message": "Not connected."}

    try:
        conn.disconnect()
    except Exception as exc:
        return {"status": "error", "message": str(exc)}

    sess["rack_connection"] = None
    return {"status": "ok", "message": "Disconnected from Rack."}
