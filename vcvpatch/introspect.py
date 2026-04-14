"""
Module param introspection via rack_introspect (headless C++ shim).

Local cache layer: vcvpatch/discovered/<plugin>/<model>/<version>.json
- Keyed by plugin version from plugin.json
- Auto-discovers on cache miss
- Treated as local/generated cache, not committed source

Failed modules: vcvpatch/discovered/<plugin>/<model>/failed.<version>.json
- Recorded when createModule() crashes headlessly
- Introspectability is a first-class selection criterion:
  if we can't introspect a module, we can't prove its params are correct,
  so the agent should prefer introspectable alternatives.

CLI:
    python -m vcvpatch.introspect Fundamental VCO

Public API:
    get_params(plugin, model)      -> list[dict]  # {id, name, default, min, max}
    is_introspectable(plugin, model) -> bool
    introspection_failure(plugin, model) -> str | None  # reason string or None
"""

import json
import os
import subprocess
import sys

PLUGINS_DIR = os.path.expanduser(
    "~/Library/Application Support/Rack2/plugins-mac-arm64"
)
RACK_LIB_DIR = "/Applications/VCV Rack 2 Free.app/Contents/Resources"
SHIM = os.path.join(os.path.dirname(__file__), "..", "tools", "rack_introspect")
CACHE_DIR = os.path.join(os.path.dirname(__file__), "discovered")


def _plugin_dir(plugin: str) -> str:
    return os.path.join(PLUGINS_DIR, plugin)


def _installed_version(plugin: str) -> str | None:
    """Read plugin version from plugin.json. Returns None if not installed."""
    path = os.path.join(_plugin_dir(plugin), "plugin.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f).get("version")


def _cache_path(plugin: str, model: str, version: str) -> str:
    return os.path.join(CACHE_DIR, plugin, model, f"{version}.json")


def _failed_path(plugin: str, model: str, version: str) -> str:
    return os.path.join(CACHE_DIR, plugin, model, f"failed.{version}.json")


def _load_cache(plugin: str, model: str, version: str) -> list[dict] | None:
    path = _cache_path(plugin, model, version)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        data = json.load(f)
    return data.get("params")


def _save_cache(plugin: str, model: str, version: str, params: list[dict]) -> None:
    path = _cache_path(plugin, model, version)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({"plugin": plugin, "model": model, "version": version,
                   "params": params}, f, indent=2)


def _save_failed(plugin: str, model: str, version: str, reason: str) -> None:
    path = _failed_path(plugin, model, version)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({"plugin": plugin, "model": model, "version": version,
                   "introspectable": False, "reason": reason}, f, indent=2)


def _run_shim(plugin: str, model: str) -> list[dict]:
    """Run rack_introspect and return params for the requested model."""
    shim = os.path.realpath(SHIM)
    if not os.path.exists(shim):
        raise RuntimeError(
            f"rack_introspect not found at {shim}. Run: make"
        )
    env = os.environ.copy()
    env["DYLD_LIBRARY_PATH"] = RACK_LIB_DIR

    result = subprocess.run(
        [shim, _plugin_dir(plugin), model],
        capture_output=True, text=True, env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"rack_introspect failed for {plugin}/{model}:\n{result.stderr}"
        )

    modules = json.loads(result.stdout)
    for m in modules:
        if m.get("model") == model:
            return m["params"]
    raise RuntimeError(f"rack_introspect ran but {plugin}/{model} not found in output")


def get_params(plugin: str, model: str) -> list[dict]:
    """
    Return param metadata for a module, auto-discovering if needed.

    Returns list of {id, name, default, min, max} dicts sorted by id.
    Raises RuntimeError if the plugin is not installed and not cached.
    """
    version = _installed_version(plugin)

    if version is not None:
        cached = _load_cache(plugin, model, version)
        if cached is not None:
            return cached
        # Cache miss -- run shim and cache the result
        params = _run_shim(plugin, model)
        _save_cache(plugin, model, version, params)
        return params

    # Plugin not installed -- look for any cached version (excluding failed markers)
    model_cache_dir = os.path.join(CACHE_DIR, plugin, model)
    if os.path.isdir(model_cache_dir):
        versions = sorted(
            f for f in os.listdir(model_cache_dir)
            if f.endswith(".json") and not f.startswith("failed.")
        )
        if versions:
            newest = versions[-1]
            import warnings
            warnings.warn(
                f"{plugin}/{model}: not installed, using cached version "
                f"{newest.removesuffix('.json')}",
                stacklevel=2,
            )
            with open(os.path.join(model_cache_dir, newest)) as f:
                return json.load(f).get("params", [])

    raise RuntimeError(
        f"{plugin} is not installed and no cached param data exists for {model}. "
        f"Install the plugin and run get_params() once to populate the cache."
    )


def introspection_failure(plugin: str, model: str) -> str | None:
    """
    Return the failure reason if this module failed headless introspection,
    None if it is introspectable (or not yet attempted).
    Checks against the currently installed version.
    """
    version = _installed_version(plugin)
    if version is None:
        return None  # not installed, no verdict
    path = _failed_path(plugin, model, version)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f).get("reason", "unknown failure")


def is_introspectable(plugin: str, model: str) -> bool:
    """
    True if this module can be fully introspected headlessly.

    A module is introspectable when:
    - Its plugin is installed, AND
    - A successful param cache exists for the current version, AND
    - No failure record exists for the current version.

    Modules that fail introspection should be avoided by the agent;
    prefer alternatives that are fully provable.
    """
    version = _installed_version(plugin)
    if version is None:
        return False
    if os.path.exists(_failed_path(plugin, model, version)):
        return False
    return os.path.exists(_cache_path(plugin, model, version))


def param_by_name(plugin: str, model: str, name: str) -> dict | None:
    """Return the param dict matching name (case-insensitive), or None."""
    name_lower = name.lower()
    for p in get_params(plugin, model):
        if p.get("name", "").lower() == name_lower:
            return p
    return None


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python -m vcvpatch.introspect <Plugin> <Model>", file=sys.stderr)
        raise SystemExit(2)

    plugin, model = sys.argv[1], sys.argv[2]
    params = get_params(plugin, model)
    print(json.dumps({
        "plugin": plugin,
        "model": model,
        "params": params,
    }, indent=2))
