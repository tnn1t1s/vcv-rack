"""
Probe patch for Hora drumsequencer outputs.

Goal: confirm whether (a) per-track gate outputs emit variable amplitude
based on the per-step CV_out_level field, and (b) what the unused output
indices 0-3 carry (suspected: clock-thru, accent, reset, EOC).

Layout:
    SlimeChild Clock       -> Hora Drumsequencer (clock at IN[2])
    Hora out 0             -> Scope A IN1
    Hora out 1             -> Scope A IN2
    Hora out 2             -> Scope B IN1
    Hora out 3             -> Scope B IN2
    Hora out 4 (BD track)  -> Scope C IN1
    Hora out 5 (SD track)  -> Scope C IN2
    Hora out 13 (CH track) -> Scope D IN1
    Hora out 14 (OH track) -> Scope D IN2

How to use:
    1. Open the patch.
    2. Click some steps on Hora's track 1 (kick) -- mix accented and normal
       steps via right-click on a step or whatever Hora's velocity edit
       affordance is.
    3. Watch Scope C's left trace: if step amplitudes vary, CV_out_level
       drives gate voltage -> Model A works directly.
    4. Watch Scopes A and B: if any of outputs 0-3 emit something during
       playback, that's our candidate for the global Total Accent / clock
       / reset signal. Note which index does what.

Usage:
    python3 build_hora_probe_patch.py
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
DEFAULT_OUT  = Path(__file__).resolve().parent / "hora_probe.vcv"
GATE_COLOR   = "#f44336"
CV_COLOR     = "#ffb437"
CLOCK_COLOR  = "#4f99ff"


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

    clock = module("SlimeChild-Substation", "SlimeChild-Substation-Clock", pos=[-22, 0])
    hora  = module("Hora-Sequencers",       "Drumsequencer",               pos=[-15, 0])

    # Four Fundamental Scopes; each shows 2 traces. Layout below the seq.
    scope_a = module("Fundamental", "Scope", pos=[-22, 1])  # outs 0 + 1
    scope_b = module("Fundamental", "Scope", pos=[-9, 1])   # outs 2 + 3
    scope_c = module("Fundamental", "Scope", pos=[ 4, 1])   # outs 4 (BD) + 5 (SD)
    scope_d = module("Fundamental", "Scope", pos=[17, 1])   # outs 13 (CH) + 14 (OH)

    # Fundamental Scope input port indices: 0 = X (CHAN 1), 1 = Y (CHAN 2).
    # Fundamental Scope external trigger input is index 2 (unused here).

    patch = {
        "version": RACK_VERSION,
        "modules": [clock, hora, scope_a, scope_b, scope_c, scope_d],
        "cables": [
            # Clock to sequencer
            cable(clock["id"], 1, hora["id"], 2, CLOCK_COLOR),

            # Outputs 0..3 (unknown role) -> Scopes A and B
            cable(hora["id"], 0, scope_a["id"], 0, CV_COLOR),
            cable(hora["id"], 1, scope_a["id"], 1, CV_COLOR),
            cable(hora["id"], 2, scope_b["id"], 0, CV_COLOR),
            cable(hora["id"], 3, scope_b["id"], 1, CV_COLOR),

            # Track outputs (BD, SD) -> Scope C, to test per-step amplitude
            cable(hora["id"], 4, scope_c["id"], 0, GATE_COLOR),
            cable(hora["id"], 5, scope_c["id"], 1, GATE_COLOR),

            # CH, OH -> Scope D, second amplitude verification point
            cable(hora["id"], 13, scope_d["id"], 0, GATE_COLOR),
            cable(hora["id"], 14, scope_d["id"], 1, GATE_COLOR),
        ],
    }

    save_vcv(patch, args.out)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
