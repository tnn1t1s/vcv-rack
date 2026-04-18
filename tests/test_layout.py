import ast
from pathlib import Path

import pytest

from vcvpatch import PatchBuilder, RackLayout


def test_layout_row_at_yields_explicit_position():
    layout = RackLayout()
    assert layout.row(2).at(36).as_list() == [36, 2]


def test_patchbuilder_requires_explicit_position():
    pb = PatchBuilder()
    with pytest.raises(TypeError):
        pb.module("Fundamental", "VCO")


def test_maintained_patch_scripts_use_explicit_positions():
    root = Path(__file__).resolve().parents[1]
    patch_roots = [
        root / "patches" / "curated",
        root / "patches" / "studies",
    ]

    missing = []
    for patch_root in patch_roots:
        for script in sorted(patch_root.glob("*.py")):
            tree = ast.parse(script.read_text(), filename=str(script))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not isinstance(func, ast.Attribute) or func.attr != "module":
                    continue
                if any(keyword.arg == "position" for keyword in node.keywords):
                    continue
                missing.append(f"{script.relative_to(root)}:{node.lineno}")

    assert not missing, "Missing explicit position in maintained patch scripts:\n" + "\n".join(missing)
