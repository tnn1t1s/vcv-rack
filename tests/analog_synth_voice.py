"""
Classic analog synth voice: LFO -> VCO (PWM) + VCF (cutoff) -> output.

Signal chain:
  VCO (square) --> VCF (low-pass) --> AudioInterface2

Modulation:
  LFO.Sine --> VCO Pulse_width_modulation input
  LFO.Sine --> VCF Frequency input

The LFO simultaneously sweeps the pulse width and the filter cutoff,
giving the classic "breathing" sound of an analog lead.

Run:
    uv run python -m tests.analog_synth_voice
"""

import os

from vcvpatch import Patch
from vcvpatch.graph import PatchLoader

OUT_PATH = os.path.join(os.path.dirname(__file__), "analog_synth_voice.vcv")

LFO_RATE   = 0.4   # Hz -- slow enough to hear both PWM and filter sweep
VCO_FREQ   = 0.0   # semitones from C4
PW_BASE    = 0.5   # 50% duty cycle (square wave at rest)
PWM_DEPTH  = 0.5   # LFO moves pulse width by ±50%
CUTOFF     = 0.6   # resting filter cutoff (0=closed, 1=open)
CUTOFF_MOD = 0.5   # LFO moves cutoff by ±50%

patch = Patch(zoom=1.0)

lfo  = patch.add("Fundamental", "LFO",            pos=[0,  0],
                 Frequency=LFO_RATE)

vco  = patch.add("Fundamental", "VCO",            pos=[8,  0],
                 Frequency=VCO_FREQ,
                 Pulse_width=PW_BASE,
                 Pulse_width_modulation=PWM_DEPTH)

vcf  = patch.add("Fundamental", "VCF",            pos=[16, 0],
                 Cutoff_frequency=CUTOFF,
                 Cutoff_frequency_CV=CUTOFF_MOD)

audio = patch.add("Core", "AudioInterface2",      pos=[24, 0])

# Modulation routing
patch.connect(lfo.o.Sine, vco.i.Pulse_width_modulation)
patch.connect(lfo.o.Sine, vcf.i.Frequency)

# Audio routing
patch.connect(vco.o.Square, vcf.i.Audio)
patch.connect(vcf.o.LPF, audio.i.Left_input)
patch.connect(vcf.o.LPF, audio.i.Right_input)

patch.save(OUT_PATH)
print()

# Prove it
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
