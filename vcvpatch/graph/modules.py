"""
Concrete Node subclass for every supported VCV Rack module.

Each class declares:
  - PLUGIN / MODEL           -- identity
  - audio routing            -- via inherited audio_out_for
  - _output_types            -- signal type of each output port
  - _required_cv             -- non-audio inputs that must be connected
                                for the node to function on the audio chain

NODE_REGISTRY maps "plugin/model" -> class, used by PatchLoader.
"""

from __future__ import annotations
from .node import (
    AudioSourceNode, AudioProcessorNode, AudioMixerNode,
    AudioSinkNode, ControllerNode, SignalType,
    PassThroughNode,
)

CV    = SignalType.CV
GATE  = SignalType.GATE
CLOCK = SignalType.CLOCK
AUDIO = SignalType.AUDIO


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------

class AudioInterface2Node(AudioSinkNode):
    PLUGIN = "Core"
    MODEL  = "AudioInterface2"
    _audio_inputs = frozenset({0, 1})           # IN_L=0, IN_R=1


class MidiMapNode(ControllerNode):
    """Core/MidiMap -- maps MIDI CC to any module param.

    Pure side-effect controller: no audio, no required CV inputs.
    Injected into patches for runtime param control via vcvpatch.runtime.
    Presence never affects patch_proven.
    """
    PLUGIN = "Core"
    MODEL  = "MidiMap"


class AudioInterface8Node(AudioSinkNode):
    PLUGIN = "Core"
    MODEL  = "Audio8"
    _audio_inputs = frozenset(range(8))


class Audio16Node(AudioSinkNode):
    PLUGIN = "Core"
    MODEL  = "Audio16"
    _audio_inputs = frozenset(range(16))


# ---------------------------------------------------------------------------
# Fundamental
# ---------------------------------------------------------------------------

class VCONode(AudioSourceNode):
    PLUGIN = "Fundamental"
    MODEL  = "VCO"
    _audio_outputs    = frozenset({0, 1, 2, 3})   # SIN, TRI, SAW, SQR
    # Both CV inputs have attenuator params that default to 0.
    # Connecting without opening them has zero audible effect.
    _port_attenuators = {
        1: 4,   # FM  input (port 1) -> FM_PARAM (param 4)
        3: 6,   # PWM input (port 3) -> PW_CV_PARAM (param 6)
    }


class VCFNode(AudioProcessorNode):
    PLUGIN = "Fundamental"
    MODEL  = "VCF"
    # IN (port 3) -> LPF (port 0), HPF (port 1)
    _routes = [(3, 0), (3, 1)]
    # FREQ CV (port 0) has an attenuator at param 3; connecting without opening it has no effect
    _port_attenuators = {0: 3}


class VCANode(AudioProcessorNode):
    PLUGIN = "Fundamental"
    MODEL  = "VCA"
    # IN1 (port 2) -> OUT1 (port 0); IN2 (port 5) -> OUT2 (port 1)
    _routes = [(2, 0), (5, 1)]
    # LIN1/CV (port 1) must be connected; without it VCA stays at LEVEL1 param
    # (which defaults to 0 -- silent). This is the most common patch mistake.
    _required_cv = {1: CV}


class NoiseNode(AudioSourceNode):
    PLUGIN = "Fundamental"
    MODEL  = "Noise"
    _audio_outputs = frozenset({0, 1, 2, 3, 4, 5, 6})  # WHITE..BLACK


class MultNode(AudioProcessorNode):
    PLUGIN = "Fundamental"
    MODEL  = "Mult"
    _routes = [(0, 0), (0, 1), (0, 2), (3, 3), (3, 4), (3, 5)]


class SplitNode(PassThroughNode):
    """Fundamental Split: split one poly/control/audio input to mono outputs."""
    PLUGIN = "Fundamental"
    MODEL  = "Split"
    _routes = [(0, 0), (0, 1), (0, 2), (0, 3)]


class FundamentalADSRNode(ControllerNode):
    PLUGIN = "Fundamental"
    MODEL  = "ADSR"
    _required_cv  = {4: GATE}                   # GATE input must be connected
    _output_types = {0: CV}                      # ENV output is CV


class FundamentalLFONode(ControllerNode):
    PLUGIN = "Fundamental"
    MODEL  = "LFO"
    _output_types = {0: CV, 1: CV, 2: CV, 3: CV}  # SIN, TRI, SAW, SQR


class SEQ3Node(ControllerNode):
    PLUGIN = "Fundamental"
    MODEL  = "SEQ3"
    _required_cv  = {1: CLOCK}                  # CLOCK input must be connected
    _output_types = {0: GATE, 1: CV, 2: CV, 3: CV}  # TRIG, CV1, CV2, CV3


# ---------------------------------------------------------------------------
# Valley
# ---------------------------------------------------------------------------

class PlateauNode(AudioProcessorNode):
    PLUGIN = "Valley"
    MODEL  = "Plateau"
    # IN_L (0), IN_R (1) -> OUT_L (0), OUT_R (1)
    _routes = [(0, 0), (0, 1), (1, 0), (1, 1)]


# ---------------------------------------------------------------------------
# Bogaudio
# ---------------------------------------------------------------------------

class BogaudioADSRNode(ControllerNode):
    PLUGIN = "Bogaudio"
    MODEL  = "Bogaudio-ADSR"
    _required_cv  = {0: GATE}                   # GATE input must be connected
    _output_types = {0: CV}                      # ENV output is CV


class BogaudioDADSRHNode(ControllerNode):
    PLUGIN = "Bogaudio"
    MODEL  = "Bogaudio-DADSRH"
    _required_cv  = {0: GATE}
    _output_types = {0: CV}


class BogaudioLFONode(ControllerNode):
    PLUGIN = "Bogaudio"
    MODEL  = "Bogaudio-LFO"
    # outputs: RAMP_UP=0, RAMP_DOWN=1, SQUARE=2, TRIANGLE=3, SINE=4, STEPPED=5
    _output_types = {0: CV, 1: CV, 2: CV, 3: CV, 4: CV, 5: CV}


class BogaudioSampleHoldNode(ControllerNode):
    PLUGIN = "Bogaudio"
    MODEL  = "Bogaudio-SampleHold"
    _required_cv  = {0: CLOCK}                  # CLOCK1/GATE1 input
    _output_types = {0: CV, 1: CV}


class BogaudioAddrSeqNode(ControllerNode):
    PLUGIN = "Bogaudio"
    MODEL  = "Bogaudio-AddrSeq"
    _required_cv  = {0: CLOCK}              # CLOCK input must be connected
    _output_types = {0: CV}                 # OUT is a CV pitch/value output


class BogaudioRGateNode(ControllerNode):
    PLUGIN = "Bogaudio"
    MODEL  = "Bogaudio-RGate"
    _output_types = {0: GATE, 1: GATE, 2: GATE, 3: GATE}


class BogaudioPgmrNode(ControllerNode):
    """Bogaudio PGMR: 4-step programmer with 4 CV channels (A-D).
    Extendable via PgmrX expanders (4 steps each).
    Inputs: Clock(0), Select CV(1), Select 1-4 triggers(2-5).
    Outputs: Seq A-D(0-3), Step change trigger(4), Select 1-4(5-8)."""
    PLUGIN = "Bogaudio"
    MODEL  = "Bogaudio-Pgmr"
    _required_cv  = {0: CLOCK}
    _output_types = {0: CV, 1: CV, 2: CV, 3: CV, 4: GATE}


class PressurNode(AudioProcessorNode):
    PLUGIN = "Bogaudio"
    MODEL  = "Bogaudio-Pressor"
    # IN_L=0, IN_R=4 -> OUT_L=1, OUT_R=2
    _routes = [(0, 1), (0, 2), (4, 1), (4, 2)]


class BogaudioMix2Node(AudioMixerNode):
    """Bogaudio MIX2 -- 2-channel stereo fader (no per-channel panning CV).

    Input port layout per channel (2 ports each, no PAN CV):
        CH1: 0=LEVEL_CV  1=IN
        CH2: 2=LEVEL_CV  3=IN
    Output ports:
        0=OUT_L  1=OUT_R
    """
    PLUGIN = "Bogaudio"
    MODEL  = "Bogaudio-Mix2"
    _audio_inputs  = frozenset({1, 3})        # IN for CH1, CH2
    _audio_outputs = frozenset({0, 1})        # OUT_L, OUT_R


class BogaudioMix4Node(AudioMixerNode):
    """Bogaudio MIX4 -- 4-channel mixer with level CV and panning CV per channel.

    Input port layout per channel (3 ports each):
        CH1:  0=LEVEL_CV   1=PAN_CV   2=IN
        CH2:  3=LEVEL_CV   4=PAN_CV   5=IN
        CH3:  6=LEVEL_CV   7=PAN_CV   8=IN
        CH4:  9=LEVEL_CV  10=PAN_CV  11=IN

    Audio always enters the IN port (rightmost of the three per channel).
    LEVEL_CV and PAN_CV are optional modulation inputs -- leave unpatched
    for static level/pan set by the fader and pan knobs.

    Output ports:
        0=OUT_L  1=OUT_R
    """
    PLUGIN = "Bogaudio"
    MODEL  = "Bogaudio-Mix4"
    _audio_inputs  = frozenset({2, 5, 8, 11})   # IN for CH1-CH4
    _audio_outputs = frozenset({0, 1})           # OUT_L, OUT_R


class BogaudioMix8Node(AudioMixerNode):
    """Bogaudio MIX8 -- 8-channel mixer, same 3-port-per-channel layout as MIX4.

    Input port layout per channel (3 ports each):
        CH1:  0=LEVEL_CV   1=PAN_CV   2=IN
        CH2:  3=LEVEL_CV   4=PAN_CV   5=IN
        CH3:  6=LEVEL_CV   7=PAN_CV   8=IN
        CH4:  9=LEVEL_CV  10=PAN_CV  11=IN
        CH5: 12=LEVEL_CV  13=PAN_CV  14=IN
        CH6: 15=LEVEL_CV  16=PAN_CV  17=IN
        CH7: 18=LEVEL_CV  19=PAN_CV  20=IN
        CH8: 21=LEVEL_CV  22=PAN_CV  23=IN

    Output ports:
        0=OUT_L  1=OUT_R
    """
    PLUGIN = "Bogaudio"
    MODEL  = "Bogaudio-Mix8"
    _audio_inputs  = frozenset({2, 5, 8, 11, 14, 17, 20, 23})  # IN for CH1-CH8
    _audio_outputs = frozenset({0, 1})                          # OUT_L, OUT_R


# ---------------------------------------------------------------------------
# AlrightDevices
# ---------------------------------------------------------------------------

class Chronoblob2Node(AudioProcessorNode):
    PLUGIN = "AlrightDevices"
    MODEL  = "Chronoblob2"
    # IN_L=5, IN_R=6 -> OUT_L=0, OUT_R=1
    _routes = [(5, 0), (5, 1), (6, 0), (6, 1)]


# ---------------------------------------------------------------------------
# Befaco
# ---------------------------------------------------------------------------

class EvenVCONode(AudioSourceNode):
    PLUGIN = "Befaco"
    MODEL  = "EvenVCO"
    _audio_outputs = frozenset({0, 1, 2, 3, 4})  # TRI, SINE, SAW, PULSE, EVEN


class KickallNode(AudioSourceNode):
    PLUGIN = "Befaco"
    MODEL  = "Kickall"
    _audio_outputs = frozenset({0})
    _required_cv   = {0: GATE}                   # GATE input triggers the kick


class BefacoMixerNode(AudioMixerNode):
    PLUGIN = "Befaco"
    MODEL  = "Mixer"
    _audio_inputs  = frozenset({0, 3, 6, 9})
    _audio_outputs = frozenset({0, 1})


# ---------------------------------------------------------------------------
# ImpromptuModular
# ---------------------------------------------------------------------------

class ClockedNode(ControllerNode):
    PLUGIN = "ImpromptuModular"
    MODEL  = "Clocked-Clkd"
    _output_types = {
        0: CLOCK,   # CLK0 / master
        1: CLOCK,   # CLK1
        2: CLOCK,   # CLK2
        3: CLOCK,   # CLK3
        4: GATE,    # RESET
        5: GATE,    # RUN
        6: CV,      # BPM
    }


# ---------------------------------------------------------------------------
# AudibleInstruments
# ---------------------------------------------------------------------------

class PlaitsNode(AudioSourceNode):
    PLUGIN = "AudibleInstruments"
    MODEL  = "Plaits"
    _audio_outputs = frozenset({0, 1})           # OUT, AUX


class RingsNode(AudioSourceNode):
    """Mutable Instruments Rings (Resonator).

    Physically modeled resonator. Generates audio from pitch/strum inputs.
    ODD (port 0) is the main output; EVEN (port 1) is the auxiliary.
    """
    PLUGIN = "AudibleInstruments"
    MODEL  = "Rings"
    _audio_outputs = frozenset({0, 1})           # ODD=0, EVEN=1


class CloudsNode(AudioProcessorNode):
    """Mutable Instruments Clouds (Texture Synthesizer).

    Granular processor. Audio enters on IN_L (port 6) and IN_R (port 7).
    Stereo output on OUT_L (port 0) and OUT_R (port 1).
    """
    PLUGIN = "AudibleInstruments"
    MODEL  = "Clouds"
    _routes = [(6, 0), (7, 1)]                   # IN_L->OUT_L, IN_R->OUT_R


class MarblesNode(ControllerNode):
    """Mutable Instruments Marbles (Random Sampler).

    Generates random gates (T1/T2/T3) and CV (X1/X2/X3/Y).
    Pure controller -- no audio outputs; never blocks audio proof.
    """
    PLUGIN = "AudibleInstruments"
    MODEL  = "Marbles"
    _output_types = {
        0: GATE, 1: GATE, 2: GATE,  # T1, T2, T3
        3: CV, 4: CV, 5: CV, 6: CV,  # Y, X1, X2, X3
    }


# ---------------------------------------------------------------------------
# DanTModules
# ---------------------------------------------------------------------------

class PurfenatorNode(ControllerNode):
    """DanTModules Purfenator -- decorative title/background panel.

    No audio or CV connections. Pure cosmetic module.
    """
    PLUGIN = "DanTModules"
    MODEL  = "Purfenator"


# ---------------------------------------------------------------------------
# mscHack
# ---------------------------------------------------------------------------

class MscHackMix934Node(AudioMixerNode):
    PLUGIN = "mscHack"
    MODEL  = "Mix_9_3_4"
    _audio_inputs  = frozenset(range(9))
    _audio_outputs = frozenset({0, 1, 2, 3})


# ---------------------------------------------------------------------------
# dbRackModules
# ---------------------------------------------------------------------------

class DrumKitNode(AudioSourceNode):
    PLUGIN = "dbRackModules"
    MODEL  = "DrumKit"
    _audio_outputs = frozenset({0, 1})


class DrumKitSequencerNode(ControllerNode):
    """DrumKit/Sequencer: 8-track step sequencer, 8 gate outputs (0-7)."""
    PLUGIN = "DrumKit"
    MODEL  = "Sequencer"
    _output_types = {i: GATE for i in range(8)}


class DBRackDrumsNode(AudioSourceNode):
    PLUGIN = "dbRackModules"
    MODEL  = "Drums"
    _audio_outputs = frozenset({0})


# ---------------------------------------------------------------------------
# VultModulesFree
# ---------------------------------------------------------------------------

class UtilSendNode(AudioProcessorNode):
    PLUGIN = "VultModulesFree"
    MODEL  = "UtilSend"
    _routes = [(0, 0)]


# ---------------------------------------------------------------------------
# ArhythmeticUnits / monitoring
# ---------------------------------------------------------------------------

class SpectrumAnalyzerNode(ControllerNode):
    """Visual spectrum analyzer -- reads audio for display, does not pass it."""
    PLUGIN = "ArhythmeticUnits-Fourier"
    MODEL  = "SpectrumAnalyzer"


# ---------------------------------------------------------------------------
# JW-Modules
# ---------------------------------------------------------------------------

class NoteSeq16Node(ControllerNode):
    """16-step grid sequencer. Rows=pitches, columns=steps.
    Polyphonic V/OCT and GATE outputs. Empty column = gate low = rest."""
    PLUGIN = "JW-Modules"
    MODEL  = "NoteSeq16"
    _required_cv  = {0: CLOCK}
    _output_types = {0: CV, 1: GATE, 2: GATE}


# ---------------------------------------------------------------------------
# SlimeChild-Substation
# ---------------------------------------------------------------------------

class SubstationClockNode(ControllerNode):
    """Clock with BASE (master) and MULT (multiplied) outputs.

    Tempo param = log2(BPM/60).  Default=1 -> 120 BPM.
    MULT param multiplies BASE rate by an integer 1-16.
    Use MULT output with MULT param=4 for 16th notes from a 4/4 beat.
    """
    PLUGIN = "SlimeChild-Substation"
    MODEL  = "SlimeChild-Substation-Clock"
    _output_types = {0: CLOCK, 1: CLOCK}  # BASE, MULT


class SubstationEnvelopesNode(ControllerNode):
    """Dual semi-interruptable AD envelopes.  Both need a gate/trigger."""
    PLUGIN = "SlimeChild-Substation"
    MODEL  = "SlimeChild-Substation-Envelopes"
    _required_cv  = {0: GATE}               # TRIG1 must be connected
    _output_types = {0: CV, 1: CV}          # ENV1, ENV2


class SubstationFilterNode(AudioProcessorNode):
    """Physically-modelled 24dB/oct ladder lowpass.  IN(2) -> OUT(0)."""
    PLUGIN = "SlimeChild-Substation"
    MODEL  = "SlimeChild-Substation-Filter"
    _routes = [(2, 0)]   # IN -> OUT
    _port_attenuators = {1: 2}  # FM input -> FM Amount param


class SubstationVCANode(AudioProcessorNode):
    """Simple VCA.  IN(1) -> OUT(0).  CV(0) required to open."""
    PLUGIN = "SlimeChild-Substation"
    MODEL  = "SlimeChild-Substation-VCA"
    _routes    = [(1, 0)]
    _required_cv = {0: CV}  # CV must be connected (Level param defaults to 1 so audio passes without CV, but flag it)


class SubstationMixerNode(AudioMixerNode):
    """3-channel saturating mixer with chain I/O.

    Audio inputs: IN1(0), IN2(1), IN3(2).
    Outputs: CHAIN(0), OUT(1).
    """
    PLUGIN = "SlimeChild-Substation"
    MODEL  = "SlimeChild-Substation-Mixer"
    _audio_inputs  = frozenset({0, 1, 2})   # IN1, IN2, IN3
    _audio_outputs = frozenset({0, 1})      # CHAIN, OUT


class SubstationQuantizerNode(ControllerNode):
    """Quantizer -- maps free CV to scale degrees."""
    PLUGIN = "SlimeChild-Substation"
    MODEL  = "SlimeChild-Substation-Quantizer"
    _output_types = {0: CV}


class SubstationSubOscillatorNode(AudioSourceNode):
    """Standalone oscillator with BASE + two sub-harmonic outputs.

    Outputs: BASE(0), SUB1(1), SUB2(2).
    SUB1/2 frequency = base_freq / SUBDIV1 / SUBDIV2 params.
    """
    PLUGIN = "SlimeChild-Substation"
    MODEL  = "SlimeChild-Substation-SubOscillator"
    _audio_outputs = frozenset({0, 1, 2})   # BASE, SUB1, SUB2


class SubstationPolySeqNode(ControllerNode):
    """3-sequence polyrhythm sequencer (A, B, C) with 4 rhythmic dividers.

    Outputs: TRIG1-4 (gates, 0-3), SEQ_A/B/C (CV, 4-6).
    """
    PLUGIN = "SlimeChild-Substation"
    MODEL  = "SlimeChild-Substation-PolySeq"
    _required_cv  = {0: CLOCK}
    _output_types = {
        0: GATE, 1: GATE, 2: GATE, 3: GATE,  # TRIG1-4
        4: CV,   5: CV,   6: CV,              # SEQ_A, SEQ_B, SEQ_C
    }


# ---------------------------------------------------------------------------
# CountModula
# ---------------------------------------------------------------------------

class CountModulaSequencer16Node(ControllerNode):
    """16-step CV + gate sequencer. Per-step CV values and per-step gate select.
    This is the 303/606-style module: pitch CV and gate pattern in one module.
    Outputs: CV(0), CVI(1), GATE(2), TRIG(3), END(4).
    """
    PLUGIN = "CountModula"
    MODEL  = "Sequencer16"
    _required_cv  = {0: CLOCK}
    _output_types = {0: GATE, 1: GATE, 2: CV, 3: CV, 4: GATE}


class CountModulaGateSequencer16Node(ControllerNode):
    """8-track × 16-step gate/trigger sequencer. No CV output.
    Use for gate patterns alongside a separate CV sequencer.
    Outputs: GATE1-8 (0-7), TRIG1-8 (8-15), END (16).
    """
    PLUGIN = "CountModula"
    MODEL  = "GateSequencer16"
    _required_cv  = {0: CLOCK}
    _output_types = {i: GATE for i in range(16)}


# ---------------------------------------------------------------------------
# AaronStatic
# ---------------------------------------------------------------------------

class ChordCVNode(ControllerNode):
    """Takes a 1V/oct root CV and outputs four chord-note CVs + one polyphonic CV."""
    PLUGIN = "AaronStatic"
    MODEL  = "ChordCV"
    _output_types = {0: CV, 1: CV, 2: CV, 3: CV, 4: CV}


# ---------------------------------------------------------------------------
# AgentRack
# ---------------------------------------------------------------------------

class AttenuateNode(AudioProcessorNode):
    """6-channel CV attenuator. OUT_n = IN_n x SCALE_n."""
    PLUGIN         = "AgentRack"
    MODEL          = "Attenuate"
    _audio_inputs  = frozenset({0, 1, 2, 3, 4, 5})
    _audio_outputs = frozenset({0, 1, 2, 3, 4, 5})
    _routes        = [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4), (5, 5)]


class AgentRackNoiseNode(AudioSourceNode):
    """Six spectral noise generators: WHITE/PINK/BROWN/BLUE/VIOLET/CRACKLE."""
    PLUGIN         = "AgentRack"
    MODEL          = "Noise"
    _audio_outputs = frozenset({0, 1, 2, 3, 4, 5})


class CrinkleNode(AudioSourceNode):
    """Buchla 259-inspired wavefolder oscillator. OUT is audio."""
    PLUGIN          = "AgentRack"
    MODEL           = "Crinkle"
    _audio_outputs  = frozenset({0})


class AgentRackADSRNode(ControllerNode):
    """ADSR envelope generator. ENV output drives VCA or filter CV."""
    PLUGIN        = "AgentRack"
    MODEL         = "ADSR"
    _required_cv  = {0: GATE}
    _output_types = {0: CV}


class InspectorNode(ControllerNode):
    """Passive observer -- no connections required."""
    PLUGIN = "AgentRack"
    MODEL  = "Inspector"


class LadderNode(AudioProcessorNode):
    """Huovilainen nonlinear ladder filter with SPREAD/SHAPE pole topology."""
    PLUGIN         = "AgentRack"
    MODEL          = "Ladder"
    _audio_inputs  = frozenset({0})   # IN
    _audio_outputs = frozenset({0})   # OUT
    _routes        = [(0, 0)]         # IN -> OUT


class SaphireNode(AudioProcessorNode):
    """Fixed-IR convolution reverb with TIME/BEND/TONE/PRE operator transformations."""
    PLUGIN         = "AgentRack"
    MODEL          = "Saphire"
    _audio_inputs  = frozenset({0, 1})   # IN_L, IN_R
    _audio_outputs = frozenset({0, 1})   # OUT_L, OUT_R
    _routes        = [(0, 0), (1, 1)]    # L->L, R->R


class SonicNode(AudioProcessorNode):
    """BBE-inspired spectral-phase maximizer: 3-band phase alignment + spectral tilt."""
    PLUGIN         = "AgentRack"
    MODEL          = "Sonic"
    _audio_inputs  = frozenset({0})   # IN
    _audio_outputs = frozenset({0})   # OUT
    _routes        = [(0, 0)]         # IN -> OUT


class VCMixerNode(AudioProcessorNode):
    """Fundamental VCMixer: 4-channel mixer, passes audio through."""
    PLUGIN         = "Fundamental"
    MODEL          = "VCMixer"
    _audio_inputs  = frozenset({1, 2, 3, 4})  # Channel 1-4
    _audio_outputs = frozenset({0})            # Mix
    _routes        = [(i, 0) for i in (1, 2, 3, 4)]


class SumNode(AudioProcessorNode):
    """Fundamental Sum: polyphonic sum to mono."""
    PLUGIN         = "Fundamental"
    MODEL          = "Sum"
    _audio_inputs  = frozenset({0})   # Polyphonic
    _audio_outputs = frozenset({0})   # Monophonic
    _routes        = [(0, 0)]


class BogaudioVCFNode(AudioProcessorNode):
    """Bogaudio VCF: LP/HP/BP/BR filter."""
    PLUGIN         = "Bogaudio"
    MODEL          = "Bogaudio-VCF"
    _audio_inputs  = frozenset({3})   # Signal (id 3)
    _audio_outputs = frozenset({0})   # Signal (id 0)
    _routes        = [(3, 0)]


class FundamentalRandomNode(ControllerNode):
    """Fundamental Random: smooth/stepped/linear random CV source."""
    PLUGIN = "Fundamental"
    MODEL  = "Random"


class QuantizerNode(ControllerNode):
    """Fundamental Quantizer: rounds V/oct to nearest semitone."""
    PLUGIN = "Fundamental"
    MODEL  = "Quantizer"


class CoffeeQuantNode(ControllerNode):
    """Coffee Quant: 12-tone quantizer with per-note enable params."""
    PLUGIN = "Coffee"
    MODEL  = "Quant"


class RandomValuesNode(ControllerNode):
    """Fundamental RandomValues: 7 random CV outputs, triggered."""
    PLUGIN = "Fundamental"
    MODEL  = "RandomValues"


class TonnetzNode(ControllerNode):
    """AgentRack Tonnetz: trigger-addressed chord generator.
    CV1-3 select triangles (stacked), TRIG commits chord.
    Output: polyphonic V/Oct chord (3-9 channels)."""
    PLUGIN = "AgentRack"
    MODEL  = "Tonnetz"
    _required_cv  = {3: GATE}                   # TRIG input must be connected
    _output_types = {0: CV}                     # CHORD poly V/Oct


class ClockDivNode(ControllerNode):
    """AgentRack ClockDiv: /2 /4 /8 /16 /32 clock divider."""
    PLUGIN = "AgentRack"
    MODEL  = "ClockDiv"
    _output_types = {0: GATE, 1: GATE, 2: GATE, 3: GATE, 4: GATE}


class SimpleClockNode(ControllerNode):
    """JW-Modules SimpleClock: clock with divided outputs.
    out0=Clock, out1=Reset, out2=/4, out3=/8, out4=/16, out5=/32"""
    PLUGIN = "JW-Modules"
    MODEL  = "SimpleClock"
    _output_types = {0: GATE, 1: GATE, 2: GATE, 3: GATE, 4: GATE, 5: GATE}


class BogaudioLVCFNode(AudioProcessorNode):
    """Bogaudio LVCF: LP/HP/BP/notch filter."""
    PLUGIN         = "Bogaudio"
    MODEL          = "Bogaudio-LVCF"
    _audio_inputs  = frozenset({0})
    _audio_outputs = frozenset({0})
    _routes        = [(0, 0)]


class BusCrushNode(AudioProcessorNode):
    """8-channel Mackie-style summing bus. Asymmetric rail clipping, 8x oversampled.
    Inputs 0-7: IN_0..IN_7 (audio). Inputs 8-15: PAN_0..PAN_7 (CV, unconnected=center).
    Outputs: OUT_L=0, OUT_R=1."""
    PLUGIN         = "AgentRack"
    MODEL          = "BusCrush"
    _audio_inputs  = frozenset({0, 1, 2, 3, 4, 5, 6, 7})   # IN_0..IN_7
    _audio_outputs = frozenset({0, 1})                       # OUT_L, OUT_R
    # Any connected input routes to both outputs (summing bus)
    _routes        = [(i, o) for i in range(8) for o in (0, 1)]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

NODE_REGISTRY: dict[str, type] = {
    f"{cls.PLUGIN}/{cls.MODEL}": cls
    for cls in [
        # Core
        AudioInterface2Node, AudioInterface8Node, Audio16Node, MidiMapNode,
        # Fundamental
        VCONode, VCFNode, VCANode, NoiseNode, MultNode, SplitNode,
        VCMixerNode, SumNode, FundamentalRandomNode,
        QuantizerNode, RandomValuesNode, CoffeeQuantNode,
        FundamentalADSRNode, FundamentalLFONode, SEQ3Node,
        # Valley
        PlateauNode,
        # Bogaudio
        BogaudioADSRNode, BogaudioDADSRHNode, BogaudioLFONode,
        BogaudioAddrSeqNode, BogaudioSampleHoldNode, BogaudioRGateNode, BogaudioPgmrNode,
        PressurNode, BogaudioMix2Node, BogaudioMix4Node, BogaudioMix8Node, BogaudioVCFNode, BogaudioLVCFNode,
        # AlrightDevices
        Chronoblob2Node,
        # Befaco
        EvenVCONode, KickallNode, BefacoMixerNode,
        # ImpromptuModular
        ClockedNode,
        # AudibleInstruments
        PlaitsNode, RingsNode, CloudsNode, MarblesNode,
        # DanTModules
        PurfenatorNode,
        # mscHack
        MscHackMix934Node,
        # dbRackModules
        DrumKitNode, DrumKitSequencerNode, DBRackDrumsNode,
        # VultModulesFree
        UtilSendNode,
        # ArhythmeticUnits
        SpectrumAnalyzerNode,
        # JW-Modules
        NoteSeq16Node, SimpleClockNode,
        # CountModula
        CountModulaSequencer16Node, CountModulaGateSequencer16Node,
        # AaronStatic
        ChordCVNode,
        # AgentRack
        AttenuateNode, AgentRackNoiseNode, CrinkleNode, AgentRackADSRNode, InspectorNode, LadderNode, SaphireNode, SonicNode, BusCrushNode, ClockDivNode, TonnetzNode,
        # SlimeChild-Substation
        SubstationClockNode, SubstationEnvelopesNode, SubstationFilterNode,
        SubstationVCANode, SubstationMixerNode, SubstationQuantizerNode,
        SubstationSubOscillatorNode, SubstationPolySeqNode,
    ]
}
