"""
Core classes: Patch, Module, Port, Cable.
"""

import random
from typing import Optional, Union
from .registry import MODULES


# Cable colors (VCV Rack default palette)
COLORS = {
    "yellow":  "#ffb437",
    "red":     "#f44336",
    "blue":    "#2196f3",
    "green":   "#4caf50",
    "white":   "#e0e0e0",
    "purple":  "#9c27b0",
    "orange":  "#ff9800",
    "cyan":    "#00bcd4",
    "pink":    "#e91e63",
    "lime":    "#8bc34a",
}

_DEFAULT_COLOR = COLORS["yellow"]


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

        key = f"{plugin}/{model}"
        self._def = MODULES.get(key)

    # -- Port access by name -------------------------------------------------

    def _lookup_port(self, name: str, prefer_output=None) -> Port:
        """Resolve a port name to a Port, checking outputs then inputs (or vice versa)."""
        d = self._def
        if d is None:
            raise ValueError(
                f"Module {self.plugin}/{self.model} not in registry. "
                f"Use .i(id) or .o(id) for raw port access."
            )
        name_upper = name.upper()
        outputs = d["outputs"]
        inputs = d["inputs"]

        if prefer_output is True:
            if name_upper in outputs:
                return Port(self, outputs[name_upper], is_output=True)
            raise AttributeError(f"No output '{name}' on {self.model}. Available: {list(outputs)}")

        if prefer_output is False:
            if name_upper in inputs:
                return Port(self, inputs[name_upper], is_output=False)
            raise AttributeError(f"No input '{name}' on {self.model}. Available: {list(inputs)}")

        # Auto: try outputs first, then inputs
        if name_upper in outputs:
            return Port(self, outputs[name_upper], is_output=True)
        if name_upper in inputs:
            return Port(self, inputs[name_upper], is_output=False)

        raise AttributeError(
            f"No port '{name}' on {self.model}.\n"
            f"  Outputs: {list(outputs)}\n"
            f"  Inputs:  {list(inputs)}"
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


class Cable:
    def __init__(self, output: Port, input: Port, color: str = _DEFAULT_COLOR):
        assert output.is_output, "First argument must be an output port"
        assert not input.is_output, "Second argument must be an input port"
        self.output = output
        self.input = input
        self.color = color


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

        params are keyword args matching the module's param names (case-insensitive).
        E.g.: patch.add("Fundamental", "VCF", FREQ=0.5, RES=0.3)

        pos=[col, row] in HP units. If omitted, auto-layout left-to-right.
        """
        if pos is None:
            pos = [self._col, self._row]
            self._col += 8  # advance by ~8HP per module (rough)

        # Resolve param names -> param IDs
        key = f"{plugin}/{model}"
        defn = MODULES.get(key)
        param_values = {}
        for name, value in params.items():
            if defn and name.upper() in defn["params"]:
                pid = defn["params"][name.upper()]
            elif defn and name in defn["params"]:
                pid = defn["params"][name]
            elif isinstance(name, int):
                pid = name
            else:
                # Try interpreting as integer string
                try:
                    pid = int(name)
                except ValueError:
                    raise ValueError(
                        f"Unknown param '{name}' for {plugin}/{model}. "
                        f"Known: {list(defn['params']) if defn else 'module not in registry'}"
                    )
            param_values[pid] = float(value)

        m = Module(self, plugin, model, pos, param_values, extra_data=extra_data)
        self.modules.append(m)
        return m

    # -- Cable connections ---------------------------------------------------

    def _cable(self, output: Port, input: Port, color: str = None) -> Cable:
        c = Cable(output, input, color or _DEFAULT_COLOR)
        self.cables.append(c)
        return c

    def connect(self, output: Port, input: Port, color: str = None) -> Cable:
        """Explicitly connect two ports. Also works via >> operator."""
        return self._cable(output, input, color)

    def connect_all(self, source: Port, *destinations: Port, color: str = None):
        """Fan out one output to multiple inputs."""
        for dst in destinations:
            self._cable(source, dst, color)

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
            print(f"  {o.module.model}[out {o.port_id}] -> {i.module.model}[in {i.port_id}]  {c.color}")
