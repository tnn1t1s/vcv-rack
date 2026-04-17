"""
patch_reader.py -- Read a patch.py builder script with slug -> display name substitution.

The patch.py files use raw plugin/model slugs like:
    pb.module("AudibleInstruments", "Rings", ...)

Before handing the script to the narration agent, we substitute well-known
slugs with their user-facing display names so the model reasons in terms of
"Resonator" rather than "Rings", avoiding reliance on its training knowledge
of these specific modules.

Substitution table (derived from the VCV Rack module display names):
    AudibleInstruments/Rings   -> Resonator
    AudibleInstruments/Clouds  -> Texture Synthesizer
    AudibleInstruments/Marbles -> Random Sampler

Usage:
    from agent.tools.patch_reader import read_patch

    result = read_patch("01")
    # result = {"status": "success", "patch_id": "01", "script": "..."}

    # With a custom base path (useful in tests):
    result = read_patch("42", base_path=Path("/tmp/test_patches"))
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional


# Default base directory for rings-to-clouds patches
_DEFAULT_BASE = Path("/Users/palaitis/Development/vcv-rack/patches/corpus/rings-to-clouds")

# Slug -> display name substitutions applied before the agent sees the script.
# Keys are substrings matched in the raw Python source; order matters for
# compound replacements (longer/more-specific keys first is safer).
_SLUG_SUBSTITUTIONS: list[tuple[str, str]] = [
    # pb.module() call-site replacements (two-arg form)
    ('pb.module("AudibleInstruments", "Rings"',   'pb.module("Resonator"'),
    ('pb.module("AudibleInstruments", "Clouds"',  'pb.module("Texture Synthesizer"'),
    ('pb.module("AudibleInstruments", "Marbles"', 'pb.module("Random Sampler"'),
    # Inline comment / string replacements
    ('Rings into Clouds',   'Resonator into Texture Synthesizer'),
    ('"Rings"',             '"Resonator"'),
    ('"Clouds"',            '"Texture Synthesizer"'),
    ('"Marbles"',           '"Random Sampler"'),
    # Bare comment references
    ('# Rings',             '# Resonator'),
    ('# Clouds',            '# Texture Synthesizer'),
    ('# Marbles',           '# Random Sampler'),
]


def read_patch(patch_id: str, base_path: Optional[Path] = None) -> dict:
    """
    Read the patch.py builder script for a rings-to-clouds patch.

    Applies slug -> display name substitutions before returning the script
    so the downstream agent reasons in terms of module functions, not raw slugs.

    Args:
        patch_id:  Zero-padded patch ID, e.g. "01", "12".
        base_path: Override the default patches/corpus/rings-to-clouds/ base directory.
                   Useful in tests to supply synthetic patch directories.

    Returns:
        On success:
            {"status": "success", "patch_id": patch_id, "script": <python source>}
        On failure:
            {"status": "error", "error": <message>}
    """
    try:
        base = (base_path or _DEFAULT_BASE) / patch_id
        py_path = base / "patch.py"

        if not py_path.exists():
            return {
                "status": "error",
                "error": f"patch.py not found: {py_path}",
            }

        script = py_path.read_text(encoding="utf-8")

        # Apply all slug substitutions in order
        for slug, display in _SLUG_SUBSTITUTIONS:
            script = script.replace(slug, display)

        return {
            "status":   "success",
            "patch_id": patch_id,
            "script":   script,
        }

    except Exception as exc:
        return {"status": "error", "error": str(exc)}
