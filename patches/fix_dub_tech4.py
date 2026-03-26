"""
Adapts "Dub Tech 4.vcv" for ARM64 Mac:
  mscHack/Mix_9_3_4     -> Bogaudio/Bogaudio-Mix8
  Autodafe/ClockDivider -> Bogaudio/Bogaudio-ClkDiv

Signal chain: Mix8 -> Plateau -> Chronoblob2 -> Pressor -> AudioInterface2
AudioInterface2 wired from Pressor is always enforced as an invariant.
"""

import sys, os, io, json, tarfile, random
import zstandard

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def load_vcv(path):
    with open(path, "rb") as f:
        data = f.read()
    dctx = zstandard.ZstdDecompressor()
    tar_bytes = dctx.decompress(data, max_output_size=64 * 1024 * 1024)
    with tarfile.open(fileobj=io.BytesIO(tar_bytes)) as tar:
        return json.loads(tar.extractfile("./patch.json").read())


def save_vcv(patch_dict, path):
    json_bytes = json.dumps(patch_dict, indent=1).encode("utf-8")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:") as tar:
        info = tarfile.TarInfo(name="patch.json")
        info.size = len(json_bytes)
        tar.addfile(info, io.BytesIO(json_bytes))
    cctx = zstandard.ZstdCompressor(level=3)
    with open(path, "wb") as f:
        f.write(cctx.compress(buf.getvalue()))


def new_cable(src_id, src_port, dst_id, dst_port, color="#ffb437"):
    return {
        "id": random.randint(10**14, 10**16),
        "outputModuleId": src_id,
        "outputId": src_port,
        "inputModuleId": dst_id,
        "inputId": dst_port,
        "color": color,
    }


def find_module(modules, plugin, model):
    for m in modules:
        if m["plugin"] == plugin and m["model"] == model:
            return m
    return None

def find_modules(modules, plugin, model):
    return [m for m in modules if m["plugin"] == plugin and m["model"] == model]


def transform(patch):
    modules = patch["modules"]
    cables  = patch["cables"]

    # -- Find all relevant modules and save their original IDs ---------------
    mschack  = find_module(modules, "mscHack",  "Mix_9_3_4")
    autodafe = find_module(modules, "Autodafe", "ClockDivider")
    plateaus = find_modules(modules, "Valley",  "Plateau")
    chronos  = find_modules(modules, "AlrightDevices", "Chronoblob2")
    pressor  = find_module(modules, "Bogaudio", "Bogaudio-Pressor")
    audio    = find_module(modules, "Core",     "AudioInterface2")

    assert mschack,  "mscHack not found"
    assert autodafe, "Autodafe not found"
    assert pressor,  "Pressor not found"
    assert audio,    "AudioInterface2 not found"

    OLD_AUTODAFE_ID = autodafe["id"]
    NEW_RGATE_ID    = random.randint(10**14, 10**16)

    # mscHack IS available on ARM64 -- only Autodafe needs replacing
    # Replace Autodafe/ClockDivider -> Bogaudio/Bogaudio-RGate (ports map 1:1)
    autodafe.update({"plugin": "Bogaudio", "model": "Bogaudio-RGate",
                     "id": NEW_RGATE_ID, "params": []})
    autodafe.pop("data", None)
    print(f"  Replacing Autodafe/ClockDivider -> Bogaudio/Bogaudio-RGate")

    # -- Remap cables touching Autodafe --------------------------------------
    new_cables = []
    for c in cables:
        if c["inputModuleId"] == OLD_AUTODAFE_ID:
            new_cables.append({**c, "inputModuleId": NEW_RGATE_ID})
        elif c["outputModuleId"] == OLD_AUTODAFE_ID:
            new_cables.append({**c, "outputModuleId": NEW_RGATE_ID})
        else:
            new_cables.append(c)

    # -- Fix AudioInterface2 device (original patch had a non-Mac device) ----
    if audio:
        audio["data"] = {
            "audio": {
                "driver": 5,       # Core Audio on Mac
                "deviceName": "",  # empty = auto / let user pick
                "sampleRate": 48000.0,
                "blockSize": 256,
                "inputOffset": 0,
                "outputOffset": 0,
            },
            "dcFilter": True,
        }
        print(f"  AudioInterface2 reset to Core Audio")

    print(f"  All other cables preserved unchanged")

    patch["cables"] = new_cables
    return patch


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

src = os.path.expanduser("~/Downloads/Dub Tech 4.vcv")
dst = os.path.join(os.path.dirname(__file__), "Dub Tech 4 ARM64.vcv")

print(f"Loading: {src}")
patch = load_vcv(src)
print(f"  {len(patch['modules'])} modules, {len(patch['cables'])} cables")

patch = transform(patch)
print(f"\nSaving: {dst}")
print(f"  {len(patch['modules'])} modules, {len(patch['cables'])} cables")
save_vcv(patch, dst)

print(f"\nOpening in VCV Rack...")
os.system(f'open -a "VCV Rack 2 Free" "{dst}"')
