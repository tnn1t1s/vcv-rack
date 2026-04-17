"""
agent/tools/ -- shared tool functions for all VCV Rack agents.

Exports:
  collab_post    -- append a message to a JSONL collaboration channel
  collab_read    -- read recent messages from a JSONL collaboration channel
  read_patch     -- read a patch.py with slug -> display name substitution
  generate_speech -- TTS via Google Gemini TTS API
  inspect_module_surface -- exact canonical params/ports plus graph semantics
"""

from .build_patch import build_patch
from .collab import collab_post, collab_read
from .file_read import file_read
from .module_surface import describe_module_surface, inspect_module_surface
from .patch_reader import read_patch
from .tts import generate_speech

__all__ = [
    "build_patch",
    "collab_post",
    "collab_read",
    "file_read",
    "inspect_module_surface",
    "describe_module_surface",
    "read_patch",
    "generate_speech",
]
