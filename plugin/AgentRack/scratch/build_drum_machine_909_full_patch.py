from __future__ import annotations

import io
import json
import tarfile
from copy import deepcopy
from pathlib import Path

import zstandard


ROOT = Path("/Users/palaitis/Development/vcv-rack/plugin/AgentRack")
SOURCE = ROOT / "scratch" / "rack-autosave-after-sequencer.json"
OUT_JSON = ROOT / "scratch" / "drum_machine_909_full.json"
OUT_VCV = ROOT / "scratch" / "drum_machine_909_full.vcv"

OLD_CLP_ID = 4419646521709571
OLD_RIM_ID = 1998295811694109
RIMCLAP_ID = 2021619775097451

SEQ_ID = 1642650207169221
BUS_ID = 723730360977925
SNR_ID = 9221724743637414
CHH_ID = 8029488123911514


def save_vcv(patch_dict: dict, path: Path) -> None:
    json_bytes = json.dumps(patch_dict, indent=1).encode("utf-8")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:") as tar:
        info = tarfile.TarInfo(name="patch.json")
        info.size = len(json_bytes)
        tar.addfile(info, io.BytesIO(json_bytes))
    compressed = zstandard.ZstdCompressor(level=3).compress(buf.getvalue())
    path.write_bytes(compressed)


def build_patch() -> dict:
    patch = json.loads(SOURCE.read_text())

    modules = []
    for module in patch["modules"]:
        if module["id"] in (OLD_CLP_ID, OLD_RIM_ID):
            continue
        modules.append(deepcopy(module))

    rimclap = {
        "id": RIMCLAP_ID,
        "plugin": "AgentRack",
        "model": "RimClap",
        "version": "2.0.0",
        "params": [
            {"id": 0, "value": 1.0},
            {"id": 1, "value": 1.0},
        ],
        "leftModuleId": SNR_ID,
        "rightModuleId": CHH_ID,
        "pos": [16, 0],
    }
    modules.append(rimclap)

    cables = []
    for cable in patch["cables"]:
        if cable["outputModuleId"] in (OLD_CLP_ID, OLD_RIM_ID):
            continue
        if cable["inputModuleId"] in (OLD_CLP_ID, OLD_RIM_ID):
            continue
        cables.append(deepcopy(cable))

    cables.extend(
        [
            {
                "id": 910001,
                "outputModuleId": SEQ_ID,
                "outputId": 9,
                "inputModuleId": RIMCLAP_ID,
                "inputId": 0,
                "color": "#8b4ade",
            },
            {
                "id": 910002,
                "outputModuleId": SEQ_ID,
                "outputId": 8,
                "inputModuleId": RIMCLAP_ID,
                "inputId": 1,
                "color": "#00b56e",
            },
            {
                "id": 910003,
                "outputModuleId": RIMCLAP_ID,
                "outputId": 0,
                "inputModuleId": BUS_ID,
                "inputId": 2,
                "color": "#ffb437",
            },
            {
                "id": 910004,
                "outputModuleId": RIMCLAP_ID,
                "outputId": 1,
                "inputModuleId": BUS_ID,
                "inputId": 3,
                "color": "#ffb437",
            },
        ]
    )

    patch["modules"] = modules
    patch["cables"] = cables
    patch["path"] = str(OUT_VCV)
    return patch


if __name__ == "__main__":
    patch = build_patch()
    OUT_JSON.write_text(json.dumps(patch, indent=2))
    save_vcv(patch, OUT_VCV)
    print(OUT_VCV)
