"""
Node base classes for the signal graph.

Every module type is a subclass of Node. Provability is a structural property:
a SignalGraph constructed from Nodes always knows whether audio reaches the sink
AND whether all required control signals on the audio chain are connected.

Signal types
------------
Every port carries exactly one signal type:
  AUDIO  -- audio-rate signal (oscillator output, filter output, etc.)
  CV     -- continuous control voltage (envelope output, LFO output, etc.)
  GATE   -- binary 0V/10V gate or trigger (sequencer gate, ADSR gate input)
  CLOCK  -- clock pulse / tempo signal (clock output, clock divider output)

Required control inputs
-----------------------
Nodes on the audio chain may declare _required_cv: {port_id: SignalType}.
These are inputs that must be connected to a source of the matching type
for the node to function correctly. Missing required control inputs are
reported as control_gaps by SignalGraph -- a patch is only fully proven
when there are none.

Node hierarchy
--------------
  Node (abstract)
    AudioSourceNode    -- generates audio without audio input
    AudioProcessorNode -- routes audio from specific inputs to specific outputs
    AudioMixerNode     -- any audio input activates all audio outputs
    AudioSinkNode      -- terminal consumer of audio (AudioInterface2)
    ControllerNode     -- produces CV/Gate/Clock; declares output signal types
    UnknownNode        -- not in registry; opaque (blocks audio propagation)
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import ClassVar


class SignalType(Enum):
    AUDIO = auto()
    CV    = auto()
    GATE  = auto()
    CLOCK = auto()


class Node(ABC):
    """
    A module instance in the signal graph.

    Class-level PLUGIN / MODEL identify the module type.
    _required_cv: inputs that must be connected for the node to work correctly.
    _output_types: signal type emitted by each output port.
    """

    PLUGIN: ClassVar[str]
    MODEL:  ClassVar[str]

    # {port_id: SignalType} -- required non-audio control inputs
    _required_cv: ClassVar[dict[int, SignalType]] = {}

    # {port_id: SignalType} -- what each output port emits
    _output_types: ClassVar[dict[int, SignalType]] = {}

    # {input_port_id: param_id} -- attenuator param that scales a CV input.
    # If the param is 0 and the port is connected, the signal has no effect.
    _port_attenuators: ClassVar[dict[int, int]] = {}

    def __init__(self, module_id: int, params: dict[int, float]):
        self.module_id = module_id
        self.params    = params

    @abstractmethod
    def audio_out_for(self, audio_in_ports: frozenset[int]) -> frozenset[int]:
        """
        Given which input port IDs currently carry audio,
        return which output port IDs emit audio.
        """
        ...

    def __repr__(self) -> str:
        return f"{self.PLUGIN}/{self.MODEL}#{self.module_id}"

    def output_signal_types_for(
        self, input_signal_types: dict[int, frozenset[SignalType]]
    ) -> dict[int, frozenset[SignalType]]:
        """
        Return the signal types currently emitted by each output port.

        Default implementation is for static control-style outputs declared in
        _output_types. Audio subclasses override this to account for routed
        audio, and passthrough nodes can override it to preserve upstream types.
        """
        return {
            port_id: frozenset({sig})
            for port_id, sig in self._output_types.items()
        }


# ---------------------------------------------------------------------------
# Audio node bases
# ---------------------------------------------------------------------------

class AudioSourceNode(Node):
    """Generates audio without needing audio input."""

    _audio_outputs: ClassVar[frozenset[int]]

    def audio_out_for(self, audio_in_ports: frozenset[int]) -> frozenset[int]:
        return self._audio_outputs

    def output_signal_types_for(
        self, input_signal_types: dict[int, frozenset[SignalType]]
    ) -> dict[int, frozenset[SignalType]]:
        outputs = super().output_signal_types_for(input_signal_types)
        for port_id in self._audio_outputs:
            outputs[port_id] = outputs.get(port_id, frozenset()) | frozenset({SignalType.AUDIO})
        return outputs


class AudioProcessorNode(Node):
    """
    Routes audio from specific inputs to specific outputs.
    Optionally declares _required_cv for control inputs that must be connected.
    """

    _routes: ClassVar[list[tuple[int, int]]]  # (in_port, out_port)

    def audio_out_for(self, audio_in_ports: frozenset[int]) -> frozenset[int]:
        return frozenset(
            out for (inp, out) in self._routes
            if inp in audio_in_ports
        )

    def output_signal_types_for(
        self, input_signal_types: dict[int, frozenset[SignalType]]
    ) -> dict[int, frozenset[SignalType]]:
        outputs = super().output_signal_types_for(input_signal_types)
        for inp, out in self._routes:
            if SignalType.AUDIO in input_signal_types.get(inp, frozenset()):
                outputs[out] = outputs.get(out, frozenset()) | frozenset({SignalType.AUDIO})
        return outputs


class AudioMixerNode(Node):
    """Any audio input activates all audio outputs."""

    _audio_inputs:  ClassVar[frozenset[int]]
    _audio_outputs: ClassVar[frozenset[int]]

    def audio_out_for(self, audio_in_ports: frozenset[int]) -> frozenset[int]:
        if audio_in_ports & self._audio_inputs:
            return self._audio_outputs
        return frozenset()

    def output_signal_types_for(
        self, input_signal_types: dict[int, frozenset[SignalType]]
    ) -> dict[int, frozenset[SignalType]]:
        outputs = super().output_signal_types_for(input_signal_types)
        if any(SignalType.AUDIO in input_signal_types.get(inp, frozenset())
               for inp in self._audio_inputs):
            for port_id in self._audio_outputs:
                outputs[port_id] = outputs.get(port_id, frozenset()) | frozenset({SignalType.AUDIO})
        return outputs


class AudioSinkNode(Node):
    """Terminal audio consumer. No audio outputs."""

    _audio_inputs: ClassVar[frozenset[int]]

    def audio_out_for(self, audio_in_ports: frozenset[int]) -> frozenset[int]:
        return frozenset()

    def receives_audio(self, audio_in_ports: frozenset[int]) -> bool:
        return bool(audio_in_ports & self._audio_inputs)


# ---------------------------------------------------------------------------
# Control node base
# ---------------------------------------------------------------------------

class ControllerNode(Node):
    """
    Produces CV, Gate, or Clock signals -- never audio.
    _output_types declares the signal type of each output port.
    """

    def audio_out_for(self, audio_in_ports: frozenset[int]) -> frozenset[int]:
        return frozenset()


class PassThroughNode(AudioProcessorNode):
    """
    Generic pass-through node whose outputs inherit the signal types present on
    the routed input ports.
    """

    def output_signal_types_for(
        self, input_signal_types: dict[int, frozenset[SignalType]]
    ) -> dict[int, frozenset[SignalType]]:
        outputs = super().output_signal_types_for(input_signal_types)
        for inp, out in self._routes:
            if input_signal_types.get(inp):
                outputs[out] = outputs.get(out, frozenset()) | input_signal_types[inp]
        return outputs


# ---------------------------------------------------------------------------
# Unknown
# ---------------------------------------------------------------------------

class UnknownNode(Node):
    """
    Module not in the registry. Treated as opaque: produces no audio.
    The proof only asserts audio_reachable when every node on the path
    is fully accounted for. Unknown nodes on the audio path are reported
    as registry gaps, not silently papered over.
    """

    PLUGIN: str
    MODEL:  str

    def __init__(self, plugin: str, model: str, module_id: int, params: dict[int, float]):
        self.PLUGIN = plugin
        self.MODEL  = model
        super().__init__(module_id, params)

    def audio_out_for(self, audio_in_ports: frozenset[int]) -> frozenset[int]:
        return frozenset()
