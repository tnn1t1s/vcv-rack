"""
PatchLoader: reads a .vcv file and constructs a SignalGraph.

The loader is the only place that touches the raw JSON format.
Everything above this layer works with typed Node/Edge objects.
"""

from __future__ import annotations
from .signal_graph import SignalGraph, Edge
from .modules import NODE_REGISTRY
from .node import UnknownNode


class PatchLoader:
    @staticmethod
    def load(path: str) -> SignalGraph:
        from vcvpatch.serialize import load_vcv
        patch = load_vcv(path)
        return PatchLoader.from_dict(patch)

    @staticmethod
    def from_dict(patch: dict) -> SignalGraph:
        graph = SignalGraph()

        for mod in patch.get("modules", []):
            plugin = mod["plugin"]
            model = mod["model"]
            key = f"{plugin}/{model}"
            params = {p["id"]: p["value"] for p in mod.get("params", [])}

            node_cls = NODE_REGISTRY.get(key)
            if node_cls is not None:
                node = node_cls(module_id=mod["id"], params=params)
            else:
                node = UnknownNode(
                    plugin=plugin, model=model,
                    module_id=mod["id"], params=params,
                )

            graph.add_node(node)

        for cable in patch.get("cables", []):
            graph.add_edge(Edge(
                src_node=cable["outputModuleId"],
                src_port=cable["outputId"],
                dst_node=cable["inputModuleId"],
                dst_port=cable["inputId"],
            ))

        return graph
