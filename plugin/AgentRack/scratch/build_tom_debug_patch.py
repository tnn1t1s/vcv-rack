"""
Build a minimal patch for hand-tuning TomDbg:
    LFO (square @ ~2 Hz) -> TomDbg trig -> AudioInterface2 L+R

Open the resulting .vcv in VCV Rack, then turn TomDbg knobs until it sounds
right. The 17 fit knobs have full ranges; right-click any knob to enter an
exact value. When you're happy, copy the values into TomFit::makeLowTom() etc.

Usage:
    python3 build_tom_debug_patch.py [--out PATH]
"""

from __future__ import annotations

import argparse
import io
import json
import random
import tarfile
from pathlib import Path

import zstandard


RACK_VERSION = "2.6.6"
DEFAULT_OUT = Path(__file__).resolve().parent / "tom_debug.vcv"
GATE_COLOR  = "#f44336"
AUDIO_COLOR = "#ffb437"


def save_vcv(patch_dict: dict, path: Path) -> None:
    json_bytes = json.dumps(patch_dict, indent=1).encode("utf-8")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:") as tar:
        info = tarfile.TarInfo(name="patch.json")
        info.size = len(json_bytes)
        tar.addfile(info, io.BytesIO(json_bytes))
    compressed = zstandard.ZstdCompressor(level=3).compress(buf.getvalue())
    path.write_bytes(compressed)


def module(plugin: str, model: str, pos: list[int], params: list[dict] | None = None) -> dict:
    return {
        "id": random.randint(10**14, 10**16),
        "plugin": plugin,
        "model": model,
        "version": RACK_VERSION,
        "params": params or [],
        "pos": pos,
    }


def cable(out_id: int, out_port: int, in_id: int, in_port: int, color: str) -> dict:
    return {
        "id": random.randint(10**14, 10**16),
        "outputModuleId": out_id,
        "outputId": out_port,
        "inputModuleId": in_id,
        "inputId": in_port,
        "color": color,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    # Fundamental LFO: param 0 = freq (-8..+10 V/oct).
    # Setting param 0 around -1 puts the rate near 1 Hz (slow trigger source).
    lfo = module(
        "Fundamental",
        "LFO",
        pos=[-12, 0],
        params=[{"id": 0, "value": -1.0}],
    )
    tom = module("AgentRack", "TomDbg", pos=[-2, 0])
    audio = module("Core", "AudioInterface2", pos=[28, 0])

    patch = {
        "version": RACK_VERSION,
        "modules": [lfo, tom, audio],
        "cables": [
            # LFO square (output index 3) -> TomDbg TRIG_INPUT (input 0)
            cable(lfo["id"], 3, tom["id"], 0, GATE_COLOR),
            # TomDbg OUT (output 0) -> AudioInterface2 inputs 0 and 1 (L + R)
            cable(tom["id"], 0, audio["id"], 0, AUDIO_COLOR),
            cable(tom["id"], 0, audio["id"], 1, AUDIO_COLOR),
        ],
    }

    save_vcv(patch, args.out)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
