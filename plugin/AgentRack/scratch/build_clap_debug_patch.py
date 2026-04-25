from __future__ import annotations

import io
import json
import random
import tarfile
from pathlib import Path

import zstandard


RACK_VERSION = "2.6.6"
OUT = Path("/Users/palaitis/Development/vcv-rack/plugin/AgentRack/scratch/clap_debug.vcv")
AUDIO_COLOR = "#ffb437"
GATE_COLOR = "#f44336"


def save_vcv(patch_dict: dict, path: Path) -> None:
    json_bytes = json.dumps(patch_dict, indent=1).encode("utf-8")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:") as tar:
        info = tarfile.TarInfo(name="patch.json")
        info.size = len(json_bytes)
        tar.addfile(info, io.BytesIO(json_bytes))
    compressed = zstandard.ZstdCompressor(level=3).compress(buf.getvalue())
    path.write_bytes(compressed)


def module(plugin: str, model: str, pos: list[int]) -> dict:
    return {
        "id": random.randint(10**14, 10**16),
        "plugin": plugin,
        "model": model,
        "version": RACK_VERSION,
        "params": [],
        "pos": pos,
    }


def cable(output_module_id: int, output_id: int, input_module_id: int, input_id: int, color: str) -> dict:
    return {
        "id": random.randint(10**14, 10**16),
        "outputModuleId": output_module_id,
        "outputId": output_id,
        "inputModuleId": input_module_id,
        "inputId": input_id,
        "color": color,
    }


clock = module("SlimeChild-Substation", "SlimeChild-Substation-Clock", [-12, 1])
clph2 = module("AgentRack", "ClpDbgHits2", [-8, 0])
clpr2 = module("AgentRack", "ClpDbgRom2", [6, 0])
bus = module("AgentRack", "BusCrush", [18, 1])
audio = module("Core", "AudioInterface2", [34, 1])

clock["params"] = [
    {"id": 0, "value": 1.45},
    {"id": 1, "value": 1.0},
    {"id": 2, "value": 16.0},
]

clph2["params"] = [
    {"id": 0, "value": 0.12},
    {"id": 1, "value": 0.40},
    {"id": 2, "value": 0.32},
    {"id": 3, "value": 0.30},
    {"id": 4, "value": 0.20},
    {"id": 5, "value": 0.10},
    {"id": 6, "value": 0.12},
]

clpr2["params"] = [
    {"id": 0, "value": 0.50},
    {"id": 1, "value": 0.42},
    {"id": 2, "value": 0.16},
    {"id": 3, "value": 0.66},
    {"id": 4, "value": 0.00},
    {"id": 5, "value": 0.08},
    {"id": 6, "value": 0.90},
]

patch = {
    "version": RACK_VERSION,
    "zoom": 1.0,
    "gridOffset": [-18.0, 0.0],
    "modules": [clock, clph2, clpr2, bus, audio],
    "cables": [
        cable(clock["id"], 1, clph2["id"], 0, GATE_COLOR),
        cable(clock["id"], 1, clpr2["id"], 0, GATE_COLOR),
        cable(clph2["id"], 0, bus["id"], 0, AUDIO_COLOR),
        cable(clpr2["id"], 0, bus["id"], 1, AUDIO_COLOR),
        cable(bus["id"], 0, audio["id"], 0, AUDIO_COLOR),
        cable(bus["id"], 1, audio["id"], 1, AUDIO_COLOR),
    ],
}

OUT.parent.mkdir(parents=True, exist_ok=True)
save_vcv(patch, OUT)
print(OUT)
