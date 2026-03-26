"""
AgentRack ADSR module spec.
The canonical example of a self-describing module.
"""

from vcvpatch.contract import (
    ModuleSpec, PortSpec, ParamSpec, ParamPreset, MusicalUse
)

ADSR = ModuleSpec(
    module_id     = "agentrack.adsr.v1",
    name          = "ADSR Envelope",
    version       = "1.0.0",
    category      = "control_envelope",
    ensemble_role = "dynamics",
    summary       = (
        "Generates a unipolar contour with attack, decay, sustain, and release "
        "phases in response to a gate signal."
    ),

    ports=[
        PortSpec(
            name          = "gate_in",
            direction     = "input",
            signal_class  = "gate",
            semantic_role = "trigger_source",
            required      = True,
            description   = "High signal starts attack. Falling edge starts release.",
        ),
        PortSpec(
            name          = "retrig_in",
            direction     = "input",
            signal_class  = "trigger",
            semantic_role = "retrigger_source",
            required      = False,
            description   = "Rising edge restarts attack from current level.",
        ),
        PortSpec(
            name          = "env_out",
            direction     = "output",
            signal_class  = "cv_unipolar",
            semantic_role = "envelope_contour",
            range_v       = (0.0, 10.0),
            description   = "Envelope contour 0–10V. Suitable for amplitude or filter CV.",
        ),
    ],

    params=[
        ParamSpec(
            id=0, name="attack", unit="seconds", scale="linear",
            min_val=0.001, max_val=10.0, default=0.01,
            description="Time to rise from 0V to 10V after gate onset.",
            presets=[
                ParamPreset("click",      0.001, "sub-ms transient"),
                ParamPreset("percussive", 0.005, "tight punch"),
                ParamPreset("standard",   0.010, "snappy"),
                ParamPreset("slow",       0.300, "gradual onset"),
                ParamPreset("pad",        1.500, "slow swell"),
            ],
        ),
        ParamSpec(
            id=1, name="decay", unit="seconds", scale="linear",
            min_val=0.001, max_val=10.0, default=0.2,
            description="Time to fall from peak to sustain level.",
            presets=[
                ParamPreset("tight",    0.05,  "very short decay"),
                ParamPreset("pluck",    0.15,  "plucked string feel"),
                ParamPreset("standard", 0.20,  "general purpose"),
                ParamPreset("long",     1.00,  "slow fade to sustain"),
            ],
        ),
        ParamSpec(
            id=2, name="sustain", unit="normalized", scale="linear",
            min_val=0.0, max_val=1.0, default=0.7,
            description=(
                "Level held while gate is high after decay. "
                "0.0 = fully percussive (envelope dies after decay). "
                "1.0 = stays at peak while gate held."
            ),
        ),
        ParamSpec(
            id=3, name="release", unit="seconds", scale="linear",
            min_val=0.001, max_val=20.0, default=0.3,
            description="Time to fall from current level to 0V after gate low.",
            presets=[
                ParamPreset("snap",     0.01, "immediate cutoff"),
                ParamPreset("short",    0.10, "quick release"),
                ParamPreset("standard", 0.30, "general purpose"),
                ParamPreset("long",     1.50, "lingering tail"),
            ],
        ),
    ],

    guarantees=[
        "output is always in [0, 10] V",
        "output is exactly 0V when idle (after release completes)",
        "attack phase is strictly monotonic increasing",
        "release phase is strictly monotonic decreasing",
        "retrigger restarts attack from current level, not from 0V",
        "sustain=0.0 makes envelope fully percussive; gate duration is irrelevant",
    ],

    limitations=[
        "not suitable for audio-rate modulation (designed for note-rate events)",
        "retrig during release extends note; may not be desired in fast passages",
        "parameter modulation takes effect at next phase boundary, not sample-accurate",
    ],

    musical_uses=[
        MusicalUse(
            label   = "pluck",
            params  = {"attack": 0.001, "decay": 0.15, "sustain": 0.0, "release": 0.05},
            routing = "env_out → Attenuate → filter_cutoff_cv  (or direct to amplitude_control)",
            notes   = "sustain=0 means gate duration irrelevant; shape is attack+decay only",
            param_effects = {
                "attack":  "decrease",
                "decay":   "decrease",
                "sustain": "zero",
                "release": "decrease",
            },
        ),
        MusicalUse(
            label   = "pad",
            params  = {"attack": 0.5, "decay": 0.3, "sustain": 0.8, "release": 1.5},
            notes   = "slow attack, high sustain, long release for evolving textures",
            param_effects = {
                "attack":  "increase",
                "sustain": "increase",
                "release": "increase",
            },
        ),
        MusicalUse(
            label   = "percussive_filter_sweep",
            params  = {"attack": 0.001, "decay": 0.15, "sustain": 0.0, "release": 0.1},
            routing = "env_out → Attenuate(SCALE=0.4) → filter_cutoff_cv",
            notes   = "sweep depth set by Attenuate scale, shape set by ADSR params",
            param_effects = {
                "attack":  "zero",
                "decay":   "decrease",
                "sustain": "zero",
            },
        ),
        MusicalUse(
            label   = "gate_following",
            params  = {"attack": 0.001, "decay": 0.001, "sustain": 1.0, "release": 0.01},
            notes   = "output tracks gate: on=10V, off=0V with negligible lag",
            param_effects = {
                "attack":  "zero",
                "decay":   "zero",
                "sustain": "max",
                "release": "zero",
            },
        ),
    ],
)
