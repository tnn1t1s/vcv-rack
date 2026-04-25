#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = REPO_ROOT / "tests"
VOICE_LAB_REFS = REPO_ROOT / "voice_lab" / "references" / "909.json"
OUT_DIR = Path(__file__).resolve().parent / "snr_batch_100"
RENDER_BIN = TESTS_DIR / "build" / "ar-render"
RACK_SDK = REPO_ROOT.parent.parent / "vendor" / "rack-sdk"
FRAMES = 16384

# This first RLHF-style batch focuses only on the two body oscillators around the
# ear-discovered basin and the currently fitted point. The rest of the snare fit
# stays fixed so user feedback is attributable to the body-core pitch region.
OSC1_VALUES = [141.169754 + 5.0 * i for i in range(10)]
OSC2_VALUES = [307.964081 + 5.0 * i for i in range(10)]


def load_reference_path() -> Path:
    refs = json.loads(VOICE_LAB_REFS.read_text(encoding="utf-8"))
    return Path(refs["snr"]["default"]).expanduser()


def build_variant_id(row: int, col: int) -> str:
    return f"snr-r{row + 1:02d}-c{col + 1:02d}"


def render_variant(out_path: Path, osc1_hz: float, osc2_hz: float) -> None:
    cmd = [
        str(RENDER_BIN),
        "--voice",
        "snr",
        "--frames",
        str(FRAMES),
        "--param",
        "tune=0.5",
        "--param",
        "tone=1.0",
        "--param",
        "snappy=1.0",
        "--param",
        f"fit_osc1_base_hz={osc1_hz:.6f}",
        "--param",
        f"fit_osc2_base_hz={osc2_hz:.6f}",
        "--wav",
        str(out_path),
    ]
    env = dict(os.environ)
    env["DYLD_LIBRARY_PATH"] = str(RACK_SDK)
    subprocess.run(
        cmd,
        cwd=TESTS_DIR,
        env=env,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def main() -> None:
    reference_path = load_reference_path()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(reference_path, OUT_DIR / "reference.wav")

    variants = []
    index = 0
    for row, osc1_hz in enumerate(OSC1_VALUES):
        for col, osc2_hz in enumerate(OSC2_VALUES):
            index += 1
            variant_id = build_variant_id(row, col)
            wav_name = f"{variant_id}.wav"
            render_variant(OUT_DIR / wav_name, osc1_hz, osc2_hz)
            variants.append(
                {
                    "index": index,
                    "id": variant_id,
                    "label": f"Variant {index:03d}",
                    "wav": wav_name,
                    "params": {
                        "fit_osc1_base_hz": round(osc1_hz, 6),
                        "fit_osc2_base_hz": round(osc2_hz, 6),
                    },
                    "grid": {
                        "row": row,
                        "col": col,
                    },
                }
            )

    manifest = {
        "batch_id": "snr-batch-100-v1",
        "title": "Snare RLHF Batch 100",
        "description": "100 fixed-control snare variants over a 10x10 osc1/osc2 body-core grid.",
        "reference": "reference.wav",
        "frames": FRAMES,
        "conditioning": {
            "tune": 0.5,
            "tone": 1.0,
            "snappy": 1.0,
        },
        "grid_axes": {
            "osc1_hz": OSC1_VALUES,
            "osc2_hz": OSC2_VALUES,
        },
        "variants": variants,
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(str(OUT_DIR))


if __name__ == "__main__":
    main()
