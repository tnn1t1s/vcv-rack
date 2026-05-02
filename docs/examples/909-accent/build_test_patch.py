"""
TR-909 accent calibration patches for Kck.

Generates one or more reproducible .vcv patches that exercise the
accent paths on Kck with the AgentRack 909 controller, for ear-tuning
the per-case dB targets defined in src/Tr909Bus.hpp::AccentMix.

Architecture (matches plugin/AgentRack/src/Tr909Bus.hpp):
    - Per-step accent events travel via CABLES (deterministic, zero
      latency): TRIG, LOCAL_ACC (Accent B), TOTAL_ACC (Accent A).
    - Tr909Ctrl broadcasts slow-changing state via the expander bus:
      DEFAULT (ghost amount), ACCENT A, ACCENT B, MASTER VOL.
    - Tr909Ctrl is NOT in the trigger path; the sequencer wires
      directly to each voice's cable inputs.

Layout (two rows):
    Row 0: SlimeChild Clock | Hora Drumsequencer
    Row 1: Tr909Ctrl | Kck | AudioInterface2

Tr909Ctrl knobs (each scales one of the four accent cases):
    DEFAULT   -> ghost (no rail fired)
    ACCENT A  -> A-only and A's contribution to both
    ACCENT B  -> B-only and B's contribution to both
    MASTER    -> post-everything output volume

Sweep DEFAULT to set the no-accent floor; sweep ACC A / ACC B to
calibrate each rail; verify the four levels by ear (or with peak
metering) match the per-voice ghostDb / globalDb / localDb / bothDb
targets.

Variants:
    basic     -- 4-on-floor BD only, no accent rails wired. Simplest;
                 every hit is a ghost-case hit, so DEFAULT alone scales
                 the kick.
    accent_a  -- 4-on-floor BD + Accent A on every other hit. Cleanly
                 alternates ghost vs A-only; good for calibrating the
                 A-vs-default relationship.
    dense     -- 16th-note kicks + Accent A every 4th + Accent B every
                 4th. Exercises all four cases (ghost / A / B / both)
                 in one bar. Note: at low DEFAULT the ghost notes
                 become click-prominent (uniform attenuation reveals
                 the click transient); use the simpler variants for
                 quiet-floor calibration.

Usage:
    python3 docs/examples/909-accent/build_test_patch.py --variant basic
    python3 docs/examples/909-accent/build_test_patch.py --all

Output filenames default to `kck_<variant>_test.vcv` next to this script.
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
GATE_COLOR   = "#f44336"
ACCENT_COLOR = "#ff9800"
AUDIO_COLOR  = "#ffb437"
CLOCK_COLOR  = "#4f99ff"


def save_vcv(patch: dict, path: Path) -> None:
    payload = json.dumps(patch, indent=1).encode("utf-8")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:") as tar:
        info = tarfile.TarInfo(name="patch.json"); info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))
    path.write_bytes(zstandard.ZstdCompressor(level=3).compress(buf.getvalue()))


def module(plugin: str, model: str, pos: list[int],
           params=None, data=None) -> dict:
    out = {
        "id": random.randint(10**14, 10**16),
        "plugin": plugin, "model": model, "version": RACK_VERSION,
        "params": params or [], "pos": pos,
    }
    if data is not None:
        out["data"] = data
    return out


def cable(out_id: int, out_port: int, in_id: int, in_port: int, color: str) -> dict:
    return {
        "id": random.randint(10**14, 10**16),
        "outputModuleId": out_id, "outputId": out_port,
        "inputModuleId":  in_id,  "inputId":  in_port,
        "color": color,
    }


def hora_data(bd_steps, acc_steps, local_steps) -> dict:
    """Build Hora data with the given gate patterns per track.

    `gate run: 0` is the AUTO-RUN mode (counter-intuitive but verified
    against working autosaves in scratch/). `gate run: 1` would tell Hora
    to wait for an external RUN gate, which we don't supply.

    Track <-> output mapping (1-indexed for Hora gates arrays, 0-indexed
    for autosave outputs):
      - gates1P1 -> output 3 (ACC, "#4 output" in UI) -- Total Accent
      - gates2P1 -> output 4 (BD)                     -- kick trigger
      - gates3P1 -> output 5 (SD)                     -- used here for
        Local Accent because it's the next available gate output
    """
    d = {}
    def gates(steps):
        a = [0] * 32
        for i in steps: a[i] = 1
        return a
    d["gates1P1"] = gates(acc_steps)
    d["gates2P1"] = gates(bd_steps)
    d["gates3P1"] = gates(local_steps)
    for trk in range(4, 13):
        d[f"gates{trk}P1"] = [0] * 32
    d["Direct Clock"] = 0
    d["auto reset"]   = 0
    d["gate run"]     = 0
    d["runningSeq"]   = True
    return d


# --- Variants -------------------------------------------------------------
# Each variant is a (description, BD steps, ACC-A steps, ACC-B steps,
# wire_local_acc) tuple. wire_local_acc=False means no LOCAL_ACC cable
# in the patch (cleaner for variants that only need ghost vs A-only).
VARIANTS = {
    "basic": (
        "Plain 4-on-floor kick. No accent rails wired -- every hit is a "
        "ghost-case hit. Use to calibrate DEFAULT knob and per-voice ghostDb.",
        [0, 4, 8, 12], [], [], False,
    ),
    "accent_a": (
        "4-on-floor kick + Accent A on every other hit (steps 0, 8). Use to "
        "calibrate ACC A vs DEFAULT relationship: alternating loud/quiet.",
        [0, 4, 8, 12], [0, 8], [], False,
    ),
    "dense": (
        "16th-note kicks + Accent A on every 4th step + Accent B on every "
        "4th step. Exercises ghost / A-only / B-only / both cases. Watch "
        "out: dense pattern, ghost notes can sound clicky at low DEFAULT.",
        list(range(16)), [0, 4, 8, 12], [0, 4, 8, 12], True,
    ),
}


# Hora baseline params -- copied verbatim from a known-working autosave
# (scratch/drum_machine_909_full.json). Without these Hora instantiates
# cold with critical mode/length/track params at 0 and silently sits idle.
HORA_BASELINE_PARAMS = [
    (0,    2.0),    # mode/select
    (2,  120.0),    # BPM display
    (5,   32.0),    # step length
    (6,    1.0),
    (7,    2.0),
    (8,    2.0),
    # ids 111..142 are per-track default multipliers; all 1.0.
    *[(i, 1.0) for i in range(111, 143)],
]


def hora_params() -> list:
    return [{"id": pid, "value": float(v)} for pid, v in HORA_BASELINE_PARAMS]


def build_patch(bd_steps, acc_a_steps, acc_b_steps, wire_local) -> dict:
    clock = module("SlimeChild-Substation", "SlimeChild-Substation-Clock",
                   pos=[-22, 0],
                   params=[{"id": 0, "value": 1.0},   # TEMPO=1 -> 120 BPM
                           {"id": 1, "value": 1.0},   # RUN=1
                           {"id": 2, "value": 4.0}])  # MULT=4 (16ths)
    hora  = module("Hora-Sequencers", "Drumsequencer",
                   pos=[-15, 0],
                   params=hora_params(),
                   data=hora_data(bd_steps, acc_a_steps, acc_b_steps))

    # Row 1: controller + kick + audio (Tr909Ctrl adjacent to Kck for bus chain)
    ctrl  = module("AgentRack", "Tr909Ctrl", pos=[-22, 1])
    kck   = module("AgentRack", "Kck",       pos=[-18, 1])
    audio = module("Core",      "AudioInterface2", pos=[ -6, 1])

    # Kck input ids (must match enum in src/Kck.cpp):
    KCK_TRIG       = 0
    KCK_LOCAL_ACC  = 8
    KCK_TOTAL_ACC  = 9

    cables = [
        # Clock MULT (out 1, x4 for 16ths) -> Hora CLOCK (in 2)
        cable(clock["id"], 1, hora["id"],  2, CLOCK_COLOR),
        # Hora BD (out 4) -> Kck TRIG
        cable(hora["id"],  4, kck["id"],   KCK_TRIG, GATE_COLOR),
        # Kck OUT -> Audio L + R
        cable(kck["id"],   0, audio["id"], 0, AUDIO_COLOR),
        cable(kck["id"],   0, audio["id"], 1, AUDIO_COLOR),
    ]
    if acc_a_steps:
        # Hora ACC (out 3) -> Kck TOTAL_ACC
        cables.append(cable(hora["id"], 3, kck["id"], KCK_TOTAL_ACC, ACCENT_COLOR))
    if wire_local and acc_b_steps:
        # Hora SD-track (out 5) used as Local Accent source -> Kck LOCAL_ACC
        cables.append(cable(hora["id"], 5, kck["id"], KCK_LOCAL_ACC, ACCENT_COLOR))

    return {
        "version": RACK_VERSION,
        "modules": [clock, hora, ctrl, kck, audio],
        "cables":  cables,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", choices=list(VARIANTS.keys()), default="dense")
    ap.add_argument("--out", type=Path, default=None,
                    help="Output path. Defaults to scratch/kck_<variant>_test.vcv.")
    ap.add_argument("--all", action="store_true",
                    help="Render every variant (overrides --variant).")
    args = ap.parse_args()

    targets = list(VARIANTS.keys()) if args.all else [args.variant]
    for variant in targets:
        desc, bd, accA, accB, wireLocal = VARIANTS[variant]
        patch = build_patch(bd, accA, accB, wireLocal)
        out_path = args.out if (args.out and not args.all) \
                   else Path(__file__).resolve().parent / f"kck_{variant}_test.vcv"
        save_vcv(patch, out_path)
        print(f"wrote {out_path}")
        print(f"  -> {desc}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
