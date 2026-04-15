"""
Core classes: Patch, Module, Port, Cable.
"""

import os
import json
import glob
import random
import re
from enum import Enum
from typing import Optional, Union


# ---------------------------------------------------------------------------
# Cable type enum + color palette
# ---------------------------------------------------------------------------

class CableType(Enum):
    AUDIO = "audio"
    CV    = "cv"
    GATE  = "gate"
    CLOCK = "clock"

CABLE_COLORS = {
    CableType.AUDIO: "#ffb437",   # yellow
    CableType.CV:    "#2196f3",   # blue
    CableType.GATE:  "#f44336",   # red
    CableType.CLOCK: "#4caf50",   # green
}


# ---------------------------------------------------------------------------
# Discovered metadata loader (sole source of truth for port/param IDs)
# ---------------------------------------------------------------------------

DISCOVERED_DIR = os.path.join(os.path.dirname(__file__), "discovered")

# Minimal legacy supplement for preserved param-only fixture files.
# This is intentionally tiny: just enough to keep the committed test subset
# usable while the broader discovered cache remains local/generated.
_LEGACY_PORTS: dict[tuple[str, str], dict[str, list[dict]]] = {
    ("Fundamental", "VCO"): {
        "inputs": [
            {"id": 0, "name": "1V/octave pitch"},
            {"id": 1, "name": "Frequency modulation"},
            {"id": 2, "name": "Sync"},
            {"id": 3, "name": "Pulse width modulation"},
        ],
        "outputs": [
            {"id": 0, "name": "Sine"},
            {"id": 1, "name": "Triangle"},
            {"id": 2, "name": "Sawtooth"},
            {"id": 3, "name": "Square"},
        ],
    },
    ("Fundamental", "VCF"): {
        "inputs": [
            {"id": 0, "name": "Frequency"},
            {"id": 1, "name": "Resonance"},
            {"id": 2, "name": "Drive"},
            {"id": 3, "name": "Audio"},
        ],
        "outputs": [
            {"id": 0, "name": "LPF"},
            {"id": 1, "name": "HPF"},
        ],
    },
    ("Fundamental", "VCA"): {
        "inputs": [
            {"id": 1, "name": "CV"},
            {"id": 2, "name": "IN"},
            {"id": 4, "name": "CV 2"},
            {"id": 5, "name": "IN 2"},
        ],
        "outputs": [
            {"id": 0, "name": "OUT"},
            {"id": 1, "name": "OUT 2"},
        ],
    },
    ("Fundamental", "ADSR"): {
        "inputs": [
            {"id": 0, "name": "Attack"},
            {"id": 1, "name": "Decay"},
            {"id": 2, "name": "Sustain"},
            {"id": 3, "name": "Release"},
            {"id": 4, "name": "Gate"},
            {"id": 5, "name": "Retrig"},
        ],
        "outputs": [
            {"id": 0, "name": "ENV"},
        ],
    },
    ("Fundamental", "LFO"): {
        "inputs": [
            {"id": 0, "name": "Frequency modulation"},
            {"id": 2, "name": "Reset"},
            {"id": 3, "name": "Pulse width"},
            {"id": 4, "name": "Clock"},
        ],
        "outputs": [
            {"id": 0, "name": "Sine"},
            {"id": 1, "name": "Triangle"},
            {"id": 2, "name": "Sawtooth"},
            {"id": 3, "name": "Square"},
        ],
    },
    ("Fundamental", "SEQ3"): {
        "inputs": [
            {"id": 0, "name": "Tempo"},
            {"id": 1, "name": "Clock"},
            {"id": 2, "name": "Reset"},
            {"id": 3, "name": "Steps"},
            {"id": 4, "name": "Run"},
        ],
        "outputs": [
            {"id": 0, "name": "Trigger"},
            {"id": 1, "name": "CV 1"},
            {"id": 2, "name": "CV 2"},
            {"id": 3, "name": "CV 3"},
            {"id": 12, "name": "Steps"},
            {"id": 13, "name": "Clock"},
            {"id": 14, "name": "Run"},
            {"id": 15, "name": "Reset"},
        ],
    },
    ("ImpromptuModular", "Clocked-Clkd"): {
        "inputs": [
            {"id": 0, "name": "Reset"},
            {"id": 1, "name": "Run"},
            {"id": 2, "name": "BPM input"},
        ],
        "outputs": [
            {"id": 0, "name": "Clock 0"},
            {"id": 1, "name": "Clock 1"},
            {"id": 2, "name": "Clock 2"},
            {"id": 3, "name": "Clock 3"},
            {"id": 4, "name": "Reset"},
            {"id": 5, "name": "Run"},
            {"id": 6, "name": "BPM"},
        ],
    },
    ("Valley", "Plateau"): {
        "inputs": [
            {"id": 0, "name": "Left"},
            {"id": 1, "name": "Right"},
        ],
        "outputs": [
            {"id": 0, "name": "Left"},
            {"id": 1, "name": "Right"},
        ],
    },
    ("AudibleInstruments", "Rings"): {
        "inputs": [
            {"id": 0, "name": "Pitch (1V/oct)"},
            {"id": 7, "name": "Strum"},
        ],
        "outputs": [
            {"id": 0, "name": "Odd"},
            {"id": 1, "name": "Even"},
        ],
    },
    ("AudibleInstruments", "Clouds"): {
        "inputs": [
            {"id": 6, "name": "Left"},
            {"id": 7, "name": "Right"},
        ],
        "outputs": [
            {"id": 0, "name": "Left"},
            {"id": 1, "name": "Right"},
        ],
    },
    ("AudibleInstruments", "Marbles"): {
        "inputs": [],
        "outputs": [
            {"id": 0, "name": "T1"},
            {"id": 1, "name": "T2"},
            {"id": 2, "name": "T3"},
            {"id": 3, "name": "Y"},
            {"id": 4, "name": "X1"},
            {"id": 5, "name": "X2"},
            {"id": 6, "name": "X3"},
        ],
    },
}


def _load_discovered(plugin: str, model: str) -> dict | None:
    """
    Load the newest discovered JSON for plugin/model.

    Returns a normalised dict with keys:
        params:  list of {id, name, default, min, max}
        inputs:  list of {id, name}
        outputs: list of {id, name}
    Returns None if no discovered file exists.
    """
    pattern = os.path.join(DISCOVERED_DIR, plugin, model, "*.json")
    files = [
        f for f in glob.glob(pattern)
        if not os.path.basename(f).startswith("failed")
    ]
    if not files:
        return None
    # Sort by filename (semver sorts lexicographically for most common versions)
    latest = sorted(files)[-1]
    with open(latest) as fh:
        data = json.load(fh)

    legacy = _LEGACY_PORTS.get((plugin, model))
    if legacy is not None:
        if not data.get("inputs"):
            data["inputs"] = legacy["inputs"]
        if not data.get("outputs"):
            data["outputs"] = legacy["outputs"]
    _add_api_names(data)
    return data


def _api_name(name: str) -> str:
    """
    Convert a discovered display name into the canonical Python-facing API name.

    This mapping is deterministic and exact. Core lookup resolves only against
    these API names; it does not perform fuzzy matching or historical aliasing.
    """
    text = re.sub(r"[^0-9A-Za-z]+", "_", name.strip()).strip("_")
    if not text:
        return ""
    if text[0].isdigit():
        return f"_{text}"
    return text


def _add_api_names(data: dict) -> None:
    """Annotate discovered params/ports with deterministic API names."""
    for bucket in ("params", "inputs", "outputs"):
        for entry in data.get(bucket, []):
            entry["api_name"] = _api_name(entry.get("name", ""))


def _find_port_id(port_list: list, name: str) -> int | None:
    """
    Search a list of {id, name, api_name} dicts for an exact API-name match.
    Returns the integer id or None if not found.
    """
    for entry in port_list:
        if entry.get("api_name") == name:
            return entry["id"]
    return None


def _find_param_id(param_list: list, name: str) -> int | None:
    """
    Search a list of {id, name, api_name, ...} dicts for an exact API-name match.
    """
    for entry in param_list:
        if entry.get("api_name") == name:
            return entry["id"]
    return None


def _port_name_by_id(port_list: list, port_id: int) -> str | None:
    """Reverse lookup: port id -> name string, or None."""
    for entry in port_list:
        if entry["id"] == port_id:
            return entry["name"].strip()
    return None


def _param_name_by_id(param_list: list, param_id: int) -> str | None:
    """Reverse lookup: param id -> name string, or None."""
    for entry in param_list:
        if entry["id"] == param_id:
            name = entry["name"].strip()
            return name if name else None
    return None


# ---------------------------------------------------------------------------
# Port
# ---------------------------------------------------------------------------

class Port:
    """A reference to a specific input or output on a module."""

    def __init__(self, module: "Module", port_id: int, is_output: bool):
        self.module = module
        self.port_id = port_id
        self.is_output = is_output

    def __rshift__(self, other: "Port") -> "Port":
        """Connect with >>:  osc.SAW >> vcf.IN"""
        if not isinstance(other, Port):
            raise TypeError(f"Cannot connect Port to {type(other)}")
        self.module._patch._cable(self, other)
        return other

    def __repr__(self):
        direction = "out" if self.is_output else "in"
        return f"Port({self.module.model}[{direction} {self.port_id}])"


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------

class Module:
    """
    A module instance placed in the patch.

    Port access via attribute:
        mod.GATE     -> looks up in outputs first, then inputs
        mod.i.GATE   -> force input lookup
        mod.o.GATE   -> force output lookup

    Param values are passed at construction and stored as {id: value}.
    """

    def __init__(self, patch: "Patch", plugin: str, model: str,
                 pos: list, param_values: dict, extra_data: dict = None):
        self._patch = patch
        self.plugin = plugin
        self.model = model
        self.pos = pos
        self._param_values = param_values  # {param_id: value}
        self._extra_data = extra_data or {}
        self.id = random.randint(10**14, 10**16)

        self._discovered = _load_discovered(plugin, model)

    # -- Port access by name -------------------------------------------------

    def _lookup_port(self, name: str, prefer_output=None) -> Port:
        """Resolve an exact canonical API port name to a Port."""
        d = self._discovered
        if d is None:
            raise ValueError(
                f"Module {self.plugin}/{self.model} not found in discovered/. "
                f"Use .i(id) or .o(id) for raw port access, or generate local cache "
                f"with `python -m vcvpatch.introspect {self.plugin} {self.model}`."
            )

        outputs = d.get("outputs", [])
        inputs  = d.get("inputs",  [])

        if prefer_output is True:
            pid = _find_port_id(outputs, name)
            if pid is not None:
                return Port(self, pid, is_output=True)
            avail = [e["api_name"] for e in outputs if e.get("api_name")]
            raise AttributeError(
                f"No output '{name}' on {self.model}. Available API outputs: {avail}"
            )

        if prefer_output is False:
            pid = _find_port_id(inputs, name)
            if pid is not None:
                return Port(self, pid, is_output=False)
            avail = [e["api_name"] for e in inputs if e.get("api_name")]
            raise AttributeError(
                f"No input '{name}' on {self.model}. Available API inputs: {avail}"
            )

        # Auto: try outputs first, then inputs
        pid = _find_port_id(outputs, name)
        if pid is not None:
            return Port(self, pid, is_output=True)
        pid = _find_port_id(inputs, name)
        if pid is not None:
            return Port(self, pid, is_output=False)

        avail_out = [e["api_name"] for e in outputs if e.get("api_name")]
        avail_in  = [e["api_name"] for e in inputs if e.get("api_name")]
        raise AttributeError(
            f"No port '{name}' on {self.model}.\n"
            f"  API outputs: {avail_out}\n"
            f"  API inputs:  {avail_in}"
        )

    def __getattr__(self, name: str) -> Port:
        if name.startswith("_") or name in ("plugin", "model", "pos", "id"):
            raise AttributeError(name)
        return self._lookup_port(name)

    # -- Convenience accessors -----------------------------------------------

    @property
    def i(self) -> "_InputAccessor":
        """Force input: mod.i.GATE"""
        return _InputAccessor(self)

    @property
    def o(self) -> "_OutputAccessor":
        """Force output: mod.o.OUT"""
        return _OutputAccessor(self)

    def input(self, id_or_name) -> Port:
        if isinstance(id_or_name, str):
            return self._lookup_port(id_or_name, prefer_output=False)
        return Port(self, id_or_name, is_output=False)

    def output(self, id_or_name) -> Port:
        if isinstance(id_or_name, str):
            return self._lookup_port(id_or_name, prefer_output=True)
        return Port(self, id_or_name, is_output=True)

    def __repr__(self):
        return f"Module({self.plugin}/{self.model} id={self.id})"


class _InputAccessor:
    def __init__(self, module):
        self._m = module

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self._m._lookup_port(name, prefer_output=False)

    def __call__(self, id_or_name):
        return self._m.input(id_or_name)


class _OutputAccessor:
    def __init__(self, module):
        self._m = module

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return self._m._lookup_port(name, prefer_output=True)

    def __call__(self, id_or_name):
        return self._m.output(id_or_name)


# ---------------------------------------------------------------------------
# Cable
# ---------------------------------------------------------------------------

class Cable:
    def __init__(self, output: Port, input: Port,
                 cable_type: CableType = CableType.AUDIO):
        assert output.is_output, "First argument must be an output port"
        assert not input.is_output, "Second argument must be an input port"
        self.output = output
        self.input = input
        self.cable_type = cable_type

    @property
    def color(self) -> str:
        return CABLE_COLORS[self.cable_type]


# ---------------------------------------------------------------------------
# Patch
# ---------------------------------------------------------------------------

class Patch:
    """
    The main object. Add modules, connect ports, save to .vcv.

    Usage:
        patch = Patch()
        osc = patch.add("Fundamental", "VCO1")
        vcf = patch.add("Fundamental", "VCF", FREQ=0.5, RES=0.2)
        osc.SAW >> vcf.IN
        # or: patch.connect(osc.SAW, vcf.IN)
        patch.save("my_patch.vcv")
    """

    RACK_VERSION = "2.6.6"
    HP = 15  # pixels per HP (approx, for layout)

    def __init__(self, zoom: float = 1.0):
        self.modules: list[Module] = []
        self.cables: list[Cable] = []
        self.zoom = zoom
        self._col = 0     # auto-layout cursor (in HP units)
        self._row = 0

    # -- Module placement ----------------------------------------------------

    def add(self, plugin: str, model: str,
            pos: Optional[list] = None,
            color: Optional[str] = None,
            extra_data: Optional[dict] = None,
            **params) -> Module:
        """
        Add a module to the patch.

        params are keyword args matching the module's canonical API param names.
        E.g.: patch.add("Fundamental", "VCF", Cutoff_frequency=0.5, Resonance=0.3)

        pos=[col, row] in HP units. If omitted, auto-layout left-to-right.
        """
        if pos is None:
            pos = [self._col, self._row]
            self._col += 8  # advance by ~8HP per module (rough)

        # Resolve canonical API param names -> param IDs using discovered metadata
        discovered = _load_discovered(plugin, model)
        param_values = {}
        for name, value in params.items():
            pid = None
            if discovered:
                pid = _find_param_id(discovered.get("params", []), name)
            if pid is None:
                # Try raw integer
                try:
                    pid = int(name)
                except (ValueError, TypeError):
                    avail = (
                        [p["api_name"] for p in discovered["params"] if p.get("api_name")]
                        if discovered else "module not in discovered/"
                    )
                    raise ValueError(
                        f"Unknown param '{name}' for {plugin}/{model}. "
                        f"Known API params: {avail}"
                    )
            param_values[pid] = float(value)

        m = Module(self, plugin, model, pos, param_values, extra_data=extra_data)
        self.modules.append(m)
        return m

    # -- Cable connections ---------------------------------------------------

    def _cable(self, output: Port, input: Port,
               cable_type: CableType = CableType.AUDIO) -> Cable:
        c = Cable(output, input, cable_type)
        self.cables.append(c)
        return c

    def connect(self, output: Port, input: Port,
                cable_type: CableType = CableType.AUDIO) -> Cable:
        """Explicitly connect two ports. Also works via >> operator."""
        return self._cable(output, input, cable_type)

    def connect_all(self, source: Port, *destinations: Port,
                    cable_type: CableType = CableType.AUDIO):
        """Fan out one output to multiple inputs."""
        for dst in destinations:
            self._cable(source, dst, cable_type)

    # -- Layout helpers ------------------------------------------------------

    def row(self, row: int = None):
        """Move auto-layout cursor to a new row."""
        if row is not None:
            self._row = row
        else:
            self._row += 1
        self._col = 0
        return self

    def gap(self, hp: int = 4):
        """Add horizontal gap in auto-layout."""
        self._col += hp
        return self

    # -- Serialization -------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialize to the patch.json dict structure."""
        return {
            "version": self.RACK_VERSION,
            "zoom": self.zoom,
            "gridOffset": [-30.0, 0.0],  # x offset keeps modules off left edge; y=0 puts row 0 at top
            "modules": [self._module_dict(m) for m in self.modules],
            "cables": [self._cable_dict(c) for c in self.cables],
        }

    def _module_dict(self, m: Module) -> dict:
        d = {
            "id": m.id,
            "plugin": m.plugin,
            "model": m.model,
            "version": self.RACK_VERSION,
            "params": [
                {"id": pid, "value": val}
                for pid, val in sorted(m._param_values.items())
            ],
            "pos": m.pos,
        }
        if m._extra_data:
            d["data"] = m._extra_data
        return d

    def _cable_dict(self, c: Cable) -> dict:
        return {
            "id": random.randint(10**14, 10**16),
            "outputModuleId": c.output.module.id,
            "outputId": c.output.port_id,
            "inputModuleId": c.input.module.id,
            "inputId": c.input.port_id,
            "color": c.color,
        }

    def save(self, path: str):
        """Save to a .vcv file (zstd-compressed tar archive)."""
        from .serialize import save_vcv
        save_vcv(self.to_dict(), path)
        print(f"Saved: {path}  ({len(self.modules)} modules, {len(self.cables)} cables)")

    def summary(self):
        """Print a human-readable summary of the patch."""
        print(f"Patch: {len(self.modules)} modules, {len(self.cables)} cables")
        print("\nModules:")
        for m in self.modules:
            print(f"  {m.plugin}/{m.model}  pos={m.pos}")
        print("\nCables:")
        for c in self.cables:
            o, i = c.output, c.input
            print(f"  {o.module.model}[out {o.port_id}] -> {i.module.model}[in {i.port_id}]  {c.cable_type.value}")
