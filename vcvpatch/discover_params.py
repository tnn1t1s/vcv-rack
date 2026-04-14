"""
Discovers the actual param IDs for a VCV Rack module by:
  1. Creating a minimal patch containing only that module
  2. Opening VCV Rack (which auto-saves on load)
  3. Waiting for the autosave to be written
  4. Reading the autosave to get all param IDs and their default values

This is runtime introspection via VCV Rack's own serialization --
no source code parsing, no user interaction.

Usage:
    uv run python -m vcvpatch.discover_params Fundamental VCO
    uv run python -m vcvpatch.discover_params Fundamental LFO
"""

import json
import os
import sys
import time

from vcvpatch.serialize import save_vcv, load_vcv

AUTOSAVE = os.path.expanduser(
    "~/Library/Application Support/Rack2/autosave/patch.json"
)
TMP_PATCH = "/tmp/vcv_discover.vcv"


def discover(plugin: str, model: str) -> list[dict]:
    # Build a minimal patch with just this module
    patch = {
        "version": "2.6.6",
        "zoom": 1.0,
        "gridOffset": [0.0, 0.0],
        "modules": [{
            "id": 1,
            "plugin": plugin,
            "model": model,
            "version": "2.6.6",
            "params": [],
            "pos": [0, 0],
        }],
        "cables": [],
    }
    save_vcv(patch, TMP_PATCH)

    # Note the autosave mtime before opening
    before = os.path.getmtime(AUTOSAVE) if os.path.exists(AUTOSAVE) else 0

    os.system(f'open -a "VCV Rack 2 Free" "{TMP_PATCH}"')

    # Wait until VCV Rack rewrites the autosave AND it contains our module
    print(f"Waiting for VCV Rack to load {plugin}/{model}...", end="", flush=True)
    for _ in range(60):   # up to 30 seconds
        time.sleep(0.5)
        if not os.path.exists(AUTOSAVE):
            print(".", end="", flush=True)
            continue
        mtime = os.path.getmtime(AUTOSAVE)
        if mtime <= before:
            print(".", end="", flush=True)
            continue
        # File updated -- check it contains our module
        try:
            with open(AUTOSAVE) as f:
                saved = json.load(f)
            if any(m.get("plugin") == plugin and m.get("model") == model
                   for m in saved.get("modules", [])):
                break
        except json.JSONDecodeError:
            pass
        print(".", end="", flush=True)
    print()

    # Read autosave
    with open(AUTOSAVE) as f:
        saved = json.load(f)

    for mod in saved.get("modules", []):
        if mod.get("plugin") == plugin and mod.get("model") == model:
            params = sorted(mod.get("params", []), key=lambda p: p["id"])
            return params

    return []


if __name__ == "__main__":
    plugin = sys.argv[1] if len(sys.argv) > 1 else "Fundamental"
    model  = sys.argv[2] if len(sys.argv) > 2 else "VCO"

    print(f"\nDiscovering params for {plugin}/{model}\n")
    params = discover(plugin, model)

    if not params:
        print("No params found -- module may not have loaded.")
        sys.exit(1)

    print(f"{'ID':>4}  {'Default value':>14}  name (to be filled manually)")
    print("-" * 50)
    for p in params:
        print(f"{p['id']:>4}  {p['value']:>14.6f}")

    print(f"\n{len(params)} params total.")
