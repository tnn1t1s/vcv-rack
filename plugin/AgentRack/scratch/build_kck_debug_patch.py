"""
Hand-tuning patch for KckDbg:
    LFO (square @ ~1 Hz) -> KckDbg trig -> AudioInterface2 L+R

Open the resulting .vcv in VCV Rack, then turn KckDbg knobs until it sounds
right. Defaults in KckDbg match the current v8 KckFit::Config (calibrated
against TR-909 BD reference). Right-click any knob to enter exact values.

When you're happy, send me the values you converged on and I'll fold them
into KckFit::makeKick().

Usage:
    python3 build_kck_debug_patch.py
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
DEFAULT_OUT  = Path(__file__).resolve().parent / "kck_debug.vcv"
GATE_COLOR   = "#f44336"
AUDIO_COLOR  = "#ffb437"


def save_vcv(patch: dict, path: Path) -> None:
    payload = json.dumps(patch, indent=1).encode("utf-8")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:") as tar:
        info = tarfile.TarInfo(name="patch.json"); info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))
    path.write_bytes(zstandard.ZstdCompressor(level=3).compress(buf.getvalue()))


def module(plugin: str, model: str, pos: list[int], params=None) -> dict:
    return {
        "id": random.randint(10**14, 10**16),
        "plugin": plugin, "model": model, "version": RACK_VERSION,
        "params": params or [], "pos": pos,
    }


def cable(out_id: int, out_port: int, in_id: int, in_port: int, color: str) -> dict:
    return {
        "id": random.randint(10**14, 10**16),
        "outputModuleId": out_id, "outputId": out_port,
        "inputModuleId":  in_id,  "inputId":  in_port,
        "color": color,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    lfo   = module("Fundamental",     "LFO",             pos=[-12, 0],
                   params=[{"id": 0, "value": -1.0}])  # ~1 Hz square
    kck   = module("AgentRack",       "KckDbg",          pos=[ -2, 0])
    audio = module("Core",            "AudioInterface2", pos=[ 30, 0])

    patch = {
        "version": RACK_VERSION,
        "modules": [lfo, kck, audio],
        "cables": [
            cable(lfo["id"], 3, kck["id"],   0, GATE_COLOR),
            cable(kck["id"], 0, audio["id"], 0, AUDIO_COLOR),
            cable(kck["id"], 0, audio["id"], 1, AUDIO_COLOR),
        ],
    }

    save_vcv(patch, args.out)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
