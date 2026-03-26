"""
Module registry: maps plugin/model -> named ports and params with their integer IDs.
IDs come directly from the C++ enum order in each module's source.
"""

# Each entry: { 'params': {name: id}, 'inputs': {name: id}, 'outputs': {name: id} }
# Aliases listed so you can use short names (e.g. 'IN', 'OUT', 'CV') or full names.

MODULES = {}


def _reg(plugin, model, params=None, inputs=None, outputs=None):
    MODULES[f"{plugin}/{model}"] = {
        "plugin": plugin,
        "model": model,
        "params": params or {},
        "inputs": inputs or {},
        "outputs": outputs or {},
    }


# ---------------------------------------------------------------------------
# Core (always installed)
# ---------------------------------------------------------------------------

_reg("Core", "MidiMap",
     params={},
     inputs={},
     outputs={})

_reg("Core", "MIDIToCVInterface",
     params={},
     inputs={},
     outputs={
         "PITCH": 0, "VOCT": 0,
         "GATE": 1,
         "VELOCITY": 2, "VEL": 2,
         "AFTERTOUCH": 3, "AT": 3,
         "PW": 4,
         "MOD": 5,
         "RETRIGGER": 6, "RETRIG": 6,
         "CLOCK": 7,
         "CLOCK_DIV": 8,
         "START": 9,
         "STOP": 10,
         "CONTINUE": 11,
     })

_reg("Core", "AudioInterface2",
     params={"VOLUME": 0},
     inputs={
         "IN_L": 0, "IN1": 0, "L": 0,
         "IN_R": 1, "IN2": 1, "R": 1,
     },
     outputs={
         "OUT_L": 0, "OUT1": 0,
         "OUT_R": 1, "OUT2": 1,
     })

# ---------------------------------------------------------------------------
# Fundamental
# ---------------------------------------------------------------------------

_reg("Fundamental", "VCO",
     # Params from C++ enum (some slots removed but still occupy IDs for back-compat):
     #   MODE_PARAM=0 (removed), SYNC_PARAM=1, FREQ_PARAM=2, FINE_PARAM=3 (removed),
     #   FM_PARAM=4, PW_PARAM=5, PW_CV_PARAM=6, LINEAR_PARAM=7
     params={
         "SYNC":   1,   # hard/soft sync toggle
         "FREQ":   2,   # coarse tune
         "FM":     4,   # FM CV attenuator (-1..1, default 0)
         "PW":     5,   # pulse width (0..1, default 0.5 = square)
         "PWM":    6,   # PWM CV attenuator (-1..1, default 0)
         "LINEAR": 7,   # FM mode: 0=1V/oct, 1=linear
     },
     inputs={
         "PITCH": 0, "VOCT": 0, "V_OCT": 0,
         "FM": 1,
         "SYNC": 2,
         "PW": 3, "PWM": 3,
     },
     outputs={
         "SIN": 0, "SINE": 0,
         "TRI": 1, "TRIANGLE": 1,
         "SAW": 2,
         "SQR": 3, "SQUARE": 3,
     })

_reg("Fundamental", "VCF",
     params={
         "FREQ":    0,   # Cutoff frequency (default 0.5)
         "FINE":    1,   # (unnamed, default 0)
         "RES":     2,   # Resonance (default 0)
         "FREQ_CV": 3,   # Cutoff frequency CV attenuator (-1..1, default 0)
         "DRIVE":   4,   # Drive (default 0)
         "RES_CV":  5,   # Resonance CV attenuator (default 0)
         "DRIVE_CV":6,   # Drive CV attenuator (default 0)
     },
     inputs={
         "FREQ": 0, "CUTOFF": 0,
         "RES": 1,
         "DRIVE": 2,
         "IN": 3, "AUDIO": 3,
     },
     outputs={
         "LPF": 0, "LP": 0,
         "HPF": 1, "HP": 1,
     })

_reg("Fundamental", "VCA",
     params={
         "LEVEL1": 0,
         "LEVEL2": 1,
     },
     inputs={
         "EXP1": 0,
         "LIN1": 1, "CV": 1, "CV1": 1,
         "IN1": 2, "IN": 2, "AUDIO": 2,
         "EXP2": 3,
         "LIN2": 4, "CV2": 4,
         "IN2": 5,
     },
     outputs={
         "OUT1": 0, "OUT": 0,
         "OUT2": 1,
     })

_reg("Fundamental", "ADSR",
     params={
         "ATTACK": 0, "A": 0,
         "DECAY": 1, "D": 1,
         "SUSTAIN": 2, "S": 2,
         "RELEASE": 3, "R": 3,
         "ATTACK_CV": 4,
         "DECAY_CV": 5,
         "SUSTAIN_CV": 6,
         "RELEASE_CV": 7,
         "PUSH": 8,
     },
     inputs={
         "ATTACK": 0,
         "DECAY": 1,
         "SUSTAIN": 2,
         "RELEASE": 3,
         "GATE": 4,
         "RETRIG": 5,
     },
     outputs={
         "ENV": 0, "OUT": 0,
     })

_reg("Fundamental", "LFO",
     # Params from C++ enum:
     #   OFFSET_PARAM=0, INVERT_PARAM=1, FREQ_PARAM=2, FM_PARAM=3,
     #   FM2_PARAM=4 (removed), PW_PARAM=5, PWM_PARAM=6
     params={
         "OFFSET": 0,   # offset toggle (default 1.0 = on)
         "INVERT": 1,   # invert toggle (default 0 = off)
         "FREQ":   2,   # frequency in Hz (default 1.0)
         "FM":     3,   # FM CV attenuator (default 0)
         "PW":     5,   # pulse width (0..1, default 0.5)
         "PWM":    6,   # PWM CV attenuator (default 0)
     },
     # Inputs from C++ enum:
     #   FM_INPUT=0, FM2_INPUT=1 (removed), RESET_INPUT=2, PW_INPUT=3, CLOCK_INPUT=4
     inputs={
         "FM": 0,
         "RESET": 2,
         "PW": 3,
         "CLOCK": 4,
     },
     outputs={
         "SIN": 0, "SINE": 0,
         "TRI": 1, "TRIANGLE": 1,
         "SAW": 2,
         "SQR": 3, "SQUARE": 3,
     })

_reg("Fundamental", "Noise",
     params={},
     inputs={},
     outputs={
         "WHITE": 0,
         "PINK": 1,
         "RED": 2,
         "VIOLET": 3,
         "BLUE": 4,
         "GRAY": 5,
         "BLACK": 6,
     })

_reg("Fundamental", "SEQ3",
     params={
         "TEMPO": 0,
         "RUN": 1,
         "RESET": 2,
         "TRIG": 3,
         # CV params 4-27 (3 rows x 8 steps): CV_ROW0_STEP0 .. CV_ROW2_STEP7
         **{f"CV_{r}_{s}": 4 + r * 8 + s for r in range(3) for s in range(8)},
         # Gate params 28-35 (8 steps)
         **{f"GATE_{s}": 28 + s for s in range(8)},
         "TEMPO_CV": 36,
         "STEPS_CV": 37,
         "CLOCK": 38,
     },
     inputs={
         "TEMPO": 0,
         "CLOCK": 1,
         "RESET": 2,
         "STEPS": 3,
         "RUN": 4,
     },
     outputs={
         "TRIG": 0,
         "CV1": 1, "CV_A": 1,
         "CV2": 2, "CV_B": 2,
         "CV3": 3, "CV_C": 3,
         **{f"STEP_{s}": 4 + s for s in range(8)},
         "STEPS": 12,
         "CLOCK": 13,
         "RUN": 14,
         "RESET": 15,
     })

_reg("Fundamental", "Mult",
     params={},
     inputs={
         "IN1": 0, "A": 0,
         "IN2": 3, "B": 3,
     },
     outputs={
         "OUT1A": 0, "OUT1B": 1, "OUT1C": 2,
         "OUT2A": 3, "OUT2B": 4, "OUT2C": 5,
     })

# ---------------------------------------------------------------------------
# Valley (free)
# ---------------------------------------------------------------------------

_reg("Valley", "Plateau",
     # Param IDs verified from discovered/Valley/Plateau/2.4.5.json
     # Previous registry had SIZE=3,DIFFUSION=4,DECAY=5 -- all wrong (off by 2+).
     params={
         "DRY":            0,   # Dry level
         "WET":            1,   # Wet level
         "PRE_DELAY":      2,   # Pre-delay
         "IN_LO_CUT":      3,   # Input low cut
         "IN_HI_CUT":      4,   # Input high cut
         "SIZE":           5,   # Room size
         "DIFFUSION":      6,   # Diffusion
         "DECAY":          7,   # Decay time
         "REVERB_HI_CUT":  8,   # Reverb high cut
         "REVERB_LO_CUT":  9,   # Reverb low cut
         "MOD_SPEED":      10,  # Modulation rate
         "MOD_SHAPE":      11,  # Modulation shape
         "MOD_DEPTH":      12,  # Modulation depth
         "HOLD":           13,  # Hold (freeze reverb tail)
         "CLEAR":          14,  # Clear reverb buffer
         "HOLD_TOGGLE":    15,  # Hold toggle mode
         # id 16 is blank/unused
         "DRY_CV":         17,
         "WET_CV":         18,
         "IN_LO_CUT_CV":   19,
         "IN_HI_CUT_CV":   20,
         "SIZE_CV":        21,
         "DIFFUSION_CV":   22,
         "DECAY_CV":       23,
         "REVERB_HI_CUT_CV": 24,
         "REVERB_LO_CUT_CV": 25,
         "MOD_SPEED_CV":   26,
         "MOD_SHAPE_CV":   27,
         "MOD_DEPTH_CV":   28,
         "TUNED":          29,  # Tuned reverb mode
         "DIFFUSE_IN":     30,  # Diffuse input
     },
     inputs={
         "IN_L": 0, "L": 0,
         "IN_R": 1, "R": 1,
         "DRY_CV": 2,
         "WET_CV": 3,
         "PRE_DELAY_CV": 4,
         "SIZE_CV": 5,
         "DIFFUSION_CV": 6,
         "DECAY_CV": 7,
         "REVERB_HPF_CV": 8,
         "REVERB_LPF_CV": 9,
         "IN_HPF_CV": 10,
         "IN_LPF_CV": 11,
         "FREEZE_CV": 12,
         "MOD_SPEED_CV": 13,
         "MOD_SHAPE_CV": 14,
         "MOD_DEPTH_CV": 15,
         "CLEAR": 16,
     },
     outputs={
         "OUT_L": 0, "L": 0,
         "OUT_R": 1, "R": 1,
     })

# ---------------------------------------------------------------------------
# Bogaudio (free)
# ---------------------------------------------------------------------------

_reg("Bogaudio", "Bogaudio-ADSR",
     # Params from C++ enum:
     #   ATTACK_PARAM=0, DECAY_PARAM=1, SUSTAIN_PARAM=2, RELEASE_PARAM=3, LINEAR_PARAM=4
     params={
         "ATTACK":  0,
         "DECAY":   1,
         "SUSTAIN": 2,
         "RELEASE": 3,
         "LINEAR":  4,
     },
     # Only 1 input and 1 output per C++ enum
     inputs={
         "GATE": 0,
     },
     outputs={
         "ENV": 0, "OUT": 0,
     })

_reg("Bogaudio", "Bogaudio-LFO",
     # Params from C++ enum:
     #   FREQUENCY_PARAM=0, SLOW_PARAM=1, SAMPLE_PARAM=2, PW_PARAM=3,
     #   OFFSET_PARAM=4, SCALE_PARAM=5, SMOOTH_PARAM=6
     params={
         "FREQ":   0,   # frequency
         "SLOW":   1,   # slow mode toggle (set to 1 for sub-Hz rates)
         "SAMPLE": 2,   # sample rate reduction
         "PW":     3,   # pulse width
         "OFFSET": 4,   # DC offset
         "SCALE":  5,   # output scale
         "SMOOTH": 6,   # output smoothing
     },
     # Inputs from C++ enum:
     #   SAMPLE_INPUT=0, PW_INPUT=1, OFFSET_INPUT=2, SCALE_INPUT=3,
     #   PITCH_INPUT=4, RESET_INPUT=5
     inputs={
         "SAMPLE": 0,
         "PW":     1,
         "OFFSET": 2,
         "SCALE":  3,
         "PITCH":  4, "VOCT": 4,
         "RESET":  5,
     },
     # Outputs from C++ enum:
     #   RAMP_UP_OUTPUT=0, RAMP_DOWN_OUTPUT=1, SQUARE_OUTPUT=2,
     #   TRIANGLE_OUTPUT=3, SINE_OUTPUT=4, STEPPED_OUTPUT=5
     outputs={
         "SAW": 0, "RAMP": 0, "RAMP_UP": 0,
         "RAMP_DOWN": 1,
         "SQR": 2, "SQUARE": 2,
         "TRI": 3, "TRIANGLE": 3,
         "SIN": 4, "SINE": 4,
         "STEPPED": 5,
     })

_reg("Bogaudio", "Bogaudio-Mix4",
     # Params: per channel order is Level/Panning/Mute (from rack_introspect)
     params={
         "LEVEL1": 0,  "PAN1": 1,  "MUTE1": 2,
         "LEVEL2": 3,  "PAN2": 4,  "MUTE2": 5,
         "LEVEL3": 6,  "PAN3": 7,  "MUTE3": 8,
         "LEVEL4": 9,  "PAN4": 10, "MUTE4": 11,
         "MASTER": 12, "MASTER_MUTE": 13, "DIM": 14,
     },
     # Inputs: per channel order is LEVEL_CV / PAN_CV / IN (confirmed visually)
     inputs={
         "LEVEL_CV1": 0, "CV1": 0,
         "PAN_CV1":   1,
         "IN1":       2,
         "LEVEL_CV2": 3, "CV2": 3,
         "PAN_CV2":   4,
         "IN2":       5,
         "LEVEL_CV3": 6, "CV3": 6,
         "PAN_CV3":   7,
         "IN3":       8,
         "LEVEL_CV4": 9, "CV4": 9,
         "PAN_CV4":   10,
         "IN4":       11,
     },
     outputs={
         "OUT_L": 0, "L": 0,
         "OUT_R": 1, "R": 1,
     })

_reg("Bogaudio", "Bogaudio-Pressor",
     # Params: THRESHOLD=0, RATIO=1, ATTACK=2, RELEASE=3, OUTPUT_GAIN=4,
     #         INPUT_GAIN=5, DETECTOR_MIX=6, MODE=7, DETECTOR_MODE=8, KNEE=9
     params={
         "THRESHOLD":    0,
         "RATIO":        1,
         "ATTACK":       2,
         "RELEASE":      3,
         "OUTPUT_GAIN":  4,
         "INPUT_GAIN":   5,
         "DETECTOR_MIX": 6,
         "MODE":         7,
         "KNEE":         9,
     },
     # Inputs: LEFT=0, SIDECHAIN=1, THRESHOLD=2, RATIO=3, RIGHT=4,
     #         ATTACK=5, RELEASE=6, INPUT_GAIN=7, OUTPUT_GAIN=8
     inputs={
         "IN_L": 0, "LEFT": 0, "L": 0,
         "SIDECHAIN": 1,
         "THRESHOLD_CV": 2,
         "RATIO_CV": 3,
         "IN_R": 4, "RIGHT": 4, "R": 4,
         "ATTACK_CV": 5,
         "RELEASE_CV": 6,
         "INPUT_GAIN_CV": 7,
         "OUTPUT_GAIN_CV": 8,
     },
     # Outputs: ENVELOPE=0, LEFT=1, RIGHT=2
     outputs={
         "ENV": 0, "ENVELOPE": 0,
         "OUT_L": 1, "LEFT": 1, "L": 1,
         "OUT_R": 2, "RIGHT": 2, "R": 2,
     })

_reg("Bogaudio", "Bogaudio-AddrSeq",
     # 8-step CV sequencer (closest registered option to 16-step)
     # Params: STEPS=0, DIRECTION=1, SELECT=2, OUT1-8=3-10
     params={
         "STEPS":     0,
         "DIRECTION": 1,
         "SELECT":    2,
         "OUT1": 3, "OUT2": 4, "OUT3": 5,  "OUT4": 6,
         "OUT5": 7, "OUT6": 8, "OUT7": 9,  "OUT8": 10,
     },
     inputs={
         "CLOCK": 0,
         "RESET": 1,
         "SELECT": 2,
     },
     outputs={
         "OUT": 0, "CV": 0,
     })

_reg("Bogaudio", "Bogaudio-SampleHold",
     params={
         "TRACK1": 0,
         "TRACK2": 1,
         "NOISE_TYPE": 2,
         "IN_RANGE": 3,
         "IN_OFFSET": 4,
         "GATE_BIAS": 5,
     },
     inputs={
         "CLOCK1": 0, "GATE1": 0,
         "IN1": 1,
         "CLOCK2": 2, "GATE2": 2,
         "IN2": 3,
     },
     outputs={
         "OUT1": 0, "OUT": 0,
         "OUT2": 1,
     })

# ---------------------------------------------------------------------------
# Befaco (free)
# ---------------------------------------------------------------------------

_reg("Befaco", "EvenVCO",
     params={
         "OCTAVE": 0,
         "TUNE": 1,
         "PW": 2,
     },
     inputs={
         "EXP": 0,
         "VOCT": 1, "V_OCT": 1, "PITCH": 1,
         "PWM": 2,
         "LIN": 3,
     },
     outputs={
         "TRI": 0,
         "SINE": 1,
         "SAW": 2,
         "PULSE": 3,
         "EVEN": 4,
     })

_reg("Befaco", "Kickall",
     # Param IDs verified from discovered/Befaco/Kickall/2.9.1.json
     # Previous registry had DECAY/FM_AMOUNT/TONE/ATTACK/DRIVE at 1-5 -- all wrong.
     params={
         "FREQ":        0,  # Tune (base pitch)
         "MANUAL_TRIG": 1,  # Manual trigger button (not useful in patches)
         "WAVE_SHAPE":  2,  # Wave shape
         "VCA_DECAY":   3,  # VCA envelope decay time
         "PITCH_DECAY": 4,  # Pitch envelope decay time
         "PITCH_ENV":   5,  # Pitch envelope attenuator
     },
     inputs={
         "GATE": 0,
         "DECAY_CV": 1,
         "PITCH_CV": 2,
         "FM": 3,
     },
     outputs={
         "OUT": 0,
     })

# ---------------------------------------------------------------------------
# AlrightDevices (free)
# ---------------------------------------------------------------------------

_reg("AlrightDevices", "Chronoblob2",
     # Param IDs verified from discovered/AlrightDevices/Chronoblob2/2.1.0.json
     # Previous registry had TIME=0, FEEDBACK=1 -- swapped! Also SLIP/SLIP_MODE/RATIO/PING_PONG were wrong.
     # CV depth params (3-6) are knobs, not jacks -- separate from the CV inputs below.
     params={
         "FEEDBACK":      0,  # Feedback amount
         "TIME":          1,  # Delay time
         "MIX":           2,  # Dry/wet mix
         "FEEDBACK_CV":   3,  # Feedback CV depth (attenuverter)
         "L_TIME_CV":     4,  # L delay time CV depth
         "R_TIME_CV":     5,  # R delay time CV depth
         "MIX_CV":        6,  # Dry/wet CV depth
         "LOOP":          7,  # Loop mode
         "TIME_MOD_MODE": 8,  # Time modulation mode
         "DELAY_MODE":    9,  # Delay mode
     },
     inputs={
         "TIME_CV": 0,
         "FEEDBACK_CV": 1,
         "MIX_CV": 2,
         "SLIP_CV": 3,
         "RATIO_CV": 4,
         "IN_L": 5, "L": 5,
         "IN_R": 6, "R": 6,
         "CLOCK": 7,
     },
     outputs={
         "OUT_L": 0, "L": 0,
         "OUT_R": 1, "R": 1,
     })

# ---------------------------------------------------------------------------
# ImpromptuModular (free)
# ---------------------------------------------------------------------------

_reg("ImpromptuModular", "Clocked-Clkd",
     # Params from Clkd.cpp enum:
     #   RATIO_PARAMS(0..2): 0=CLK1_ratio, 1=CLK2_ratio, 2=CLK3_ratio
     #   BPM_PARAM=3 (range 30-300, value IS the BPM, default 120)
     #   RESET_PARAM=4, RUN_PARAM=5, BPMMODE_DOWN=6, BPMMODE_UP=7, ...
     # RATIO values: positive = multiply (1=x1.5, 2=x2, 3=x3, 4=x4...),
     #               negative = divide, 0 = same as master
     params={
         "RATIO1": 0,   # CLK1 ratio (positive=faster, negative=slower)
         "RATIO2": 1,   # CLK2 ratio
         "RATIO3": 2,   # CLK3 ratio
         "BPM":    3,   # Master BPM (30-300, set to actual BPM value)
         "RESET":  4,
         "RUN":    5,   # 1=running, 0=stopped
     },
     # Inputs from Clkd.cpp enum: RESET=0, RUN=1, BPM_INPUT=2
     inputs={
         "RESET":     0,
         "RUN":       1,
         "BPM_INPUT": 2,
     },
     outputs={
         "CLK0": 0, "MASTER": 0,   # master clock (1 pulse per beat)
         "CLK1": 1,                 # sub-clock 1 (rate set by RATIO1)
         "CLK2": 2,                 # sub-clock 2
         "CLK3": 3,                 # sub-clock 3
         "RESET": 4,
         "RUN":   5,
         "BPM":   6,
     })

# ---------------------------------------------------------------------------
# AudibleInstruments / Mutable Instruments Plaits (free)
# ---------------------------------------------------------------------------

_reg("AudibleInstruments", "Plaits",
     # Param IDs verified from discovered/AudibleInstruments/Plaits/2.0.0.json
     # Previous registry was off by 1 for most params (skipped MODEL_B at id 1).
     # Discovered order: 0=MODEL(pitched), 1=MODEL_B(noise/perc), 2=FREQ, 3=HARMONICS,
     #   4=TIMBRE, 5=MORPH, 6=TIMBRE_CV, 7=FREQ_CV, 8=MORPH_CV, 9=LPG_COLOUR, 10=LPG_DECAY
     params={
         "MODEL":               0,   # Pitched model select (0-1 maps to 8 models)
         "MODEL_B":             1,   # Noise/percussive model select
         "FREQ":                2,   # Octave offset from A4 (-4 to +4)
         "HARMONICS":           3,   # Harmonics amount
         "TIMBRE":              4,   # Timbre
         "MORPH":               5,   # Morph
         "TIMBRE_ATTENUVERTER": 6,   # Timbre CV depth (-1 to 1, default 0)
         "FM_ATTENUVERTER":     7,   # Frequency CV depth (-1 to 1, default 0)
         "MORPH_ATTENUVERTER":  8,   # Morph CV depth (-1 to 1, default 0)
         "LPG_COLOUR":          9,   # LPG filter response (0-1)
         "DECAY":               10,  # LPG decay time (0-1)
     },
     inputs={
         "PITCH": 0, "VOCT": 0,
         "HARMONICS": 1,
         "TIMBRE": 2,
         "MORPH": 3,
         "FM": 4,
         "TRIGGER": 5, "GATE": 5,
         "LEVEL": 6,
         "MODEL": 7,
     },
     outputs={
         "OUT": 0, "MAIN": 0,
         "AUX": 1,
     })

# ---------------------------------------------------------------------------
# JW-Modules
# ---------------------------------------------------------------------------

_reg("JW-Modules", "NoteSeq16",
     # 16-step grid sequencer. Rows=pitches, columns=steps. Empty column = rest.
     # Polyphonic outputs: channel count = number of active cells in current column.
     # For monophonic use, activate one cell per column.
     # LENGTH_KNOB controls active step count (1-16).
     params={
         "LENGTH":       0,   # number of active steps (1-16)
         "PLAY_MODE":    1,   # 0=fwd loop, 1=bwd, 2=fwd/bwd, 3=bwd/fwd, 4=random
         "CLEAR":        2,
         "RND_TRIG":     3,
         "RND_AMT":      4,
         "SCALE":        5,
         "NOTE":         6,
         "OCTAVE":       7,
         "LOW_HIGH":     8,
         "INCLUDE_INACTIVE": 9,
         "START":        10,
         "FOLLOW":       11,
     },
     inputs={
         "CLOCK": 0,
         "RESET": 1,
         "RND_TRIG": 2,
         "FLIP": 4,
         "SHIFT": 5,
         "LENGTH": 6,
         "START": 7,
     },
     outputs={
         "VOCT": 0, "POLY_VOCT": 0,
         "GATE": 1, "POLY_GATE": 1,
         "EOC": 2,
     })

# ---------------------------------------------------------------------------
# AaronStatic
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# SlimeChild-Substation (v2.2.6)
# Subharmonic, Polyrhythmic Synthesis Toolkit
# Ports verified from https://slimechildaudio.com/substation/manual/
# ---------------------------------------------------------------------------

_reg("SlimeChild-Substation", "SlimeChild-Substation-Clock",
     # Tempo = log2(BPM/60).  Default=1 -> 2^1 Hz = 2 Hz = 120 BPM.
     # Formula: Tempo = log2(BPM / 60)   e.g. 127 BPM -> log2(2.1167) ≈ 1.082
     # BASE output = master rate.  MULT output = BASE * Multiplier (integer 1-16).
     params={
         "TEMPO": 0,   # log2 Hz, default=1 (120 BPM)
         "RUN":   1,   # 0=stopped, 1=running
         "MULT":  2,   # integer multiplier 1-16 for MULT output
     },
     inputs={
         "RUN":  0,   # gate: starts/stops clock
         "SYNC": 1,   # sync to external clock
     },
     outputs={
         "BASE": 0,   # master clock (BPM rate)
         "MULT": 1,   # multiplied clock (BASE * MULT param)
     })

_reg("SlimeChild-Substation", "SlimeChild-Substation-Envelopes",
     # Dual semi-interruptable AD envelopes (no sustain stage).
     # Hold param=1 converts to AR (holds while gate is high).
     params={
         "EG1_ATTACK": 0,   # log scale [-3, 1]
         "EG1_DECAY":  1,   # log scale [-3, 1]
         "EG2_ATTACK": 2,
         "EG2_DECAY":  3,
         "HOLD":       4,   # 0=AD, 1=AR (hold while gate high)
         "TRIGGER":    5,   # manual trigger button
     },
     inputs={
         "TRIG1": 0, "TRIGGER1": 0, "GATE1": 0,
         "TRIG2": 1, "TRIGGER2": 1, "GATE2": 1,
     },
     outputs={
         "ENV1": 0,
         "ENV2": 1,
     })

_reg("SlimeChild-Substation", "SlimeChild-Substation-Filter",
     # Physically-modelled 24dB/oct ladder lowpass.
     # Frequency param is in log-Hz units (default ~4.98 ≈ mid-range).
     # V/OCT input tracks pitch (1V/oct).
     params={
         "FREQ": 0,       # log-Hz, default=4.98
         "RES":  1,       # resonance [0, 1.2]
         "FM":   2,       # FM attenuverter [-1, 1]
     },
     inputs={
         "VOCT": 0, "V/OCT": 0,   # pitch tracking
         "FM":   1,                # FM CV
         "IN":   2,                # audio in
     },
     outputs={
         "OUT": 0,
     })

_reg("SlimeChild-Substation", "SlimeChild-Substation-VCA",
     params={
         "LEVEL": 0,   # [0, 1], default=1
     },
     inputs={
         "CV": 0,
         "IN": 1,
     },
     outputs={
         "OUT": 0,
     })

_reg("SlimeChild-Substation", "SlimeChild-Substation-Mixer",
     # 3-channel saturating mixer with chain I/O.
     # Channels: Level knob + CV attenuverter each. Mix Level = master.
     params={
         "LEVEL1": 0, "CH1_LEVEL": 0,
         "LEVEL2": 1, "CH2_LEVEL": 1,
         "LEVEL3": 2, "CH3_LEVEL": 2,
         "MOD1":   3, "CH1_MOD": 3,
         "MOD2":   4, "CH2_MOD": 4,
         "MOD3":   5, "CH3_MOD": 5,
         "MIX":    6, "MIX_LEVEL": 6,
         "CHAIN_GAIN": 7,
         "DRIVE":  8,
     },
     inputs={
         "IN1": 0, "CH1": 0,
         "IN2": 1, "CH2": 1,
         "IN3": 2, "CH3": 2,
         "CV1": 3,
         "CV2": 4,
         "CV3": 5,
         "CHAIN": 6,
         "LEVEL": 7,
     },
     outputs={
         "CHAIN": 0,
         "OUT":   1,
     })

_reg("SlimeChild-Substation", "SlimeChild-Substation-Quantizer",
     params={
         "TEMPERAMENT":  0,
         "SCALE":        1,
         "ROOT":         2,   # [0, 11] semitone
         "OCTAVE":       3,   # [-4, 4]
         "TRANSPOSE":    4,
     },
     inputs={
         "ROOT": 0,
         "OCT":  1,
         "IN":   2,
     },
     outputs={
         "OUT": 0,
     })

# SubOscillator ports confirmed from https://slimechildaudio.com/substation/manual/suboscillator/
# Standalone oscillator with base output + two sub-harmonic outputs.
# SUB 1 / SUB 2 inputs are CV for dynamic subdivision amount.

_reg("SlimeChild-Substation", "SlimeChild-Substation-SubOscillator",
     params={
         "BASE_FREQ":   0,   # [-48, 48] semitones
         "WAVEFORM":    1,   # [0, 2]
         "SUBDIV1":     2,   # [1, 16]
         "SUBDIV2":     3,   # [1, 16]
         "PWM":         4,   # [0, 1], default=0.5
         "DETUNE":      5,   # [-2, 2]
     },
     inputs={
         "VOCT":   0, "V/OCT": 0,
         "SUB1":   1,   # CV for subdivision 1 amount
         "SUB2":   2,   # CV for subdivision 2 amount
         "PWM":    3,
     },
     outputs={
         "BASE": 0,   # main oscillator output
         "SUB1": 1,   # sub-harmonic 1 (frequency / SUBDIV1)
         "SUB2": 2,   # sub-harmonic 2 (frequency / SUBDIV2)
     })

# PolySeq ports confirmed from https://slimechildaudio.com/substation/manual/polyseq/
# Has CLOCK, RESET, DIV[N] inputs and TRIG[X] + SEQ[X] outputs.
# Exact count/order of DIV inputs and TRIG/SEQ outputs confirmed as:
#   Inputs:  CLOCK(0), RESET(1), DIV1(2), DIV2(3), DIV3(4), DIV4(5)
#   Outputs: TRIG1(0), TRIG2(1), TRIG3(2), TRIG4(3), SEQ_A(4), SEQ_B(5), SEQ_C(6)
# (DIV CV inputs and exact output indices are best-effort; verify in Rack if needed)

_reg("SlimeChild-Substation", "SlimeChild-Substation-PolySeq",
     # 3-sequence polyrhythm sequencer (A, B, C) with 4 rhythmic dividers.
     # Each sequence has 4 steps (params 0-11, grouped A/B/C).
     # Dividers route steps to sequences via routing matrix (params 16-27).
     params={
         "A1": 0, "A2": 1, "A3": 2, "A4": 3,
         "B1": 4, "B2": 5, "B3": 6, "B4": 7,
         "C1": 8, "C2": 9, "C3": 10, "C4": 11,
         "DIV1": 12, "DIV2": 13, "DIV3": 14, "DIV4": 15,
         "DIV1_A": 16, "DIV2_A": 17, "DIV3_A": 18, "DIV4_A": 19,
         "DIV1_B": 20, "DIV2_B": 21, "DIV3_B": 22, "DIV4_B": 23,
         "DIV1_C": 24, "DIV2_C": 25, "DIV3_C": 26, "DIV4_C": 27,
         "RANGE_A": 28, "RANGE_B": 29, "RANGE_C": 30,
         "SUM_MODE": 31,
         "RESET": 32,
         "NEXT":  33,
         "STEPS": 34,
     },
     inputs={
         "CLOCK": 0,
         "RESET": 1,
         "DIV1":  2,   # CV for divider 1 rate
         "DIV2":  3,
         "DIV3":  4,
         "DIV4":  5,
     },
     outputs={
         "TRIG1": 0, "TRIG_A": 0,
         "TRIG2": 1, "TRIG_B": 1,
         "TRIG3": 2, "TRIG_C": 2,
         "TRIG4": 3,
         "SEQ_A": 4, "A": 4,
         "SEQ_B": 5, "B": 5,
         "SEQ_C": 6, "C": 6,
     })

_reg("AaronStatic", "ChordCV",
     params={
         "ROOT_NOTE": 0,
         "CHORD_TYPE": 1,  # -4=major, -3=minor, -2=dom7, -1=min7, 0=maj7, 1=sus2, 2=sus4, 3=dim, 4=aug
         "INVERSION": 2,
         "VOICING": 3,
     },
     inputs={
         "ROOT": 0, "PITCH": 0, "VOCT": 0,
         "TYPE": 1,
         "INVERSION": 2,
         "VOICING": 3,
     },
     outputs={
         "NOTE1": 0,
         "NOTE2": 1,
         "NOTE3": 2,
         "NOTE4": 3,
         "POLY": 4,
     })


# ---------------------------------------------------------------------------
# CountModula (v2.5.0)
# ---------------------------------------------------------------------------

# Sequencer16: 16-step CV + gate sequencer with per-step trigger/gate select.
# This is the 303/606-style module: one module for both pitch CV and gate pattern.
#
# Port IDs verified empirically against enum OutputIds in SequencerSrc.hpp
# (master branch, countmodula/VCVRackPlugins). The enum order is the source of
# truth -- addOutput() call order in the widget is DIFFERENT and misleading.
#
# Outputs (enum order):  GATE=0, TRIG=1, END=2, CV=3, CVI=4
#   GATE: held gate output (high while step is active, use for ADSR sustain)
#   TRIG: 1ms trigger pulse per step (use for percussive envelopes)
#   END:  fires once at end of a 1-shot cycle (not useful for looping patches)
#   CV:   pitch CV out (1V/oct)
#   CVI:  inverted pitch CV
#
# Params:
#   STEP{N} (ids 16-31): per-step CV value (pitch)
#   TRIG{N} (ids 37-52): per-step trigger select (0=off, 1=on) -- drives TRIG out
#   GATE{N} (ids 53-68): per-step gate select  (0=off, 1=on) -- drives GATE out
#   LENGTH  (id 32):     active step count (1-16)
_reg("CountModula", "Sequencer16",
     params={
         # Per-step CV values (pitch)
         **{f"STEP{i+1}": 16 + i for i in range(16)},
         # Per-step trigger on/off (1ms pulse -- use for percussive envelopes)
         **{f"TRIG{i+1}": 37 + i for i in range(16)},
         # Per-step gate on/off (held high -- use for ADSR sustain)
         **{f"GATE{i+1}": 53 + i for i in range(16)},
         "LENGTH":   32,
         "RANGE_SW": 35,  # CV output scale: 1-8V full-scale (default=8). output = STEP_value × RANGE_SW
     },
     inputs={
         "RUN":   0,  # enum order: RUN first, then CLOCK, then RESET
         "CLOCK": 1,
         "RESET": 2,
     },
     outputs={
         "GATE": 0,  # held gate (ADSR sustain)
         "TRIG": 1,  # 1ms pulse (percussive)
         "END":  2,  # 1-shot end pulse (ignore for looping patches)
         "CV":   3,  # pitch CV (1V/oct)
         "CVI":  4,  # inverted pitch CV
     })

# GateSequencer16: 8-track × 16-step gate/trigger sequencer (no CV).
# Track 1 step params: ids 0-15. Track N: (N-1)*16 + step-1.
_reg("CountModula", "GateSequencer16",
     params={
         **{f"T1_S{i+1}": i for i in range(16)},      # Track 1 gate steps 1-16
         **{f"T2_S{i+1}": 16 + i for i in range(16)}, # Track 2
         "LENGTH": 128,
     },
     inputs={
         "CLOCK": 0,
         "RESET": 1,
         "RUN":   2,
     },
     outputs={
         "GATE1": 0, "GATE2": 1, "GATE3": 2, "GATE4": 3,
         "GATE5": 4, "GATE6": 5, "GATE7": 6, "GATE8": 7,
         "TRIG1": 8, "TRIG2": 9, "TRIG3": 10, "TRIG4": 11,
         "TRIG5": 12, "TRIG6": 13, "TRIG7": 14, "TRIG8": 15,
         "END": 16,
     })


# ---------------------------------------------------------------------------
# AgentRack (our plugin)
# Port IDs are frozen in the C++ source -- verified from enum order.
# ---------------------------------------------------------------------------

_reg("AgentRack", "Attenuate",
     params={
         "SCALE_0": 0, "SCALE_1": 1, "SCALE_2": 2,
         "SCALE_3": 3, "SCALE_4": 4, "SCALE_5": 5,
         # Legacy alias: row 0 matches old single-channel IDs
         "SCALE": 0,
     },
     inputs={
         "IN_0": 0, "IN_1": 1, "IN_2": 2,
         "IN_3": 3, "IN_4": 4, "IN_5": 5,
         "IN": 0,  # legacy alias
     },
     outputs={
         "OUT_0": 0, "OUT_1": 1, "OUT_2": 2,
         "OUT_3": 3, "OUT_4": 4, "OUT_5": 5,
         "OUT": 0,  # legacy alias
     })

_reg("AgentRack", "Noise",
     params={},
     inputs={},
     outputs={
         "WHITE":   0,
         "PINK":    1,
         "BROWN":   2,
         "BLUE":    3,
         "VIOLET":  4,
         "CRACKLE": 5,
     })

_reg("AgentRack", "ADSR",
     params={
         "ATTACK":  0,
         "DECAY":   1,
         "SUSTAIN": 2,
         "RELEASE": 3,
     },
     inputs={
         "GATE": 0,
     },
     outputs={
         "ENV": 0,
     })

_reg("AgentRack", "Crinkle",
     params={
         "TUNE":      0,
         "TIMBRE":    1,
         "SYMMETRY":  2,
         "TIMBRE_CV": 3,
     },
     inputs={
         "VOCT":   0,
         "TIMBRE": 1,
     },
     outputs={
         "OUT": 0,
     })

_reg("AgentRack", "Inspector",
     params={},
     inputs={},
     outputs={})

_reg("AgentRack", "Ladder",
     params={
         "FREQ":   0,
         "RES":    1,
         "SPREAD": 2,
         "SHAPE":  3,
         "MODE":   4,  # 0=A freq-comp, 1=B noise-kick, 2=C standard
     },
     inputs={
         "IN":         0,
         "CUTOFF_MOD": 1,
         "RES_MOD":    2,
         "SPREAD_MOD": 3,
         "SHAPE_MOD":  4,
     },
     outputs={
         "OUT": 0,
     })

_reg("AgentRack", "Saphire",
     params={
         "MIX":  0,
         "TIME": 1,
         "BEND": 2,
         "TONE": 3,
         "PRE":  4,
         "IR":   5,
     },
     inputs={
         "IN_L": 0,
         "IN_R": 1,
     },
     outputs={
         "OUT_L": 0,
         "OUT_R": 1,
     })

_reg("AgentRack", "Sonic",
     params={
         "AMOUNT":      0,
         "COLOR":       1,
         "LOW_CONTOUR": 2,
         "PROCESS":     3,
     },
     inputs={
         "IN":        0,
         "CV_AMOUNT": 1,
         "CV_COLOR":  2,
     },
     outputs={
         "OUT": 0,
     })
