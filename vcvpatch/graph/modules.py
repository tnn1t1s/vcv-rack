"""
Declarative semantic node registry for supported VCV Rack modules.

Module-specific graph semantics live in YAML under `vcvpatch/graph/specs/`.
This module loads that registry and preserves the historic `*Node` symbol names
as compatibility aliases for tests and existing imports.
"""

from __future__ import annotations

from .specs import load_semantic_node_specs


NODE_REGISTRY: dict[str, type] = load_semantic_node_specs()


_ALIASES = {
    "AudioInterface2Node": "Core/AudioInterface2",
    "MidiMapNode": "Core/MidiMap",
    "AudioInterface8Node": "Core/Audio8",
    "Audio16Node": "Core/Audio16",
    "VCONode": "Fundamental/VCO",
    "VCFNode": "Fundamental/VCF",
    "VCANode": "Fundamental/VCA",
    "NoiseNode": "Fundamental/Noise",
    "MultNode": "Fundamental/Mult",
    "FundamentalADSRNode": "Fundamental/ADSR",
    "FundamentalLFONode": "Fundamental/LFO",
    "SEQ3Node": "Fundamental/SEQ3",
    "PlateauNode": "Valley/Plateau",
    "BogaudioADSRNode": "Bogaudio/Bogaudio-ADSR",
    "BogaudioDADSRHNode": "Bogaudio/Bogaudio-DADSRH",
    "BogaudioLFONode": "Bogaudio/Bogaudio-LFO",
    "BogaudioSampleHoldNode": "Bogaudio/Bogaudio-SampleHold",
    "BogaudioAddrSeqNode": "Bogaudio/Bogaudio-AddrSeq",
    "BogaudioRGateNode": "Bogaudio/Bogaudio-RGate",
    "BogaudioPgmrNode": "Bogaudio/Bogaudio-Pgmr",
    "PressurNode": "Bogaudio/Bogaudio-Pressor",
    "BogaudioMix2Node": "Bogaudio/Bogaudio-Mix2",
    "BogaudioMix4Node": "Bogaudio/Bogaudio-Mix4",
    "BogaudioMix8Node": "Bogaudio/Bogaudio-Mix8",
    "Chronoblob2Node": "AlrightDevices/Chronoblob2",
    "EvenVCONode": "Befaco/EvenVCO",
    "KickallNode": "Befaco/Kickall",
    "BefacoMixerNode": "Befaco/Mixer",
    "ClockedNode": "ImpromptuModular/Clocked-Clkd",
    "PlaitsNode": "AudibleInstruments/Plaits",
    "RingsNode": "AudibleInstruments/Rings",
    "CloudsNode": "AudibleInstruments/Clouds",
    "MarblesNode": "AudibleInstruments/Marbles",
    "PurfenatorNode": "DanTModules/Purfenator",
    "MscHackMix934Node": "mscHack/Mix_9_3_4",
    "DrumKitNode": "dbRackModules/DrumKit",
    "DrumKitSequencerNode": "DrumKit/Sequencer",
    "DBRackDrumsNode": "dbRackModules/Drums",
    "UtilSendNode": "VultModulesFree/UtilSend",
    "SpectrumAnalyzerNode": "ArhythmeticUnits-Fourier/SpectrumAnalyzer",
    "NoteSeq16Node": "JW-Modules/NoteSeq16",
    "SubstationClockNode": "SlimeChild-Substation/SlimeChild-Substation-Clock",
    "SubstationEnvelopesNode": "SlimeChild-Substation/SlimeChild-Substation-Envelopes",
    "SubstationFilterNode": "SlimeChild-Substation/SlimeChild-Substation-Filter",
    "SubstationVCANode": "SlimeChild-Substation/SlimeChild-Substation-VCA",
    "SubstationMixerNode": "SlimeChild-Substation/SlimeChild-Substation-Mixer",
    "SubstationQuantizerNode": "SlimeChild-Substation/SlimeChild-Substation-Quantizer",
    "SubstationSubOscillatorNode": "SlimeChild-Substation/SlimeChild-Substation-SubOscillator",
    "SubstationPolySeqNode": "SlimeChild-Substation/SlimeChild-Substation-PolySeq",
    "CountModulaSequencer16Node": "CountModula/Sequencer16",
    "CountModulaGateSequencer16Node": "CountModula/GateSequencer16",
    "ChordCVNode": "AaronStatic/ChordCV",
    "AttenuateNode": "AgentRack/Attenuate",
    "AgentRackNoiseNode": "AgentRack/Noise",
    "CrinkleNode": "AgentRack/Crinkle",
    "AgentRackADSRNode": "AgentRack/ADSR",
    "InspectorNode": "AgentRack/Inspector",
    "LadderNode": "AgentRack/Ladder",
    "SaphireNode": "AgentRack/Saphire",
    "SonicNode": "AgentRack/Sonic",
    "VCMixerNode": "Fundamental/VCMixer",
    "SumNode": "Fundamental/Sum",
    "BogaudioVCFNode": "Bogaudio/Bogaudio-VCF",
    "FundamentalRandomNode": "Fundamental/Random",
    "QuantizerNode": "Fundamental/Quantizer",
    "CoffeeQuantNode": "Coffee/Quant",
    "RandomValuesNode": "Fundamental/RandomValues",
    "SimpleClockNode": "JW-Modules/SimpleClock",
    "BogaudioLVCFNode": "Bogaudio/Bogaudio-LVCF",
    "BusCrushNode": "AgentRack/BusCrush",
    "SplitNode": "Fundamental/Split",
    "TonnetzNode": "AgentRack/Tonnetz",
    "ClockDivNode": "AgentRack/ClockDiv",
}

globals().update({alias: NODE_REGISTRY[key] for alias, key in _ALIASES.items()})

__all__ = ["NODE_REGISTRY", *_ALIASES.keys()]
