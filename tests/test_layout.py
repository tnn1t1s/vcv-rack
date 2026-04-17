import pytest

from vcvpatch import PatchBuilder, RackLayout


def test_layout_row_at_yields_explicit_position():
    layout = RackLayout()
    assert layout.row(2).at(36).as_list() == [36, 2]


def test_patchbuilder_requires_explicit_position():
    pb = PatchBuilder()
    with pytest.raises(TypeError):
        pb.module("Fundamental", "VCO")
