"""
BusCrush demo -- 8 oscillators spanning the VCO range.

Uses discovered param metadata (vcvpatch/discovered/) as source of truth
rather than hand-annotated registry values.

8 VCOs spread evenly across the FREQ range (-54..+54 st), each one octave
apart. Pulse widths step from narrow to square. All hit BusCrush with no
pre-gain so bus congestion is audible.
"""

import json
import math
from pathlib import Path

from vcvpatch.builder import PatchBuilder

# -- Read FREQ param range directly from discovered metadata (source of truth) --
ROOT = Path(__file__).resolve().parents[1]

with open(ROOT / "vcvpatch" / "discovered" / "Fundamental" / "VCO" / "2.6.4.json") as f:
    vco_meta = json.load(f)

freq_meta = next(p for p in vco_meta["params"] if p["name"] == "Frequency")
f_min, f_max = freq_meta["min"], freq_meta["max"]
print(f"VCO Frequency range from discovered: {f_min} to {f_max} st")

pb = PatchBuilder()

N      = 8
# Spread evenly: -48, -36, -24, -12, 0, 12, 24, 36 (one octave apart)
freqs  = [f_min + (f_max - f_min) * i / (N - 1) for i in range(N)]
# Round to nearest semitone for clarity
freqs  = [round(f) for f in freqs]
widths = [0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]

for i, (f, w) in enumerate(zip(freqs, widths)):
    print(f"  VCO {i+1}: FREQ={f:+d} st  PW={w:.2f}")

vcos = [
    pb.module("Fundamental", "VCO", Frequency=freqs[i], Pulse_width=widths[i])
    for i in range(N)
]

bus   = pb.module("AgentRack", "BusCrush")
audio = pb.module("Core", "AudioInterface2")

CHANNEL_NAMES = [f"Channel {i+1} in" for i in range(8)]

for i, vco in enumerate(vcos):
    pb.connect(vco.o.Square, getattr(bus.i, CHANNEL_NAMES[i].replace(" ", "_")))  # type: ignore

pb.connect(bus.o.Stereo_left_out, audio.i.Left_input)   # type: ignore
pb.connect(bus.o.Stereo_right_out, audio.i.Right_input)  # type: ignore

print(pb.status)
for w in pb.warnings:
    print("WARN:", w)

out = str(ROOT / "patches" / "buscrush_demo_v2.vcv")
pb.save(out)
print(f"Saved: {out}")
