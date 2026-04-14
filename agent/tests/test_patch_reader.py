"""
Tests for agent/tools/patch_reader.py.

Tests:
  - read_patch returns error for a non-existent patch
  - read_patch returns success with script for a real patch
  - slug replacement works: AudibleInstruments/Rings -> Resonator, etc.
  - patch_id is in the returned dict on success
"""

import sys
from pathlib import Path
import tempfile
import os

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent.tools.patch_reader import read_patch


# ---------------------------------------------------------------------------
# Tests using a real patch (rings-to-clouds/01)
# ---------------------------------------------------------------------------

PATCH_01 = Path("/Users/palaitis/Development/vcv-rack/patches/rings-to-clouds/01/patch.py")


@pytest.mark.skipif(not PATCH_01.exists(), reason="patch 01 not present")
def test_read_real_patch_success():
    """Reading patch 01 returns status success with a non-empty script."""
    result = read_patch("01")
    assert result["status"] == "success"
    assert result["patch_id"] == "01"
    assert len(result["script"]) > 100


@pytest.mark.skipif(not PATCH_01.exists(), reason="patch 01 not present")
def test_rings_slug_replaced():
    """AudibleInstruments/Rings is replaced with Resonator in the script."""
    result = read_patch("01")
    # The raw slug should not appear
    assert 'pb.module("AudibleInstruments", "Rings"' not in result["script"]
    # The display name should appear
    assert "Resonator" in result["script"]


@pytest.mark.skipif(not PATCH_01.exists(), reason="patch 01 not present")
def test_clouds_slug_replaced():
    """AudibleInstruments/Clouds is replaced with Texture Synthesizer."""
    result = read_patch("01")
    assert 'pb.module("AudibleInstruments", "Clouds"' not in result["script"]
    assert "Texture Synthesizer" in result["script"]


@pytest.mark.skipif(not PATCH_01.exists(), reason="patch 01 not present")
def test_marbles_slug_replaced():
    """AudibleInstruments/Marbles is replaced with Random Sampler."""
    result = read_patch("01")
    assert 'pb.module("AudibleInstruments", "Marbles"' not in result["script"]
    assert "Random Sampler" in result["script"]


# ---------------------------------------------------------------------------
# Tests for error paths
# ---------------------------------------------------------------------------

def test_read_nonexistent_patch():
    """Requesting a patch that does not exist returns status error."""
    result = read_patch("99999")
    assert result["status"] == "error"
    assert "error" in result


def test_read_patch_with_custom_base(tmp_path):
    """
    read_patch with an explicit base_path reads from that directory.
    This lets tests create synthetic patches without touching the real patches/.
    """
    patch_dir = tmp_path / "42"
    patch_dir.mkdir()
    script = 'pb.module("AudibleInstruments", "Rings")\npb.module("AudibleInstruments", "Clouds")\n'
    (patch_dir / "patch.py").write_text(script)

    result = read_patch("42", base_path=tmp_path)
    assert result["status"] == "success"
    assert result["patch_id"] == "42"
    # Slugs should be replaced
    assert "Resonator" in result["script"]
    assert "Texture Synthesizer" in result["script"]
    assert 'pb.module("AudibleInstruments", "Rings"' not in result["script"]
