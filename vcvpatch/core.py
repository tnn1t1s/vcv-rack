"""
Core classes: Patch, Module, Port, Cable.
"""

import os
import json
import glob
import random
import re
import copy
from enum import Enum
from typing import Optional, Union

from .layout import Position


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

# Explicit metadata supplements for modules whose discovered cache is not
# committed locally but that are still part of the maintained authoring surface.
# These specs are exact and deterministic. They are not fuzzy aliases.
#
# Some entries below preserve older, intentional API spellings used by the
# maintained patch corpus. That is acceptable here because these are explicit
# API specs, not discovered-name heuristics.
_EXPLICIT_METADATA: dict[tuple[str, str], dict[str, list[dict]]] = {
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
    ("SlimeChild-Substation", "SlimeChild-Substation-Clock"): {
        "params": [
            {"id": 0, "name": "TEMPO"},
            {"id": 1, "name": "RUN"},
            {"id": 2, "name": "MULT"},
        ],
        "inputs": [
            {"id": 0, "name": "RUN"},
            {"id": 1, "name": "SYNC"},
        ],
        "outputs": [
            {"id": 0, "name": "BASE"},
            {"id": 1, "name": "MULT"},
        ],
    },
    ("SlimeChild-Substation", "SlimeChild-Substation-Envelopes"): {
        "params": [
            {"id": 0, "name": "EG1_ATTACK"},
            {"id": 1, "name": "EG1_DECAY"},
            {"id": 2, "name": "EG2_ATTACK"},
            {"id": 3, "name": "EG2_DECAY"},
            {"id": 4, "name": "HOLD"},
            {"id": 5, "name": "TRIGGER"},
        ],
        "inputs": [
            {"id": 0, "name": "TRIG1"},
            {"id": 1, "name": "TRIG2"},
        ],
        "outputs": [
            {"id": 0, "name": "ENV1"},
            {"id": 1, "name": "ENV2"},
        ],
    },
    ("SlimeChild-Substation", "SlimeChild-Substation-Filter"): {
        "params": [
            {"id": 0, "name": "FREQ"},
            {"id": 1, "name": "RES"},
            {"id": 2, "name": "FM"},
        ],
        "inputs": [
            {"id": 0, "name": "VOCT"},
            {"id": 1, "name": "FM"},
            {"id": 2, "name": "IN"},
        ],
        "outputs": [
            {"id": 0, "name": "OUT"},
        ],
    },
    ("SlimeChild-Substation", "SlimeChild-Substation-VCA"): {
        "params": [
            {"id": 0, "name": "LEVEL"},
        ],
        "inputs": [
            {"id": 0, "name": "CV"},
            {"id": 1, "name": "IN"},
        ],
        "outputs": [
            {"id": 0, "name": "OUT"},
        ],
    },
    ("SlimeChild-Substation", "SlimeChild-Substation-Mixer"): {
        "params": [
            {"id": 0, "name": "LEVEL1"},
            {"id": 1, "name": "LEVEL2"},
            {"id": 2, "name": "LEVEL3"},
            {"id": 3, "name": "MOD1"},
            {"id": 4, "name": "MOD2"},
            {"id": 5, "name": "MOD3"},
            {"id": 6, "name": "MIX_LEVEL"},
            {"id": 7, "name": "CHAIN_GAIN"},
            {"id": 8, "name": "DRIVE"},
        ],
        "inputs": [
            {"id": 0, "name": "IN1"},
            {"id": 1, "name": "IN2"},
            {"id": 2, "name": "IN3"},
            {"id": 3, "name": "CV1"},
            {"id": 4, "name": "CV2"},
            {"id": 5, "name": "CV3"},
            {"id": 6, "name": "CHAIN"},
            {"id": 7, "name": "LEVEL"},
        ],
        "outputs": [
            {"id": 0, "name": "CHAIN"},
            {"id": 1, "name": "OUT"},
        ],
    },
    ("SlimeChild-Substation", "SlimeChild-Substation-Quantizer"): {
        "params": [
            {"id": 0, "name": "TEMPERAMENT"},
            {"id": 1, "name": "SCALE"},
            {"id": 2, "name": "ROOT"},
            {"id": 3, "name": "OCTAVE"},
            {"id": 4, "name": "TRANSPOSE"},
        ],
        "inputs": [
            {"id": 0, "name": "ROOT"},
            {"id": 1, "name": "OCT"},
            {"id": 2, "name": "IN"},
        ],
        "outputs": [
            {"id": 0, "name": "OUT"},
        ],
    },
    ("SlimeChild-Substation", "SlimeChild-Substation-SubOscillator"): {
        "params": [
            {"id": 0, "name": "BASE_FREQ"},
            {"id": 1, "name": "WAVEFORM"},
            {"id": 2, "name": "SUBDIV1"},
            {"id": 3, "name": "SUBDIV2"},
            {"id": 4, "name": "PWM"},
            {"id": 5, "name": "DETUNE"},
        ],
        "inputs": [
            {"id": 0, "name": "VOCT"},
            {"id": 1, "name": "SUB1"},
            {"id": 2, "name": "SUB2"},
            {"id": 3, "name": "PWM"},
        ],
        "outputs": [
            {"id": 0, "name": "BASE"},
            {"id": 1, "name": "SUB1"},
            {"id": 2, "name": "SUB2"},
        ],
    },
    ("SlimeChild-Substation", "SlimeChild-Substation-PolySeq"): {
        "params": [
            {"id": 0, "name": "A1"}, {"id": 1, "name": "A2"}, {"id": 2, "name": "A3"}, {"id": 3, "name": "A4"},
            {"id": 4, "name": "B1"}, {"id": 5, "name": "B2"}, {"id": 6, "name": "B3"}, {"id": 7, "name": "B4"},
            {"id": 8, "name": "C1"}, {"id": 9, "name": "C2"}, {"id": 10, "name": "C3"}, {"id": 11, "name": "C4"},
            {"id": 12, "name": "DIV1"}, {"id": 13, "name": "DIV2"}, {"id": 14, "name": "DIV3"}, {"id": 15, "name": "DIV4"},
            {"id": 16, "name": "DIV1_A"}, {"id": 17, "name": "DIV2_A"}, {"id": 18, "name": "DIV3_A"}, {"id": 19, "name": "DIV4_A"},
            {"id": 20, "name": "DIV1_B"}, {"id": 21, "name": "DIV2_B"}, {"id": 22, "name": "DIV3_B"}, {"id": 23, "name": "DIV4_B"},
            {"id": 24, "name": "DIV1_C"}, {"id": 25, "name": "DIV2_C"}, {"id": 26, "name": "DIV3_C"}, {"id": 27, "name": "DIV4_C"},
            {"id": 28, "name": "RANGE_A"}, {"id": 29, "name": "RANGE_B"}, {"id": 30, "name": "RANGE_C"},
            {"id": 31, "name": "SUM_MODE"},
            {"id": 32, "name": "RESET"},
            {"id": 33, "name": "NEXT"},
            {"id": 34, "name": "STEPS"},
        ],
        "inputs": [
            {"id": 0, "name": "CLOCK"},
            {"id": 1, "name": "RESET"},
            {"id": 2, "name": "DIV1"},
            {"id": 3, "name": "DIV2"},
            {"id": 4, "name": "DIV3"},
            {"id": 5, "name": "DIV4"},
        ],
        "outputs": [
            {"id": 0, "name": "TRIG1"},
            {"id": 1, "name": "TRIG2"},
            {"id": 2, "name": "TRIG3"},
            {"id": 3, "name": "TRIG4"},
            {"id": 4, "name": "SEQ_A"},
            {"id": 5, "name": "SEQ_B"},
            {"id": 6, "name": "SEQ_C"},
        ],
    },
    ("AaronStatic", "ChordCV"): {
        "params": [
            {"id": 0, "name": "Root Note"},
            {"id": 1, "name": "Chord Type"},
            {"id": 2, "name": "Inversion"},
            {"id": 3, "name": "Voicing"},
        ],
        "inputs": [
            {"id": 0, "name": "ROOT"},
            {"id": 1, "name": "TYPE"},
            {"id": 2, "name": "INVERSION"},
            {"id": 3, "name": "VOICING"},
        ],
        "outputs": [
            {"id": 0, "name": "NOTE1"},
            {"id": 1, "name": "NOTE2"},
            {"id": 2, "name": "NOTE3"},
            {"id": 3, "name": "NOTE4"},
            {"id": 4, "name": "Polyphonic"},
        ],
    },
    ("CountModula", "Sequencer16"): {
        "params": (
            [{"id": 16 + i, "name": f"STEP{i+1}"} for i in range(16)] +
            [{"id": 37 + i, "name": f"TRIG{i+1}"} for i in range(16)] +
            [{"id": 53 + i, "name": f"GATE{i+1}"} for i in range(16)] +
            [
                {"id": 32, "name": "LENGTH"},
                {"id": 35, "name": "RANGE_SW"},
            ]
        ),
        "inputs": [
            {"id": 0, "name": "RUN"},
            {"id": 1, "name": "CLOCK"},
            {"id": 2, "name": "RESET"},
            {"id": 3, "name": "LENGTH_INPUT"},
            {"id": 4, "name": "DIRECTION_INPUT"},
            {"id": 5, "name": "ADDRESS_INPUT"},
        ],
        "outputs": [
            {"id": 0, "name": "GATE"},
            {"id": 1, "name": "TRIG"},
            {"id": 2, "name": "END"},
            {"id": 3, "name": "CV"},
            {"id": 4, "name": "CVI"},
        ],
    },
    ("Bogaudio", "Bogaudio-Pgmr"): {
        "inputs": [
            {"id": 0, "name": "Clock"},
        ],
        "outputs": [
            {"id": 0, "name": "Channel_A"},
            {"id": 1, "name": "Channel_B"},
            {"id": 2, "name": "Channel_C"},
            {"id": 3, "name": "Channel_D"},
            {"id": 4, "name": "Step_trigger"},
        ],
    },
    ("Bogaudio", "Bogaudio-PgmrX"): {
        "inputs": [],
        "outputs": [],
    },
    ("AlrightDevices", "Chronoblob2"): {
        "params": [
            {"id": 0, "name": "Feedback"},
            {"id": 1, "name": "Delay Time"},
            {"id": 2, "name": "Dry/Wet"},
            {"id": 8, "name": "Time Modulation Mode"},
            {"id": 9, "name": "Delay Mode"},
        ],
        "inputs": [
            {"id": 0, "name": "L_Delay_Time_CV"},
            {"id": 1, "name": "Feedback_CV"},
            {"id": 2, "name": "Mix_CV"},
            {"id": 5, "name": "Left"},
            {"id": 6, "name": "Right_Return"},
            {"id": 7, "name": "Sync_Trigger"},
        ],
        "outputs": [
            {"id": 0, "name": "Left"},
            {"id": 1, "name": "Right_Send"},
        ],
    },
    ("JW-Modules", "SimpleClock"): {
        "params": [
            {"id": 0, "name": "BPM"},
            {"id": 1, "name": "Run"},
            {"id": 2, "name": "Random Reset Probability"},
        ],
        "inputs": [],
        "outputs": [
            {"id": 0, "name": "Clock"},
            {"id": 1, "name": "Reset"},
            {"id": 2, "name": "_4"},
            {"id": 5, "name": "_32"},
        ],
    },
    ("Fundamental", "Random"): {
        "params": [
            {"id": 0, "name": "Internal trigger rate"},
        ],
        "inputs": [],
        "outputs": [
            {"id": 6, "name": "Smooth"},
        ],
    },
    ("Fundamental", "RandomValues"): {
        "params": [],
        "inputs": [
            {"id": 0, "name": "Trigger"},
        ],
        "outputs": [
            {"id": 1, "name": "Random_2"},
            {"id": 6, "name": "Random_7"},
        ],
    },
    ("Fundamental", "VCMixer"): {
        "params": [],
        "inputs": [
            {"id": 1, "name": "Channel_1"},
            {"id": 2, "name": "Channel_2"},
            {"id": 3, "name": "Channel_3"},
            {"id": 4, "name": "Channel_4"},
        ],
        "outputs": [
            {"id": 0, "name": "Mix"},
        ],
    },
    ("Fundamental", "Sum"): {
        "params": [],
        "inputs": [
            {"id": 0, "name": "Polyphonic"},
        ],
        "outputs": [
            {"id": 0, "name": "Monophonic"},
        ],
    },
    ("Bogaudio", "Bogaudio-ADSR"): {
        "params": [
            {"id": 0, "name": "Attack"},
            {"id": 1, "name": "Decay"},
            {"id": 2, "name": "Sustain"},
            {"id": 3, "name": "Release"},
            {"id": 4, "name": "Linear"},
        ],
        "inputs": [
            {"id": 0, "name": "Gate"},
        ],
        "outputs": [
            {"id": 0, "name": "Envelope"},
        ],
    },
    ("Bogaudio", "Bogaudio-LFO"): {
        "params": [
            {"id": 0, "name": "FREQ"},
            {"id": 1, "name": "SLOW"},
            {"id": 2, "name": "SAMPLE"},
            {"id": 3, "name": "PW"},
            {"id": 4, "name": "OFFSET"},
            {"id": 5, "name": "SCALE"},
            {"id": 6, "name": "SMOOTH"},
        ],
        "inputs": [
            {"id": 0, "name": "SAMPLE"},
            {"id": 1, "name": "PW"},
            {"id": 2, "name": "OFFSET"},
            {"id": 3, "name": "SCALE"},
            {"id": 4, "name": "VOCT"},
            {"id": 5, "name": "RESET"},
        ],
        "outputs": [
            {"id": 0, "name": "SAW"},
            {"id": 1, "name": "RAMP_DOWN"},
            {"id": 2, "name": "SQR"},
            {"id": 3, "name": "TRI"},
            {"id": 4, "name": "SIN"},
            {"id": 5, "name": "STEPPED"},
        ],
    },
    ("Bogaudio", "Bogaudio-Pressor"): {
        "params": [
            {"id": 0, "name": "Threshold"},
            {"id": 1, "name": "Ratio"},
            {"id": 2, "name": "Attack"},
            {"id": 3, "name": "Release"},
            {"id": 4, "name": "Output gain"},
        ],
        "inputs": [
            {"id": 0, "name": "Left_signal"},
            {"id": 4, "name": "Right_signal"},
        ],
        "outputs": [
            {"id": 1, "name": "Left_signal"},
            {"id": 2, "name": "Right_signal"},
        ],
    },
    ("Bogaudio", "Bogaudio-DADSRH"): {
        "params": [
            {"id": 0, "name": "Delay"},
            {"id": 1, "name": "Attack"},
            {"id": 2, "name": "Decay"},
            {"id": 3, "name": "Sustain"},
            {"id": 4, "name": "Release"},
            {"id": 5, "name": "Hold"},
            {"id": 6, "name": "Attack shape"},
            {"id": 7, "name": "Decay shape"},
            {"id": 8, "name": "Release shape"},
            {"id": 11, "name": "Loop"},
            {"id": 12, "name": "Speed"},
            {"id": 13, "name": "Retrigger"},
        ],
        "inputs": [
            {"id": 0, "name": "Trigger"},
        ],
        "outputs": [
            {"id": 1, "name": "Inverted_envelope"},
        ],
    },
    ("Bogaudio", "Bogaudio-LVCF"): {
        "params": [
            {"id": 0, "name": "Center/cutoff frequency"},
            {"id": 1, "name": "Frequency CV attenuation"},
            {"id": 2, "name": "Resonance / bandwidth"},
        ],
        "inputs": [
            {"id": 0, "name": "Cutoff_CV"},
            {"id": 3, "name": "Signal"},
        ],
        "outputs": [
            {"id": 0, "name": "Signal"},
        ],
    },
    ("Bogaudio", "Bogaudio-VCF"): {
        "params": [
            {"id": 0, "name": "Center/cutoff frequency"},
            {"id": 1, "name": "Frequency CV attenuation"},
            {"id": 2, "name": "Resonance / bandwidth"},
            {"id": 3, "name": "Mode"},
        ],
        "inputs": [
            {"id": 0, "name": "Cutoff_CV"},
            {"id": 3, "name": "Signal"},
        ],
        "outputs": [
            {"id": 0, "name": "Signal"},
        ],
    },
    ("AudibleInstruments", "Plaits"): {
        "params": [
            {"id": 0, "name": "MODEL"},
            {"id": 2, "name": "FREQ"},
            {"id": 3, "name": "HARMONICS"},
            {"id": 4, "name": "TIMBRE"},
            {"id": 5, "name": "MORPH"},
            {"id": 8, "name": "MORPH_ATTENUVERTER"},
            {"id": 9, "name": "LPG_COLOUR"},
            {"id": 10, "name": "DECAY"},
        ],
        "inputs": [
            {"id": 0, "name": "Pitch_1V_oct_"},
            {"id": 2, "name": "Timbre"},
            {"id": 3, "name": "MORPH"},
            {"id": 5, "name": "TRIGGER"},
        ],
        "outputs": [
            {"id": 0, "name": "OUT"},
            {"id": 1, "name": "AUX"},
            {"id": 0, "name": "Main"},
        ],
    },
    ("Befaco", "Kickall"): {
        "params": [
            {"id": 0, "name": "Tune"},
            {"id": 2, "name": "Wave shape"},
            {"id": 3, "name": "VCA Envelope decay time"},
        ],
        "inputs": [
            {"id": 0, "name": "Trigger"},
            {"id": 2, "name": "Tune_V_Oct_"},
        ],
        "outputs": [
            {"id": 0, "name": "Kick"},
        ],
    },
    ("dbRackModules", "Drums"): {
        "params": [
            {"id": 0, "name": "Type"},
            {"id": 1, "name": "Sample selection"},
            {"id": 2, "name": "Pitch"},
            {"id": 3, "name": "Decay"},
        ],
        "inputs": [
            {"id": 0, "name": "Trig"},
        ],
        "outputs": [
            {"id": 0, "name": "CV"},
        ],
    },
    ("mscHack", "Mix_9_3_4"): {
        "params": [
            {"id": 0, "name": "Main Level"},
            {"id": 1, "name": "Ch1. Level"},
            {"id": 2, "name": "Ch2. Level"},
            {"id": 3, "name": "Ch3. Level"},
            {"id": 4, "name": "Ch4. Level"},
            {"id": 5, "name": "Ch5. Level"},
            {"id": 6, "name": "Ch6. Level"},
            {"id": 7, "name": "Ch7. Level"},
            {"id": 13, "name": "AUX1. Level"},
            {"id": 14, "name": "AUX2. Level"},
            {"id": 85, "name": "Ch2. AUX 1 Level"},
            {"id": 86, "name": "Ch2. AUX 2 Level"},
            {"id": 90, "name": "Ch3. AUX 2 Level"},
            {"id": 94, "name": "Ch4. AUX 2 Level"},
            {"id": 106, "name": "Ch7. AUX 2 Level"},
        ],
        "inputs": [
            {"id": 2, "name": "Ch1_Left"},
            {"id": 4, "name": "Ch2_Left"},
            {"id": 6, "name": "Ch3_Left"},
            {"id": 8, "name": "Ch4_Left"},
            {"id": 10, "name": "Ch5_Left"},
            {"id": 12, "name": "Ch6_Left"},
            {"id": 14, "name": "Ch7_Left"},
            {"id": 11, "name": "Ch5_Level_CV"},
            {"id": 13, "name": "Ch6_Level_CV"},
            {"id": 24, "name": "AUX1_Left"},
            {"id": 28, "name": "AUX1_Right"},
            {"id": 25, "name": "AUX2_Left"},
            {"id": 29, "name": "AUX2_Right"},
        ],
        "outputs": [
            {"id": 0, "name": "Main_Left"},
            {"id": 1, "name": "Main_Right"},
            {"id": 10, "name": "Aux_1_Left"},
            {"id": 14, "name": "Aux_1_Right"},
            {"id": 9, "name": "Aux_2_Left"},
            {"id": 13, "name": "Aux_2_Right"},
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
    supplement = _EXPLICIT_METADATA.get((plugin, model))
    if not files:
        if supplement is None:
            return None
        data = copy.deepcopy(supplement)
        _add_api_names(data)
        return data

    # Sort by filename (semver sorts lexicographically for most common versions)
    latest = sorted(files)[-1]
    with open(latest) as fh:
        data = json.load(fh)

    if supplement is not None:
        for bucket in ("params", "inputs", "outputs"):
            if not data.get(bucket):
                data[bucket] = copy.deepcopy(supplement.get(bucket, []))
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
    def __init__(self, zoom: float = 1.0):
        self.modules: list[Module] = []
        self.cables: list[Cable] = []
        self.zoom = zoom

    # -- Module placement ----------------------------------------------------

    def add(self, plugin: str, model: str,
            pos,
            color: Optional[str] = None,
            extra_data: Optional[dict] = None,
            **params) -> Module:
        """
        Add a module to the patch.

        params are keyword args matching the module's canonical API param names.
        E.g.: patch.add("Fundamental", "VCF", Cutoff_frequency=0.5, Resonance=0.3)

        pos is required. Pass either:
          - [hp, row]
          - (hp, row)
          - vcvpatch.layout.Position
        """
        pos = _normalize_pos(pos)

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


def _normalize_pos(pos) -> list[int]:
    """Normalize an explicit position value into [hp, row]."""
    if pos is None:
        raise ValueError(
            "pos is required. Pass an explicit position such as [0, 0] or "
            "RackLayout().row(0).at(0)."
        )
    if isinstance(pos, Position):
        return pos.as_list()
    if isinstance(pos, (list, tuple)) and len(pos) == 2:
        return [int(pos[0]), int(pos[1])]
    raise TypeError(
        f"Invalid pos={pos!r}. Expected [hp, row], (hp, row), or vcvpatch.layout.Position."
    )
