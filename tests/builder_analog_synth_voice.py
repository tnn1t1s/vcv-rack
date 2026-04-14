"""
Fluent PatchBuilder version of the analog synth voice.

Signal chain:
  VCO (square) --> VCF (low-pass) --> AudioInterface2

Modulation (auto-attenuators -- no manual param lookup):
  LFO.Sine --> VCO.Pulse_width_modulation (auto-opens its attenuator)
  LFO.Sine --> VCF.Frequency (auto-opens Cutoff_frequency_CV)

Proof state progression:
  after 4 modules:          proven=False
  after chain(vco.Square, vcf.i.Audio):              proven=False
  after .fan_out(audio.i.Left_input, Right_input):   proven=True  <-- before save()

Run:
    uv run python -m tests.builder_analog_synth_voice
"""

import os

from vcvpatch import PatchBuilder

OUT_PATH = os.path.join(os.path.dirname(__file__), "builder_analog_synth_voice.vcv")

pb = PatchBuilder(zoom=1.0)

lfo   = pb.module("Fundamental", "LFO",          Frequency=0.4)
vco   = pb.module("Fundamental", "VCO",          Frequency=0.0, Pulse_width=0.5)
vcf   = pb.module("Fundamental", "VCF",          Cutoff_frequency=0.6)
audio = pb.module("Core",        "AudioInterface2")

# Audio chain -- reads left-to-right as signal flow.
# fan_out automatically uses VCF.LPF (port 0) as the source.
(pb.chain(vco.o.Square, vcf.i.Audio)
     .fan_out(audio.i.Left_input, audio.i.Right_input))

# Modulation -- explicit source output, auto-opens attenuators; no need to know param IDs.
# Cable type auto-detected: LFO outputs are CV -> blue cables.
(lfo.modulates(vco.i.Pulse_width_modulation, via="Sine", attenuation=0.5)
    .modulates(vcf.i.Frequency, via="Sine", attenuation=0.5))

print(pb.describe())
print()

# build() validates proof state and returns the proven Patch.
patch = pb.build()
patch.save(OUT_PATH)

print("All assertions passed.")
print(f'\n  open -a "VCV Rack 2 Free" "{OUT_PATH}"')
