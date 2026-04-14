"""
Patch: LFO sine -> VCO pulse-width modulation -> square wave -> AudioInterface2.

The LFO continuously sweeps the pulse width of the VCO square wave.
At 50% duty (PW=0.5) you hear a clean square; as the LFO pushes it
toward 0% or 100% the timbre thins and fattens.

Module-aware initialisation
---------------------------
VCO has two CV inputs that both default to zero-effect:

  Input port 3 (PWM CV) -- the modulation input itself.
  Param  id  3 (PW)     -- base pulse width knob (0=0%, 0.5=50%, 1=100%).
  Param  id  4 (PWM)    -- attenuator that scales the CV input signal.

If PWM param (id=4) is 0, the LFO is wired but does nothing.
VCONode._port_attenuators maps port->param so the generator can read
and set this without hardcoding.

Run:
    uv run python -m examples.lfo_to_vco_square
"""

import os

from vcvpatch import Patch
from vcvpatch.graph import PatchLoader
from vcvpatch.graph.modules import VCONode

OUT_PATH = os.path.join(os.path.dirname(__file__), "lfo_to_vco_square.vcv")


# ---------------------------------------------------------------------------
# Module-aware param setup -- read from VCONode, don't hardcode
# ---------------------------------------------------------------------------

PWM_IN_PORT  = 3                                      # VCO PWM CV input port
PW_PARAM_ID  = 5                                      # VCO base pulse-width knob
PWM_PARAM_ID = VCONode._port_attenuators[PWM_IN_PORT] # == 6: PWM attenuator

PW_BASE   = 0.5   # start at 50% duty cycle (true square wave)
PWM_DEPTH = 0.5   # attenuator at 50% -- LFO ±5V sweeps PW by ±2.5V
LFO_RATE  = 0.4   # Hz -- slow enough to clearly hear the timbre sweep


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

patch = Patch(zoom=1.0)

lfo   = patch.add("Fundamental", "LFO",            pos=[0,  0],
                  Frequency=LFO_RATE)

vco   = patch.add("Fundamental", "VCO",            pos=[8,  0],
                  Frequency=0.0,
                  Pulse_width=PW_BASE,              # base pulse width = 50% (true square)
                  Pulse_width_modulation=PWM_DEPTH) # PWM attenuator open -- LFO now has effect

audio = patch.add("Core",        "AudioInterface2", pos=[16, 0])

patch.connect(lfo.o.Sine,   vco.i.Pulse_width_modulation)
patch.connect(vco.o.Square, audio.i.Left_input)
patch.connect(vco.o.Square, audio.i.Right_input)

patch.save(OUT_PATH)
print()


# ---------------------------------------------------------------------------
# Prove
# ---------------------------------------------------------------------------

graph = PatchLoader.load(OUT_PATH)
print(graph.report())
print()

assert graph.patch_proven, (
    f"FAIL\n"
    f"  missing:      {graph.missing_modules()}\n"
    f"  audio_reach:  {graph.audio_reachable}\n"
    f"  control_gaps: {graph.control_gaps}\n"
    f"  warnings:     {graph.warnings}"
)
assert not graph.warnings, f"Unexpected warnings: {graph.warnings}"

print("All assertions passed.")
print(f'\n  open -a "VCV Rack 2 Free" "{OUT_PATH}"')
