"""
Populate vcvpatch/discovered/ cache for every installed plugin.

Runs rack_introspect on every plugin directory, dumps all models.
Safe to re-run -- skips models already cached at the current version.

Usage:
    python3 tools/populate_cache.py [--force]
"""

import json, os, subprocess, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from vcvpatch.introspect import (
    PLUGINS_DIR, RACK_LIB_DIR, SHIM, CACHE_DIR,
    _installed_version, _cache_path, _save_cache, _save_failed,
)

SHIM_BIN = os.path.realpath(SHIM)
FORCE = "--force" in sys.argv


def get_model_slugs(plugin_dir: str) -> list[str]:
    """Read model slugs from plugin.json without running the shim."""
    path = os.path.join(plugin_dir, "plugin.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        data = json.load(f)
    return [m["slug"] for m in data.get("modules", []) if "slug" in m]


def run_model(plugin_dir: str, model_slug: str) -> list[dict] | None:
    """Run shim for a single model. Returns params or None on failure."""
    env = os.environ.copy()
    env["DYLD_LIBRARY_PATH"] = RACK_LIB_DIR
    result = subprocess.run(
        [SHIM_BIN, plugin_dir, model_slug],
        capture_output=True, text=True, env=env,
    )
    if result.returncode != 0 or not result.stdout.strip():
        if result.stderr.strip():
            print(f"    stderr: {result.stderr.strip()[:120]}")
        return None
    try:
        modules = json.loads(result.stdout)
        for m in modules:
            if m.get("model") == model_slug:
                return m["params"]
        return []
    except json.JSONDecodeError as e:
        print(f"    bad JSON: {e}")
        return None


def main():
    if not os.path.exists(SHIM_BIN):
        print(f"rack_introspect not found at {SHIM_BIN}. Run: make")
        sys.exit(1)

    plugins = sorted(os.listdir(PLUGINS_DIR))
    total_new = 0

    for plugin_slug in plugins:
        plugin_dir = os.path.join(PLUGINS_DIR, plugin_slug)
        if not os.path.isdir(plugin_dir):
            continue
        if not os.path.exists(os.path.join(plugin_dir, "plugin.dylib")):
            continue

        version = _installed_version(plugin_slug)
        if not version:
            print(f"{plugin_slug}: no plugin.json, skipping")
            continue

        slugs = get_model_slugs(plugin_dir)
        if not slugs:
            print(f"{plugin_slug} {version}: no models in plugin.json")
            continue

        print(f"{plugin_slug} {version} ({len(slugs)} models)")
        for model in slugs:
            path = _cache_path(plugin_slug, model, version)
            if not FORCE and os.path.exists(path):
                with open(path) as f:
                    n = len(json.load(f).get("params", []))
                print(f"  {model}: cached ({n} params)")
                continue

            params = run_model(plugin_dir, model)
            if params is None:
                print(f"  {model}: FAILED (crash or bad output)")
                _save_failed(plugin_slug, model, version,
                             reason="createModule() crashed or produced invalid output")
                continue

            _save_cache(plugin_slug, model, version, params)
            print(f"  {model}: {len(params)} params  [saved]")
            total_new += 1

    print(f"\nDone. {total_new} new cache entries written.")


if __name__ == "__main__":
    main()
