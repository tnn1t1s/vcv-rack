"""
Build a minimal snare debug patch with the repo's public vcvpatch API:
    Fundamental LFO (square) -> AgentRack Snr trigger -> AudioInterface2 L+R

Run:
    .venv/bin/python plugin/AgentRack/scratch/build_snr_lfo_debug_patch.py
"""

from __future__ import annotations

from pathlib import Path

from vcvpatch import CableType, Patch


OUT = Path(__file__).resolve().parent / "snr_lfo_debug.vcv"


patch = Patch(zoom=1.0)

lfo = patch.add(
    "Fundamental",
    "LFO",
    position=[0, 0],
    Frequency=-1.0,
)

snr = patch.add(
    "AgentRack",
    "Snr",
    position=[8, 0],
    Tune=0.5,
    Tone=1.0,
    Snappy=1.0,
    Level=1.0,
)

audio = patch.add(
    "Core",
    "AudioInterface2",
    position=[18, 0],
)

patch.connect(lfo.o.Square, snr.i.Trigger, cable_type=CableType.GATE)
patch.connect(snr.o.Audio, audio.i.Left_input, cable_type=CableType.AUDIO)
patch.connect(snr.o.Audio, audio.i.Right_input, cable_type=CableType.AUDIO)

patch.save(str(OUT))
print(OUT)
