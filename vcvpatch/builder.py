"""
PatchBuilder: fluent, live-proven patch construction API.

Every operation returns a chainable object. The SignalGraph is kept in sync
incrementally -- proof state is accurate at every intermediate step, not just
at save time.

    pb = PatchBuilder()
    lfo   = pb.module("Fundamental", "LFO",  FREQ=0.4)
    vco   = pb.module("Fundamental", "VCO",  FREQ=0.0, PW=0.5)
    vcf   = pb.module("Fundamental", "VCF",  FREQ=0.6)
    audio = pb.module("Core", "AudioInterface2")

    (pb.chain(vco.SQR, vcf.i.IN)
         .fan_out(audio.i.IN_L, audio.i.IN_R, color=COLORS["green"]))

    (lfo.modulates(vco.i.PWM,    attenuation=0.5, color=COLORS["blue"])
        .modulates(vcf.i.CUTOFF, attenuation=0.5, color=COLORS["purple"]))

    compiled = pb.compile()   # raises PatchCompileError if not proven
    compiled.save("patch.vcv")
    # or in one step: pb.save("patch.vcv")
"""

from __future__ import annotations
from typing import Optional
from .core import Patch, Module, Port, COLORS, _load_discovered, _port_name_by_id, _param_name_by_id
from .graph import SignalGraph, Edge
from .graph.modules import NODE_REGISTRY
from .graph.node import UnknownNode

_YELLOW = COLORS["yellow"]


# ---------------------------------------------------------------------------
# Compile output and error
# ---------------------------------------------------------------------------

class PatchCompileError(Exception):
    """Raised by PatchBuilder.compile() when the patch is not proven."""


class CompiledPatch:
    """
    The validated output of PatchBuilder.compile().

    Holds the frozen patch dict and the proven SignalGraph.
    Call .save(path) to write to disk.
    """

    def __init__(self, patch_dict: dict, graph: SignalGraph):
        self.patch_dict = patch_dict
        self.graph      = graph

    def save(self, path: str) -> str:
        """Write the patch to a .vcv file. Returns the path on success."""
        from .serialize import save_vcv
        save_vcv(self.patch_dict, path)
        return path


# ---------------------------------------------------------------------------
# Internal record type for describe()
# ---------------------------------------------------------------------------

class _ConnectionRecord:
    __slots__ = ("src_label", "dst_label", "color", "role", "attenuation")

    def __init__(self, src_label: str, dst_label: str,
                 color: str, role: str, attenuation: float = None):
        self.src_label  = src_label
        self.dst_label  = dst_label
        self.color      = color
        self.role       = role          # "audio" | "modulation"
        self.attenuation = attenuation


# ---------------------------------------------------------------------------
# SignalChain
# ---------------------------------------------------------------------------

class SignalChain:
    """
    Tracks audio cables being laid. tail is the last port in the chain;
    fan_out / to extend it.
    """

    def __init__(self, tail: Port, builder: "PatchBuilder"):
        self._tail   = tail
        self._builder = builder

    @property
    def tail(self) -> Port:
        """Last port in the chain (may be input or output)."""
        return self._tail

    def to(self, port: Port, color: str = None) -> "SignalChain":
        """Extend chain: tail -> port.  Advances tail to the computed output."""
        src = self._resolve_src()
        self._builder._add_cable(src, port, color or _YELLOW, role="audio")
        computed = self._builder._compute_output(port)
        self._tail = computed if computed is not None else port
        return self

    def fan_out(self, *ports: Port, color: str = None) -> "SignalChain":
        """Create cables from tail to every destination in ports."""
        src = self._resolve_src()
        cable_color = color or _YELLOW
        for port in ports:
            self._builder._add_cable(src, port, cable_color, role="audio")
        return self

    # -- Internal ------------------------------------------------------------

    def _resolve_src(self) -> Port:
        """
        If tail is an input port, compute the module's primary audio output
        (e.g. VCF.IN -> VCF.LPF).  Returns an output Port.
        """
        if self._tail.is_output:
            return self._tail
        computed = self._builder._compute_output(self._tail)
        return computed if computed is not None else self._tail


# ---------------------------------------------------------------------------
# ModuleHandle
# ---------------------------------------------------------------------------

class ModuleHandle:
    """
    Wraps Module; delegates port access and provides modulates() for CV routing.
    """

    def __init__(self, module: Module, builder: "PatchBuilder"):
        self._module  = module
        self._builder = builder

    # -- Port access ---------------------------------------------------------

    def __getattr__(self, name: str) -> Port:
        # Called only for names not found normally (not _module, i, o, modulates).
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._module, name)

    @property
    def i(self) -> "_InputAccessorProxy":
        return _InputAccessorProxy(self._module)

    @property
    def o(self) -> "_OutputAccessorProxy":
        return _OutputAccessorProxy(self._module)

    def out_id(self, port_id: int) -> Port:
        """Return an output Port by numeric ID (for modules with unnamed ports)."""
        return self._module.output(port_id)

    def in_id(self, port_id: int) -> Port:
        """Return an input Port by numeric ID (for modules with unnamed ports)."""
        return self._module.input(port_id)

    # -- Modulation ----------------------------------------------------------

    def modulates(self, target_port: Port, *,
                  via: str = "SIN",
                  attenuation: float = 0.5,
                  color: str = None,
                  open_attenuator: bool = True) -> "ModuleHandle":
        """
        Create a CV cable from this module's output (via) to target_port.

        If open_attenuator=True and the destination port has a registered
        attenuator param (_port_attenuators), that param is set to attenuation
        automatically -- no manual param lookup needed.

        Returns self for chaining: lfo.modulates(...).modulates(...)
        """
        src_port = self._module._lookup_port(via, prefer_output=True)

        if open_attenuator:
            dst_module = target_port.module
            key = f"{dst_module.plugin}/{dst_module.model}"
            node_cls = NODE_REGISTRY.get(key)
            if node_cls is not None:
                param_id = node_cls._port_attenuators.get(target_port.port_id)
                if param_id is not None:
                    # Mutate _param_values -- shared with node.params by reference.
                    dst_module._param_values[param_id] = attenuation

        cable_color = color or COLORS["blue"]
        self._builder._add_cable(
            src_port, target_port, cable_color,
            role="modulation", attenuation=attenuation,
        )
        return self

    def __repr__(self) -> str:
        return f"ModuleHandle({self._module})"


class _InputAccessorProxy:
    """Delegates .NAME to module.i.NAME."""
    __slots__ = ("_m",)
    def __init__(self, module: Module):
        self._m = module
    def __getattr__(self, name: str) -> Port:
        if name.startswith("__"):
            raise AttributeError(name)
        return self._m._lookup_port(name, prefer_output=False)


class _OutputAccessorProxy:
    """Delegates .NAME to module.o.NAME."""
    __slots__ = ("_m",)
    def __init__(self, module: Module):
        self._m = module
    def __getattr__(self, name: str) -> Port:
        if name.startswith("__"):
            raise AttributeError(name)
        return self._m._lookup_port(name, prefer_output=True)


# ---------------------------------------------------------------------------
# PatchBuilder
# ---------------------------------------------------------------------------

class PatchBuilder:
    """
    Fluent patch builder with a live, always-consistent SignalGraph.

    proof state (proven, warnings) is accurate after every module() and
    cable operation -- no separate prove step.
    """

    def __init__(self, zoom: float = 1.0):
        self._patch   = Patch(zoom=zoom)
        self._graph   = SignalGraph()
        self._records: list[_ConnectionRecord] = []
        self._handles: list[ModuleHandle]      = []

    # -- Module addition -----------------------------------------------------

    def module(self, plugin: str, model: str, pos=None, data=None, **params) -> ModuleHandle:
        """
        Add a module, sync the graph node, return a ModuleHandle.

        params are keyword args matching the module's param names, same as
        Patch.add().  E.g.: pb.module("Fundamental", "VCF", FREQ=0.6)

        pos=[col, row] in Rack grid units: col in HP (1HP=5.08mm),
        row is row index (0=top row, 1=second row, ...).
        If omitted, auto-layout left-to-right on row 0.
        """
        m = self._patch.add(plugin, model, pos=pos, extra_data=data, **params)

        key = f"{plugin}/{model}"
        node_cls = NODE_REGISTRY.get(key)
        if node_cls is not None:
            # Share _param_values by reference: auto-attenuator mutations are
            # immediately visible in node.params without any sync step.
            node = node_cls(module_id=m.id, params=m._param_values)
        else:
            node = UnknownNode(
                plugin=plugin, model=model,
                module_id=m.id, params=m._param_values,
            )
        self._graph.add_node(node)

        handle = ModuleHandle(m, self)
        self._handles.append(handle)
        return handle

    # -- Audio chain ---------------------------------------------------------

    def chain(self, *ports: Port) -> SignalChain:
        """
        Create audio cables from a sequence of (output, input) port pairs
        and return a SignalChain for further chaining.

        chain(vco.SQR, vcf.i.IN)  ->  cable: VCO -> VCF
                                      tail:  VCF.LPF (computed via graph routing)

        Accepts an even number of ports: (out0, in0, out1, in1, ...).
        """
        if len(ports) < 2:
            raise ValueError("chain() requires at least 2 ports")
        if len(ports) % 2 != 0:
            raise ValueError("chain() requires an even number of ports (out, in pairs)")

        last_in: Port = ports[1]
        for i in range(0, len(ports), 2):
            out_port = ports[i]
            in_port  = ports[i + 1]
            self._add_cable(out_port, in_port, _YELLOW, role="audio")
            last_in = in_port

        return SignalChain(last_in, self)

    # -- Proof state ---------------------------------------------------------

    @property
    def proven(self) -> bool:
        """True iff patch is fully proven (modules installed, audio reachable, control complete)."""
        return self._graph.patch_proven

    @property
    def warnings(self) -> list[str]:
        """Non-fatal advisory issues (attenuators at 0, orphaned sinks, etc.)."""
        return self._graph.warnings

    @property
    def status(self) -> str:
        """One-liner summary: modules, cables, proof state, warning count."""
        n_mod  = len(self._patch.modules)
        n_cab  = len(self._patch.cables)
        n_warn = len(self._graph.warnings)
        return (
            f"{n_mod} modules, {n_cab} cables"
            f" | proven={self._graph.patch_proven}"
            f" | warnings={n_warn}"
        )

    def report(self) -> str:
        """Full SignalGraph proof report."""
        return self._graph.report()

    def describe(self) -> str:
        """
        Human-readable routing table:
          Modules section (with key params)
          Signal flow section (audio cables)
          Modulation section (CV cables with attenuation)
          Status line
        """
        lines = []

        # Modules
        lines.append("Modules:")
        for h in self._handles:
            m = h._module
            param_str = self._format_params(m)
            suffix = f"  {param_str}" if param_str else ""
            lines.append(f"  {m.plugin}/{m.model}{suffix}")
        lines.append("")

        # Signal flow
        audio = [r for r in self._records if r.role == "audio"]
        if audio:
            lines.append("Signal flow (audio):")
            for r in audio:
                lines.append(f"  {r.src_label}  ->  {r.dst_label}")
            lines.append("")

        # Modulation
        mods = [r for r in self._records if r.role == "modulation"]
        if mods:
            lines.append("Modulation (CV):")
            for r in mods:
                atn = f"  [attenuation={r.attenuation}]" if r.attenuation is not None else ""
                lines.append(f"  {r.src_label}  ->  {r.dst_label}{atn}")
            lines.append("")

        # Other roles
        other = [r for r in self._records if r.role not in ("audio", "modulation")]
        if other:
            lines.append("Other:")
            for r in other:
                lines.append(f"  {r.src_label}  ->  {r.dst_label}")
            lines.append("")

        lines.append(f"Status: {self.status}")
        return "\n".join(lines)

    # -- Save / escape hatch -------------------------------------------------

    def connect(self, src: Port, dst: Port,
                color: str = None, role: str = "cv") -> "PatchBuilder":
        """
        Connect any two ports directly. Use for clock, gate, and plain CV routing
        that does not need auto-attenuator handling. Returns self for chaining.
        """
        self._add_cable(src, dst, color or _YELLOW, role=role)
        return self

    def compile(self) -> CompiledPatch:
        """
        Validate and freeze the patch, returning a CompiledPatch ready for saving.

        Raises PatchCompileError (with the full graph report) if:
          - any module is missing
          - audio does not reach the sink
          - required control inputs are unconnected
          - any wired CV input has a zero attenuator (cable present but ignored)

        Advisory warnings do not block compilation.
        """
        if not self._graph.patch_proven:
            raise PatchCompileError(
                f"Patch is not proven -- cannot compile.\n\n"
                f"{self._graph.report()}"
            )
        return CompiledPatch(self._patch.to_dict(), self._graph)

    def save(self, path: str) -> "PatchBuilder":
        """Compile (raising PatchCompileError if not proven) and save to .vcv."""
        self.compile().save(path)
        return self

    def build(self) -> Patch:
        """Return the underlying Patch object (escape hatch)."""
        return self._patch

    # -- Internal helpers ----------------------------------------------------

    def _add_cable(self, src: Port, dst: Port, color: str, role: str,
                   attenuation: float = None) -> None:
        """Create cable in patch + edge in graph, record for describe()."""
        self._patch.connect(src, dst, color=color)
        self._graph.add_edge(Edge(
            src_node=src.module.id,
            src_port=src.port_id,
            dst_node=dst.module.id,
            dst_port=dst.port_id,
        ))
        src_label = f"{src.module.model}.{self._port_name(src)}"
        dst_label = f"{dst.module.model}.{self._port_name(dst)}"
        self._records.append(
            _ConnectionRecord(src_label, dst_label, color, role, attenuation)
        )

    def _compute_output(self, in_port: Port) -> Optional[Port]:
        """
        Given an input port, return the primary audio output of the same module
        (the lowest-numbered output port that audio would exit from).
        Returns None if the module has no audio outputs for this input
        (e.g. sinks, controllers, unknown nodes).
        """
        if in_port.is_output:
            return in_port
        node = self._graph._nodes.get(in_port.module.id)
        if node is None:
            return None
        outputs = node.audio_out_for(frozenset({in_port.port_id}))
        if not outputs:
            return None
        return Port(in_port.module, min(outputs), is_output=True)

    def _port_name(self, port: Port) -> str:
        """Resolve port_id to a human-readable name, falling back to the int."""
        discovered = _load_discovered(port.module.plugin, port.module.model)
        if discovered is None:
            return str(port.port_id)
        bucket = "outputs" if port.is_output else "inputs"
        name = _port_name_by_id(discovered.get(bucket, []), port.port_id)
        return name if name is not None else str(port.port_id)

    def _format_params(self, m: Module) -> str:
        """Format non-empty param_values as 'NAME=val, ...' using discovered metadata."""
        if not m._param_values:
            return ""
        discovered = _load_discovered(m.plugin, m.model)
        parts = []
        for pid, val in sorted(m._param_values.items()):
            name = str(pid)
            if discovered:
                resolved = _param_name_by_id(discovered.get("params", []), pid)
                if resolved:
                    name = resolved
            val_str = f"{val:g}"
            parts.append(f"{name}={val_str}")
        return ", ".join(parts)
