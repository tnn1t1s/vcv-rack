"""Tests for agent/tools/build_patch.py"""
from pathlib import Path
import pytest

from agent.tools.build_patch import build_patch


MINIMAL_PROVEN_PATCH = """
from vcvpatch.builder import PatchBuilder

pb = PatchBuilder()

sampler = pb.module("AudibleInstruments", "Marbles",
    position=[0, 0],
    data={{'t_deja_vu': False, 'x_deja_vu': False, 't_mode': 2, 'x_mode': 0,
           't_range': 2, 'x_range': 0, 'external': False, 'x_scale': 2,
           'y_divider_index': 8, 'x_clock_source_internal': 0}})
resonator = pb.module("AudibleInstruments", "Rings",
    position=[12, 0],
    data={{'polyphony': 1, 'model': 0, 'easterEgg': False}})
texture = pb.module("AudibleInstruments", "Clouds",
    position=[24, 0],
    data={{'playback': 0, 'quality': 0, 'blendMode': 2}})
audio = pb.module("Core", "AudioInterface2",
    position=[40, 0],
    data={{"audio": {{"driver": 6, "deviceName": "Speakers (High Definition Audio Device)",
           "sampleRate": 48000.0, "blockSize": 256,
           "inputOffset": 0, "outputOffset": 0}}, "dcFilter": True}})

pb.connect(sampler.o.T2, resonator.i.Strum)
pb.connect(sampler.o.X2, resonator.i.Pitch_1V_oct)
pb.connect(resonator.o.Odd, texture.i.Left)
pb.connect(texture.o.Left, audio.i.Left_input)
pb.connect(texture.o.Right, audio.i.Right_input)

print(pb.status)
pb.save("{out_path}")
"""

BROKEN_PATCH = """
from vcvpatch.builder import PatchBuilder
pb = PatchBuilder()
# No modules, no connections -- not proven
print(pb.status)
"""


def test_proven_patch_returns_success(tmp_path):
    code = MINIMAL_PROVEN_PATCH.format(out_path=tmp_path / "patch.vcv")
    result = build_patch(code, str(tmp_path))
    assert result["status"] == "success"
    assert result["proven"] is True


def test_proven_patch_saves_py_source(tmp_path):
    code = MINIMAL_PROVEN_PATCH.format(out_path=tmp_path / "patch.vcv")
    build_patch(code, str(tmp_path))
    assert (tmp_path / "patch.py").read_text() == code


def test_proven_patch_saves_vcv(tmp_path):
    code = MINIMAL_PROVEN_PATCH.format(out_path=tmp_path / "patch.vcv")
    build_patch(code, str(tmp_path))
    assert (tmp_path / "patch.vcv").exists()


def test_unproven_patch_returns_success_but_proven_false(tmp_path):
    result = build_patch(BROKEN_PATCH, str(tmp_path))
    assert result["status"] == "success"
    assert result["proven"] is False


def test_syntax_error_returns_error(tmp_path):
    result = build_patch("this is not python !!!!", str(tmp_path))
    assert result["status"] == "error"
    assert result["proven"] is False
    assert result["error"]


def test_stdout_captured(tmp_path):
    code = MINIMAL_PROVEN_PATCH.format(out_path=tmp_path / "patch.vcv")
    result = build_patch(code, str(tmp_path))
    assert "proven=True" in result["stdout"]


def test_creates_output_dir(tmp_path):
    nested = tmp_path / "deep" / "nested"
    code = MINIMAL_PROVEN_PATCH.format(out_path=nested / "patch.vcv")
    result = build_patch(code, str(nested))
    assert result["status"] == "success"
    assert nested.exists()
