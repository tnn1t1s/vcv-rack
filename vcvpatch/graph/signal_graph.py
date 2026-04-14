"""
SignalGraph: owns Nodes and Edges; audio reachability is always a current property.

Construction invariant: after any add_node / add_edge call,
audio_reachable, audio_chain, and warnings are immediately accurate.
No separate "prove" step exists or is needed.

UnknownNode policy: opaque. Produces no audio. The proof only asserts
audio_reachable when every node on the path is fully accounted for.
"""

from __future__ import annotations
from dataclasses import dataclass
from .node import (
    Node, AudioSourceNode, AudioProcessorNode, AudioMixerNode,
    AudioSinkNode, ControllerNode, UnknownNode, SignalType,
)
from .installed import InstalledRegistry


@dataclass(frozen=True)
class Edge:
    """A cable: one output port to one input port."""
    src_node: int   # module_id
    src_port: int   # output port id
    dst_node: int   # module_id
    dst_port: int   # input port id


class SignalGraph:
    """
    The patch as a typed signal graph.

    Properties audio_reachable, audio_chain, and warnings are computed
    on demand from the current graph topology -- always consistent with
    the nodes and edges that have been added.
    """

    def __init__(self):
        self._nodes: dict[int, Node] = {}   # module_id -> Node
        self._edges: list[Edge] = []

    # -- Construction --------------------------------------------------------

    def add_node(self, node: Node) -> None:
        self._nodes[node.module_id] = node

    def add_edge(self, edge: Edge) -> None:
        self._edges.append(edge)

    # -- Public properties (always current) ----------------------------------

    @property
    def audio_reachable(self) -> bool:
        """True iff audio reaches at least one AudioSinkNode."""
        audio_in = self._propagate()
        return any(
            isinstance(n, AudioSinkNode)
            and n.receives_audio(audio_in.get(n.module_id, frozenset()))
            for n in self._nodes.values()
        )

    @property
    def audio_chain(self) -> list[Node]:
        """All nodes through which audio flows, from sources to sinks."""
        audio_in = self._propagate()
        result = []
        for node in self._nodes.values():
            ports_in = audio_in.get(node.module_id, frozenset())
            ports_out = node.audio_out_for(ports_in)
            if isinstance(node, AudioSourceNode):
                result.append(node)
            elif isinstance(node, AudioSinkNode) and node.receives_audio(ports_in):
                result.append(node)
            elif ports_in and ports_out:
                result.append(node)
        return result

    def missing_modules(self, installed: InstalledRegistry = None) -> list[Node]:
        """
        Nodes whose plugin/model is not present in the installed VCV Rack plugins.
        A patch with missing modules cannot produce audio -- existence is the
        zeroth condition in any reachability proof.
        """
        reg = installed or InstalledRegistry.default()
        return [
            n for n in self._nodes.values()
            if not reg.has(n.PLUGIN, n.MODEL)
        ]

    @property
    def patch_proven(self) -> bool:
        """
        The patch is fully proven when:
          1. All modules are installed
          2. Audio reaches the sink
          3. All required control inputs on the audio chain are connected
          4. No wired CV input is silenced by a zero attenuator
        """
        return (
            not self.missing_modules()
            and self.audio_reachable
            and self.control_complete
            and not self.attenuator_errors
        )

    @property
    def control_complete(self) -> bool:
        """True iff every required control input on the audio chain is connected."""
        return not self.control_gaps

    @property
    def control_gaps(self) -> list[tuple[Node, int, SignalType]]:
        """
        For each node on the audio chain, required control inputs that are
        either unconnected or connected to a source that emits the wrong signal type.

        Returns (node, port_id, required_signal_type) tuples.
        Each tuple is a specific wiring gap that must be fixed.
        """
        # Build: for each (module_id, input_port) -> set of source signal types
        input_signal_types: dict[tuple[int, int], set[SignalType]] = {}
        for edge in self._edges:
            src = self._nodes.get(edge.src_node)
            if src is None:
                continue
            sig = src._output_types.get(edge.src_port)
            key = (edge.dst_node, edge.dst_port)
            if sig is not None:
                input_signal_types.setdefault(key, set()).add(sig)

        gaps = []
        for node in self.audio_chain:
            for port_id, required_type in node._required_cv.items():
                sources = input_signal_types.get((node.module_id, port_id), set())
                if required_type not in sources:
                    gaps.append((node, port_id, required_type))
        return gaps

    @property
    def unknown_nodes(self) -> list[UnknownNode]:
        """Nodes not in the module registry. They block audio propagation."""
        return [n for n in self._nodes.values() if isinstance(n, UnknownNode)]

    @property
    def audio_sources(self) -> list[Node]:
        return [n for n in self._nodes.values() if isinstance(n, AudioSourceNode)]

    @property
    def audio_sinks(self) -> list[Node]:
        return [n for n in self._nodes.values() if isinstance(n, AudioSinkNode)]

    @property
    def attenuator_errors(self) -> list[str]:
        """
        CV inputs that are wired but whose attenuator param is 0.

        This is a hard error, not a warning: the cable carries signal but the
        module ignores it entirely, so the connection is effectively absent.
        Reported separately from warnings so callers can treat it as a
        compile-time failure.
        """
        errors = []
        for node in self._nodes.values():
            for in_port, param_id in node._port_attenuators.items():
                port_has_connection = any(
                    e.dst_node == node.module_id and e.dst_port == in_port
                    for e in self._edges
                )
                if port_has_connection and node.params.get(param_id, 0.0) == 0.0:
                    errors.append(
                        f"{node}: port[{in_port}] is connected but "
                        f"attenuator param[{param_id}] is 0 -- signal has no effect"
                    )
        return errors

    @property
    def warnings(self) -> list[str]:
        """
        Non-fatal advisory issues. Does not include attenuator_errors (those
        are hard errors checked by build()).
        """
        issues = []
        audio_in = self._propagate()

        for node in self._nodes.values():
            ports_in = audio_in.get(node.module_id, frozenset())

            # Sink with nothing connected
            if isinstance(node, AudioSinkNode) and not ports_in:
                issues.append(f"{node}: nothing connected to audio inputs")

            # Key audio nodes with param[0] = 0.0 (often master/level)
            if node.params.get(0, 1.0) == 0.0:
                if isinstance(node, (AudioSinkNode, AudioProcessorNode, AudioMixerNode)):
                    issues.append(f"{node}: param[0] (level/volume) is 0 -- may be muted")

            # Unknown node with audio arriving -- it's a gap in registry coverage
            if isinstance(node, UnknownNode) and ports_in:
                issues.append(
                    f"{node}: not in module registry; audio arrives here but cannot propagate"
                    f" -- add {node.PLUGIN}/{node.MODEL} to modules.py"
                )

        return issues

    def report(self) -> str:
        """Human-readable reachability report."""
        lines = []
        lines.append(f"Nodes: {len(self._nodes)}  Edges: {len(self._edges)}")
        lines.append("")

        # Zeroth check: existence
        missing = self.missing_modules()
        if missing:
            lines.append(f"MODULES MISSING ({len(missing)}) -- cannot prove reachability:")
            for n in missing:
                lines.append(f"  ! {n.PLUGIN}/{n.MODEL}")
            lines.append("")
            lines.append("AUDIO REACHABLE: unknown (missing modules)")
            return "\n".join(lines)
        lines.append("All modules installed: yes")
        lines.append("")

        # Unknown nodes block the proof even if installed
        unknown = self.unknown_nodes
        if unknown:
            lines.append(f"MODULE REGISTRY GAPS ({len(unknown)}) -- add these to modules.py:")
            for n in unknown:
                lines.append(f"  ? {n.PLUGIN}/{n.MODEL}")
            lines.append("")

        if self.audio_reachable:
            lines.append("AUDIO REACHABLE: yes")
        else:
            lines.append("AUDIO REACHABLE: NO -- patch will be silent")

        gaps = self.control_gaps
        if gaps:
            lines.append("")
            lines.append(f"CONTROL INCOMPLETE ({len(gaps)}) -- required CV/Gate/Clock inputs missing:")
            for node, port_id, sig_type in gaps:
                lines.append(f"  ! {node}  port[{port_id}] requires {sig_type.name}")
            lines.append("CONTROL COMPLETE: no")
        else:
            lines.append("CONTROL COMPLETE: yes")

        lines.append("")
        if self.patch_proven:
            lines.append("PATCH PROVEN: yes")
        else:
            lines.append("PATCH PROVEN: NO")

        chain = self.audio_chain
        if chain:
            lines.append("")
            lines.append("Audio chain:")
            for node in chain:
                lines.append(f"  {node}")

        attn_errs = self.attenuator_errors
        if attn_errs:
            lines.append("")
            lines.append(f"ATTENUATOR ERRORS ({len(attn_errs)}) -- connected CV with zero attenuation:")
            for e in attn_errs:
                lines.append(f"  ! {e}")

        warns = self.warnings
        if warns:
            lines.append("")
            lines.append("Warnings:")
            for w in warns:
                lines.append(f"  ! {w}")

        orphans = self._orphaned_nodes()
        if orphans:
            lines.append("")
            lines.append("Orphaned (no outputs connected):")
            for node in orphans:
                lines.append(f"  {node}")

        return "\n".join(lines)

    # -- Internal ------------------------------------------------------------

    def _propagate(self) -> dict[int, frozenset[int]]:
        """
        Forward propagation: for each node, compute which input ports carry audio.

        Iterates to a fixed point. Cycles terminate because audio_in sets can
        only grow, bounded by the finite port count.

        UnknownNode.audio_out_for returns frozenset() so propagation stops
        at any unregistered module.
        """
        audio_in: dict[int, set[int]] = {mid: set() for mid in self._nodes}
        changed = True

        while changed:
            changed = False
            for edge in self._edges:
                src = self._nodes.get(edge.src_node)
                if src is None:
                    continue

                src_audio_out = src.audio_out_for(frozenset(audio_in[edge.src_node]))

                if edge.src_port in src_audio_out:
                    if edge.dst_port not in audio_in[edge.dst_node]:
                        audio_in[edge.dst_node].add(edge.dst_port)
                        changed = True

        return {mid: frozenset(ports) for mid, ports in audio_in.items()}

    def _orphaned_nodes(self) -> list[Node]:
        """Nodes with no output edges (may be dead ends in the patch)."""
        nodes_with_outputs = {e.src_node for e in self._edges}
        skip_models = {"Notes", "Blank", "Label", "SpectrumAnalyzer", "Scope", "Viz",
                       "AudioInterface2", "Audio8", "Audio16"}
        return [
            n for n in self._nodes.values()
            if n.module_id not in nodes_with_outputs
            and n.MODEL not in skip_models
        ]
