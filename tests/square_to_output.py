"""
Minimal demo: VCO square wave -> AudioInterface2.

Proves in order:
  1. All modules exist in the installed VCV Rack plugins
  2. Audio reaches the sink

Run:
    python3 tests/square_to_output.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from vcvpatch import Patch, COLORS
from vcvpatch.graph import PatchLoader

OUT_PATH = os.path.join(os.path.dirname(__file__), "square_to_output.vcv")


# ---------------------------------------------------------------------------
# 1. Build the patch
# ---------------------------------------------------------------------------

patch = Patch(zoom=1.0)

vco   = patch.add("Fundamental", "VCO",           pos=[0, 0], FREQ=0.0)
audio = patch.add("Core",        "AudioInterface2", pos=[8, 0])

patch.connect(vco.SQR, audio.i.IN_L, color=COLORS["yellow"])
patch.connect(vco.SQR, audio.i.IN_R, color=COLORS["yellow"])

patch.save(OUT_PATH)
print()

# ---------------------------------------------------------------------------
# 2. Prove: existence then reachability
# ---------------------------------------------------------------------------

graph = PatchLoader.load(OUT_PATH)
print(graph.report())
print()

assert graph.patch_proven, (
    f"FAIL\n"
    f"  missing:        {graph.missing_modules()}\n"
    f"  audio_reachable:{graph.audio_reachable}\n"
    f"  control_gaps:   {graph.control_gaps}"
)

print("All assertions passed.")
print(f'\n  open -a "VCV Rack 2 Free" "{OUT_PATH}"')
