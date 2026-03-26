"""
Patch analyzer: loads a .vcv file and traces the signal path,
flagging broken connections, dead ends, and potential issues.
"""

import io, json, tarfile, sys, os
from collections import defaultdict
import zstandard


def load_vcv(path):
    with open(path, "rb") as f:
        data = f.read()
    dctx = zstandard.ZstdDecompressor()
    tar_bytes = dctx.decompress(data, max_output_size=64 * 1024 * 1024)
    with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as tar:
        for name in tar.getnames():
            if name.endswith("patch.json"):
                return json.loads(tar.extractfile(name).read())


def analyze(path):
    patch = load_vcv(path)
    modules = {m["id"]: m for m in patch["modules"]}
    cables  = patch["cables"]

    def name(mod_id):
        m = modules.get(mod_id, {})
        return f"{m.get('plugin','?')}/{m.get('model','?')}"

    # Build adjacency: who feeds whom
    # outputs_of[mod_id] = list of (out_port, dst_mod_id, dst_port)
    # inputs_of[mod_id]  = list of (in_port, src_mod_id, src_port)
    outputs_of = defaultdict(list)
    inputs_of  = defaultdict(list)

    for c in cables:
        src, sp, dst, dp = c["outputModuleId"], c["outputId"], c["inputModuleId"], c["inputId"]
        outputs_of[src].append((sp, dst, dp))
        inputs_of[dst].append((dp, src, sp))

    # -----------------------------------------------------------------------
    # 1. Find audio output module
    # -----------------------------------------------------------------------
    audio_mods = [m for m in patch["modules"] if m["model"] in ("AudioInterface2", "Audio2", "Audio8", "Audio16")]
    print("=" * 60)
    print(f"PATCH: {os.path.basename(path)}")
    print(f"  {len(patch['modules'])} modules, {len(cables)} cables")
    print("=" * 60)

    if not audio_mods:
        print("ERROR: No audio output module found!")
        return

    # -----------------------------------------------------------------------
    # 2. Trace backwards from audio output
    # -----------------------------------------------------------------------
    print("\n-- SIGNAL PATH (backwards from audio output) --\n")

    def trace_back(mod_id, port, depth=0, visited=None):
        if visited is None:
            visited = set()
        indent = "  " * depth
        mod_name = name(mod_id)

        sources = [(sp, src, dp) for (dp, src, sp) in inputs_of[mod_id] if dp == port]

        if not sources:
            print(f"{indent}[in {port}] ← NOTHING CONNECTED  ← {mod_name}")
            return False

        all_ok = True
        for (src_port, src_id, _) in sources:
            src_name = name(src_id)
            print(f"{indent}[in {port}] ← {src_name}[out {src_port}]")

            key = (src_id, src_port)
            if key in visited:
                print(f"{indent}  (already traced)")
                continue
            visited.add(key)

            # Recurse into that module's inputs
            src_mod = modules.get(src_id, {})
            n_inputs = max((dp for (dp, _, _) in inputs_of[src_id]), default=-1) + 1
            if n_inputs == 0:
                # Source module has no inputs (e.g. LFO, Clock, Noise) -- that's fine
                pass
            else:
                # Check all inputs of source module
                connected_inputs = {dp for (dp, _, _) in inputs_of[src_id]}
                for i in range(n_inputs):
                    if i not in connected_inputs:
                        pass  # not every input needs to be connected
                    else:
                        ok = trace_back(src_id, i, depth + 1, visited)
                        all_ok = all_ok and ok
        return all_ok

    for audio in audio_mods:
        print(f"AUDIO OUTPUT: {name(audio['id'])}")
        # Typical audio inputs: 0=L, 1=R
        connected = {dp for (dp, _, _) in inputs_of[audio["id"]]}
        if not connected:
            print("  ERROR: Nothing connected to audio output!")
        for port in sorted(connected):
            trace_back(audio["id"], port)
        print()

    # -----------------------------------------------------------------------
    # 3. Modules with no outputs connected (dead ends / orphans)
    # -----------------------------------------------------------------------
    print("\n-- ORPHANED MODULES (no outputs connected) --\n")
    orphans = []
    for m in patch["modules"]:
        mid = m["id"]
        if not outputs_of[mid]:
            # Skip purely visual/utility modules
            if m["model"] not in ("Notes", "Blank", "Label", "CableColourKey", "Purfenator",
                                   "SpectrumAnalyzer", "Scope", "Viz"):
                orphans.append(m)
    if orphans:
        for m in orphans:
            print(f"  {name(m['id'])} -- no outputs patched")
    else:
        print("  None")

    # -----------------------------------------------------------------------
    # 4. Params that look like they might be at zero/minimum
    # -----------------------------------------------------------------------
    print("\n-- SUSPICIOUS PARAMS (value = 0 on key modules) --\n")
    key_param_names = {"LEVEL", "VOLUME", "MASTER", "GAIN", "MIX", "WET", "AMOUNT"}
    for m in patch["modules"]:
        for p in m.get("params", []):
            if p["value"] == 0.0:
                # Heuristic: flag id 0 (often master level) at 0
                if p["id"] == 0 and m["model"] in ("AudioInterface2", "Bogaudio-Mix8",
                                                     "Bogaudio-Mix4", "Bogaudio-Pressor"):
                    print(f"  {name(m['id'])} param[{p['id']}] = 0.0  (may be muted)")

    print("\n-- DONE --\n")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "patches/Dub Tech 4 ARM64.vcv"
    analyze(path)
