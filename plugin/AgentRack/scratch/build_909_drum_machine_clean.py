"""
Clean 909 drum machine patch (verified port mapping):

    SlimeChild Clock OUT[1]  -> Drumsequencer IN[2]   (clock)

    Drumsequencer track gate outputs (verified from rack-autosave):
        OUT[4]  -> Kck         (BD, track 1)
        OUT[5]  -> Snr         (SD, track 2)
        OUT[6]  -> Toms LOW    (LT, track 3)
        OUT[7]  -> Toms MID    (MT, track 4)
        OUT[8]  -> Toms HIGH   (HT, track 5)
        OUT[9]  -> RimClap CLAP (CP, track 6)
        OUT[13] -> Chh         (CH, track 10)
        OUT[14] -> Ohh         (OH, track 11)

    Voice audio outs -> BusCrush 8 channels (0..7), stereo out -> AudioInterface2.

Layout matches scratch/rack-autosave-after-sequencer.json structure:
    y=0 row: voices left to right
    y=1 row: clock + sequencer + mixer + audio interface

Open in Rack, click drumsequencer steps to program patterns, hit play.

Usage:
    python3 build_909_drum_machine_clean.py
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
DEFAULT_OUT  = Path(__file__).resolve().parent / "drum_machine_909_clean.vcv"
GATE_COLOR   = "#f44336"
AUDIO_COLOR  = "#ffb437"
CLOCK_COLOR  = "#4f99ff"


def save_vcv(patch: dict, path: Path) -> None:
    payload = json.dumps(patch, indent=1).encode("utf-8")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:") as tar:
        info = tarfile.TarInfo(name="patch.json"); info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))
    path.write_bytes(zstandard.ZstdCompressor(level=3).compress(buf.getvalue()))


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
        "outputModuleId": out_id, "outputId": out_port,
        "inputModuleId":  in_id,  "inputId":  in_port,
        "color": color,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    # ── Voices on top row (y=0), spaced 13 HP apart (12 HP voice + 1 HP gap) ──
    kck     = module("AgentRack", "Kck",     pos=[-16, 0])
    snr     = module("AgentRack", "Snr",     pos=[ -3, 0])
    toms    = module("AgentRack", "Toms",    pos=[ 10, 0])
    chh     = module("AgentRack", "Chh",     pos=[ 23, 0])
    ohh     = module("AgentRack", "Ohh",     pos=[ 36, 0])
    rimclap = module("AgentRack", "RimClap", pos=[ 49, 0])

    # ── Control + mix on bottom row (y=1) matching the autosave geometry ──
    clock   = module("SlimeChild-Substation", "SlimeChild-Substation-Clock", pos=[-15, 1])
    drumseq = module("Hora-Sequencers",       "Drumsequencer",               pos=[ -8, 1])
    bus     = module("AgentRack",             "BusCrush",                    pos=[ 36, 1])
    audio   = module("Core",                  "AudioInterface2",             pos=[ 60, 1])

    cables = [
        # ── clock ────────────────────────────────────────────────────────────
        cable(clock["id"], 1, drumseq["id"], 2, CLOCK_COLOR),

        # ── triggers (verified output indices from rack-autosave) ────────────
        cable(drumseq["id"],  4, kck["id"],     0, GATE_COLOR),  # BD -> Kck
        cable(drumseq["id"],  5, snr["id"],     0, GATE_COLOR),  # SD -> Snr
        cable(drumseq["id"],  6, toms["id"],    0, GATE_COLOR),  # LT -> Toms LOW
        cable(drumseq["id"],  7, toms["id"],    1, GATE_COLOR),  # MT -> Toms MID
        cable(drumseq["id"],  8, toms["id"],    2, GATE_COLOR),  # HT -> Toms HIGH
        cable(drumseq["id"],  9, rimclap["id"], 0, GATE_COLOR),  # CP -> Clap
        cable(drumseq["id"], 13, chh["id"],     0, GATE_COLOR),  # CH -> Chh
        cable(drumseq["id"], 14, ohh["id"],     0, GATE_COLOR),  # OH -> Ohh

        # ── voice audio into BusCrush channels 0..7 ─────────────────────────
        cable(kck["id"],     0, bus["id"], 0, AUDIO_COLOR),
        cable(snr["id"],     0, bus["id"], 1, AUDIO_COLOR),
        cable(toms["id"],    0, bus["id"], 2, AUDIO_COLOR),  # Toms LOW out
        cable(toms["id"],    1, bus["id"], 3, AUDIO_COLOR),  # Toms MID out
        cable(toms["id"],    2, bus["id"], 4, AUDIO_COLOR),  # Toms HIGH out
        cable(rimclap["id"], 0, bus["id"], 5, AUDIO_COLOR),  # Clap out
        cable(chh["id"],     0, bus["id"], 6, AUDIO_COLOR),
        cable(ohh["id"],     0, bus["id"], 7, AUDIO_COLOR),

        # ── stereo bus to audio interface ────────────────────────────────────
        cable(bus["id"], 0, audio["id"], 0, AUDIO_COLOR),
        cable(bus["id"], 1, audio["id"], 1, AUDIO_COLOR),
    ]

    patch = {
        "version": RACK_VERSION,
        "modules": [kck, snr, toms, chh, ohh, rimclap, clock, drumseq, bus, audio],
        "cables": cables,
    }

    save_vcv(patch, args.out)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
