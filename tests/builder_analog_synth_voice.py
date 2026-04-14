"""
Fluent PatchBuilder version of the analog synth voice.

Signal chain:
  VCO (square) --> VCF (low-pass) --> AudioInterface2

Modulation (auto-attenuators -- no manual param lookup):
  LFO.SIN --> VCO.PWM    (auto-opens PWM attenuator)
  LFO.SIN --> VCF.CUTOFF (auto-opens FREQ_CV attenuator)

Proof state progression:
  after 4 modules:          proven=False
  after chain(vco.SQR, vcf.i.IN):          proven=False
  after .fan_out(audio.i.IN_L, IN_R):      proven=True  <-- before save()

Run:
    python3 tests/builder_analog_synth_voice.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vcvpatch import PatchBuilder, PatchCompileError, COLORS

OUT_PATH = os.path.join(os.path.dirname(__file__), "builder_analog_synth_voice.vcv")

pb = PatchBuilder(zoom=1.0)

lfo   = pb.module("Fundamental", "LFO",          FREQ=0.4)
vco   = pb.module("Fundamental", "VCO",          FREQ=0.0, PW=0.5)
vcf   = pb.module("Fundamental", "VCF",          FREQ=0.6)
audio = pb.module("Core",        "AudioInterface2")

# Audio chain -- reads left-to-right as signal flow.
# fan_out automatically uses VCF.LPF (port 0) as the source.
(pb.chain(vco.SQR, vcf.i.IN)
     .fan_out(audio.i.IN_L, audio.i.IN_R, color=COLORS["green"]))

# Modulation -- auto-opens attenuators; no need to know param IDs.
(lfo.modulates(vco.i.PWM,    attenuation=0.5, color=COLORS["blue"])
    .modulates(vcf.i.CUTOFF, attenuation=0.5, color=COLORS["purple"]))

print(pb.describe())
print()

# compile() validates proof state and returns a CompiledPatch.
# It raises PatchCompileError (with the full graph report) if not proven.
compiled = pb.compile()
compiled.save(OUT_PATH)

print("All assertions passed.")
print(f'\n  open -a "VCV Rack 2 Free" "{OUT_PATH}"')
