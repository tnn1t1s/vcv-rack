"""
InstalledRegistry: scans the VCV Rack plugins directory to build the set of
available plugin/model pairs.

Existence is the zeroth check in any proof -- a module that isn't installed
can never produce audio, regardless of wiring.
"""

from __future__ import annotations
import os
import json


class InstalledRegistry:
    """
    Lazy-loading registry of actually-installed VCV Rack modules.

    Available as a singleton via `default()` for normal use, or
    constructed directly with a custom path for testing.
    """

    PLUGINS_DIRS = [
        "~/Library/Application Support/Rack2/plugins-mac-arm64",  # macOS ARM64
        "~/Library/Application Support/Rack2/plugins-mac-x64",   # macOS x64
        "~/Documents/Rack2/plugins",                              # Windows/Linux fallback
    ]

    # Core modules are built into VCV Rack itself -- no plugin.json exists for them.
    BUILTIN = frozenset({
        "Core/AudioInterface2",
        "Core/AudioInterface",
        "Core/Audio2",
        "Core/Audio8",
        "Core/Audio16",
        "Core/MIDIToCVInterface",
        "Core/MIDICCToCVInterface",
        "Core/MIDITriggerToCVInterface",
        "Core/MIDIClock",
        "Core/Notes",
        "Core/Blank",
    })

    def __init__(self, plugins_dir: str = None):
        if plugins_dir:
            self._paths = [os.path.expanduser(plugins_dir)]
        else:
            self._paths = [os.path.expanduser(p) for p in self.PLUGINS_DIRS]
        self._available: set[str] | None = None  # lazy

    def available(self) -> set[str]:
        """Set of 'plugin/model' strings present in the installed plugins."""
        if self._available is None:
            self._available = self._scan()
        return self._available

    def has(self, plugin: str, model: str) -> bool:
        return f"{plugin}/{model}" in self.available()

    def _scan(self) -> set[str]:
        result = set(self.BUILTIN)
        for base in self._paths:
            if not os.path.isdir(base):
                continue
            for entry in os.scandir(base):
                pjson = os.path.join(entry.path, "plugin.json")
                if not os.path.isfile(pjson):
                    continue
                try:
                    with open(pjson) as f:
                        d = json.load(f)
                    plugin_slug = d.get("slug", entry.name)
                    for mod in d.get("modules", []):
                        result.add(f"{plugin_slug}/{mod['slug']}")
                except (json.JSONDecodeError, KeyError):
                    pass
        return result

    @classmethod
    def default(cls) -> "InstalledRegistry":
        return _DEFAULT

    def __len__(self) -> int:
        return len(self.available())

    def __repr__(self) -> str:
        return f"InstalledRegistry({len(self)} modules)"


_DEFAULT = InstalledRegistry()
