"""
Build a small patch to audition the combined `Toms` module:
    LFO (square ~1 Hz) -> Toms LOW trig
    LFO inverted        -> Toms MID trig (offset, fires opposite)
    [HIGH trig left unconnected; you can patch in Rack]
    Toms LOW out  -> AudioInterface2 left
    Toms MID out  -> AudioInterface2 right
    Toms HIGH out -> available, patch by hand if you want

You'll hear LOW + MID alternating. Add a clock/seq from inside Rack to drive
HIGH or rewire as you like. The point is to hear the three calibrated voices
at their factory baseHz (85.7 / 107.3 / 126.3).
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
DEFAULT_OUT  = Path(__file__).resolve().parent / "toms_kit.vcv"
GATE_COLOR   = "#f44336"
AUDIO_COLOR  = "#ffb437"


def save_vcv(patch: dict, path: Path) -> None:
    json_bytes = json.dumps(patch, indent=1).encode("utf-8")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:") as tar:
        info = tarfile.TarInfo(name="patch.json"); info.size = len(json_bytes)
        tar.addfile(info, io.BytesIO(json_bytes))
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

    lfo   = module("Fundamental", "LFO", pos=[-12, 0],
                   params=[{"id": 0, "value": -1.5}])
    toms  = module("AgentRack",   "Toms",            pos=[-2, 0])
    audio = module("Core",        "AudioInterface2", pos=[14, 0])

    patch = {
        "version": RACK_VERSION,
        "modules": [lfo, toms, audio],
        "cables": [
            # LFO output 3 = square; LFO output 4 = square inverted
            cable(lfo["id"], 3, toms["id"], 0, GATE_COLOR),  # LOW trig
            cable(lfo["id"], 4, toms["id"], 1, GATE_COLOR),  # MID trig
            # toms outputs to stereo
            cable(toms["id"], 0, audio["id"], 0, AUDIO_COLOR),  # LOW -> L
            cable(toms["id"], 1, audio["id"], 1, AUDIO_COLOR),  # MID -> R
        ],
    }

    save_vcv(patch, args.out)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
