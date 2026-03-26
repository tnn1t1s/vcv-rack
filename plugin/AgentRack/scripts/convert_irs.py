"""
Convert cv313/Echospace IR WAV files to raw interleaved stereo float32
at 44100 Hz for Saphire's IR bank.

Output:
  res/ir/00.f32 .. 49.f32   -- raw stereo float32, max 132300 samples (3s @ 44100)
  src/ir_names.hpp           -- C++ array of short display names

Run from plugin/AgentRack/:
  ../../.venv/bin/python3 scripts/convert_irs.py
"""

import os
import re
import struct
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from math import gcd

SRC_DIR    = "../../research/impulse-response"
OUT_IR_DIR = "res/ir"
OUT_HPP    = "src/ir_names.hpp"
TARGET_SR  = 44100
MAX_SAMP   = 132300  # 3s @ 44100

# Curated selection: 50 weirdest / most interesting IRs from the 100 available.
# Order here becomes the preset index (00–49).
# Format: source file number (as string prefix, e.g. "091")
SELECTION = [
    # ── Non-linear / gated / percussive ──────────────────────────────────────
    "091",   # 00 GATED ATTACK SLAP
    "095",   # 01 SUDDEN DROP NLR
    "096",   # 02 IN THE PAST NLR
    "097",   # 03 RISING NON LINEAR
    "094",   # 04 STEREO REBOUND
    "093",   # 05 3D BACK SLAP
    "092",   # 06 3D STEREO NON LINEAR
    "068",   # 07 GATED BRASS
    "069",   # 08 ORCHESTRA HIT
    "060",   # 09 BITCHIN ECHO
    # ── Weird / unusual sources ───────────────────────────────────────────────
    "100",   # 10 TOTALLY OFF
    "099",   # 11 SQUEAKY BOARDS
    "090",   # 12 BIG FOOT
    "048",   # 13 DEEP BREATHING
    "057",   # 14 ARRON'S ROOM
    "047",   # 15 LONG HI TAIL ECHO
    "070",   # 16 STEREO LUSH GUITAR
    "075",   # 17 STEREO PLATER THAN H
    # ── Modulated / chorus verbs ──────────────────────────────────────────────
    "052",   # 18 STEREO GALACTIC CHORUS VERB
    "053",   # 19 STEREO SYNTH VANISH
    "055",   # 20 CHORUS VERB 1
    "056",   # 21 CHORUS REVERB 2
    # ── 3D spatial ────────────────────────────────────────────────────────────
    "081",   # 22 3D DIMENSIONAL SPACE
    "082",   # 23 3D SPARKLING VERB
    "083",   # 24 3D CORRIDOR
    "015",   # 25 3D SUBTLE STEREO AMBIENCE
    "019",   # 26 3D ROOM AMBIENCE
    "044",   # 27 3D VOX HALL AMBIENCE
    # ── Drum rooms / snare chambers ───────────────────────────────────────────
    "065",   # 28 STEREOCRACK SNARE
    "066",   # 29 STEREO SNARE CHAMBER
    "067",   # 30 STEREO KICK CHAMBER
    "062",   # 31 MIRRORED DRUM ROOM
    "061",   # 32 TIGHT DRUM ROOM 2
    "064",   # 33 ROCK SNARE 1
    # ── Big / extreme spaces ──────────────────────────────────────────────────
    "084",   # 34 WAREHOUSE
    "085",   # 35 MEDIUM WAREHOUSE
    "088",   # 36 STADIUM ANNOUNCE
    "089",   # 37 STADIUM 1
    "076",   # 38 BIG STACK ROOM
    "086",   # 39 BIG CATHEDRAL
    "087",   # 40 DARK CATHEDRAL
    "049",   # 41 HUGE CATHEDRAL
    "050",   # 42 AVE CATHEDRAL
    # ── Unusual plates / rooms ────────────────────────────────────────────────
    "001",   # 43 STEREO 140
    "007",   # 44 BRITE CAVE PLATE
    "010",   # 45 70 RICH PLATE
    "071",   # 46 140 PLATE 5
    "023",   # 47 NICE ROOM SIZZLE
    "063",   # 48 MEDIUM + STAGE
    "098",   # 49 SMALL CLEAR ROOM
]

assert len(SELECTION) == 50, f"Selection must be 50 items, got {len(SELECTION)}"
N_FILES = len(SELECTION)


def find_file(directory: str, num: str) -> str:
    """Find the WAV file starting with the given 3-digit number."""
    for fname in os.listdir(directory):
        if fname.startswith(num) and fname.endswith(".wav"):
            return fname
    raise FileNotFoundError(f"No WAV file starting with {num!r} in {directory}")


def short_name(filename: str) -> str:
    """Extract name between 'NNN - ' (or 'NNN -') and ' [cv313'."""
    m = re.match(r"^\d+ -\s*(.+?)\s*(?:\[cv313|\[)", filename)
    if m:
        name = m.group(1).strip()
    else:
        name = os.path.splitext(filename)[0]
    return name[:14].strip()


def convert(src_path: str, dst_path: str):
    data, sr = sf.read(src_path, dtype="float32", always_2d=True)

    # Force stereo
    if data.shape[1] == 1:
        data = np.repeat(data, 2, axis=1)
    elif data.shape[1] > 2:
        data = data[:, :2]

    # Resample if needed
    if sr != TARGET_SR:
        g = gcd(TARGET_SR, sr)
        up, down = TARGET_SR // g, sr // g
        L = resample_poly(data[:, 0], up, down).astype(np.float32)
        R = resample_poly(data[:, 1], up, down).astype(np.float32)
        data = np.stack([L, R], axis=1)

    # Truncate
    data = data[:MAX_SAMP]

    # Normalize to unit energy (sum L^2 + R^2 = 1)
    energy = float(np.sum(data ** 2))
    if energy > 0:
        data /= np.sqrt(energy)

    # Write interleaved float32
    with open(dst_path, "wb") as f:
        f.write(data.astype(np.float32).tobytes())

    return data.shape[0]


def main():
    os.makedirs(OUT_IR_DIR, exist_ok=True)

    names = []
    for i, num in enumerate(SELECTION):
        fname = find_file(SRC_DIR, num)
        src   = os.path.join(SRC_DIR, fname)
        dst   = os.path.join(OUT_IR_DIR, f"{i:02d}.f32")
        n     = convert(src, dst)
        name  = short_name(fname)
        names.append(name)
        print(f"  {i:02d}  {n:6d}samp  {name!r:<20}  {fname}")

    # Write C++ header
    lines = [
        "// AUTO-GENERATED by scripts/convert_irs.py -- do not edit",
        "#pragma once",
        "",
        f"static constexpr int IR_COUNT = {N_FILES};",
        "",
        "static const char* const IR_NAMES[IR_COUNT] = {",
    ]
    for name in names:
        lines.append(f'    "{name}",')
    lines += ["};", ""]
    with open(OUT_HPP, "w") as f:
        f.write("\n".join(lines))

    print(f"\nWrote {N_FILES} IR files to {OUT_IR_DIR}/")
    print(f"Wrote {OUT_HPP}")


if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)) + "/..")
    main()
