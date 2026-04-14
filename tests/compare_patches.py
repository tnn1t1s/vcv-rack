"""
Structural comparison of two .vcv patch files.

Module IDs are random per run, so comparison normalises them to
(plugin, model) keys and checks:
  - same set of modules with same params
  - same set of cables by (src_plugin/model:port, dst_plugin/model:port)

Usage:
    uv run python -m tests.compare_patches <patch_a.vcv> <patch_b.vcv>
"""

import os
import sys

from vcvpatch.serialize import load_vcv


def normalise(patch: dict) -> tuple[frozenset, frozenset]:
    """
    Return (modules, cables) as frozensets of comparable tuples,
    with random module IDs replaced by (plugin, model).
    """
    # Build id -> (plugin, model) map
    id_to_key = {
        m["id"]: (m["plugin"], m["model"])
        for m in patch["modules"]
    }

    modules = frozenset(
        (
            m["plugin"],
            m["model"],
            frozenset((p["id"], p["value"]) for p in m.get("params", [])),
        )
        for m in patch["modules"]
    )

    cables = frozenset(
        (
            id_to_key[c["outputModuleId"]],
            c["outputId"],
            id_to_key[c["inputModuleId"]],
            c["inputId"],
            c["color"],
        )
        for c in patch["cables"]
    )

    return modules, cables


def compare(path_a: str, path_b: str) -> bool:
    a = load_vcv(path_a)
    b = load_vcv(path_b)

    mods_a, cables_a = normalise(a)
    mods_b, cables_b = normalise(b)

    ok = True

    if mods_a == mods_b:
        print(f"Modules:  OK ({len(mods_a)} modules, params match)")
    else:
        ok = False
        only_a = mods_a - mods_b
        only_b = mods_b - mods_a
        print("Modules:  MISMATCH")
        for m in sorted(only_a):
            print(f"  only in A: {m[0]}/{m[1]}  params={dict(m[2])}")
        for m in sorted(only_b):
            print(f"  only in B: {m[0]}/{m[1]}  params={dict(m[2])}")

    if cables_a == cables_b:
        print(f"Cables:   OK ({len(cables_a)} cables, connections and colors match)")
    else:
        ok = False
        only_a = cables_a - cables_b
        only_b = cables_b - cables_a
        print("Cables:   MISMATCH")
        for c in sorted(only_a):
            print(f"  only in A: {c[0][1]}[out {c[1]}] -> {c[2][1]}[in {c[3]}]  {c[4]}")
        for c in sorted(only_b):
            print(f"  only in B: {c[0][1]}[out {c[1]}] -> {c[2][1]}[in {c[3]}]  {c[4]}")

    return ok


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <patch_a.vcv> <patch_b.vcv>")
        sys.exit(1)

    path_a, path_b = sys.argv[1], sys.argv[2]
    print(f"A: {path_a}")
    print(f"B: {path_b}")
    print()

    if compare(path_a, path_b):
        print("\nPatches are structurally identical.")
        sys.exit(0)
    else:
        print("\nPatches differ.")
        sys.exit(1)
