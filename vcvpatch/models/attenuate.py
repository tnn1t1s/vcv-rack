"""
Attenuate: one knob (0-1), one input, one output.
OUT = IN × SCALE

The simplest composable unit. The passthrough semantic role means this module
is transparent to the compatibility graph: any connection valid without it is
valid through it.
"""

from vcvpatch.contract import ModuleSpec, PortSpec, ParamSpec, MusicalUse

Attenuate = ModuleSpec(
    module_id     = "agentrack.attenuate.v1",
    name          = "Attenuate",
    version       = "1",
    category      = "utility",
    summary       = "Single-channel CV attenuator. OUT = IN × SCALE.",
    ensemble_role = "none",

    ports = [
        PortSpec(
            name          = "IN",
            direction     = "input",
            signal_class  = "cv",
            semantic_role = "passthrough",
            required      = True,
            description   = "Signal to attenuate. Any signal class accepted.",
        ),
        PortSpec(
            name          = "OUT",
            direction     = "output",
            signal_class  = "cv",
            semantic_role = "passthrough",
            description   = (
                "Attenuated output. Signal class and semantic role of IN are "
                "preserved. Range is IN.range × SCALE."
            ),
        ),
    ],

    params = [
        ParamSpec(
            id          = 0,
            name        = "SCALE",
            unit        = "normalized",
            scale       = "linear",
            min_val     = 0.0,
            max_val     = 1.0,
            default     = 1.0,
            modulatable = False,
            description = "Attenuation factor. 1.0 = unity gain, 0.0 = silence.",
        ),
    ],

    guarantees = [
        "OUT = IN × SCALE at every sample",
        "SCALE=1.0 is unity gain",
        "SCALE=0.0 produces exactly 0V",
        "signal class of IN is preserved at OUT",
        "semantic role of IN is preserved at OUT",
    ],

    limitations = [
        "unipolar only -- no attenuverter, no offset",
        "single channel -- no stereo or polyphonic operation",
    ],

    musical_uses = [
        MusicalUse(
            label  = "lfo_to_filter",
            params = {"SCALE": 0.3},
            notes  = "30% of LFO sweep reaches filter cutoff. Start point for LFO depth dialing.",
        ),
        MusicalUse(
            label  = "envelope_trim",
            params = {"SCALE": 0.5},
            notes  = "Half envelope depth. Useful when full envelope is too aggressive.",
        ),
    ],
)
