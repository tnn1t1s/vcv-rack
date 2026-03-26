"""
Runtime interpreter interface.

The contract is the pure value.
The runtime is an effect context.
The interpreter executes the contract in that context.

          contract  →  projection  →  interpreter
          (pure)       (context map)  (execution)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ResolvedPort:
    runtime_id:   Any   # int in Rack, string in Max, address in hardware
    runtime_name: str


@dataclass
class ResolvedParam:
    runtime_id:   Any
    runtime_name: str


class RuntimeInterpreter(ABC):
    """
    Interprets a semantic PatchPlan in a specific runtime context.

    Implementations: VCVRackInterpreter, (future) MaxMSPInterpreter, etc.
    Each reads projections for its runtime and executes against it.
    """

    @abstractmethod
    def resolve_port(self, module_id: str, port_name: str) -> ResolvedPort:
        """Map a contract port name to a runtime port identifier."""

    @abstractmethod
    def resolve_param(self, module_id: str, param_name: str) -> ResolvedParam:
        """Map a contract param name to a runtime param identifier."""

    @abstractmethod
    def emit(self, plan: "PatchPlan") -> Any:
        """Translate a semantic PatchPlan into a runtime-native patch artifact."""

    @abstractmethod
    def read_state(self) -> dict:
        """Read current state, returning values keyed by semantic param names."""

    @abstractmethod
    def set_param(self, module_id: str, param_name: str, value: float) -> None:
        """Set a parameter by semantic name and value in declared units."""
