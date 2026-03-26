"""
patch_screenshot.py -- Screenshot modules from a .vcv patch file.

Uses VCV Rack's built-in `-t <zoom>` CLI flag to render module screenshots
headlessly. Rack renders ALL installed modules, so this extracts only the
ones present in the given patch file.

Usage:
    python3 tools/patch_screenshot.py tests/slimechild_demo.vcv [output_dir]
    # Screenshots saved to output_dir/{plugin}/{model}.png

Programmatic usage:
    from tools.patch_screenshot import screenshot_patch
    paths = screenshot_patch("tests/slimechild_demo.vcv")
    # Returns {"SlimeChild-Substation/SlimeChild-Substation-Clock": "/tmp/.../Clock.png", ...}
"""

import io
import json
import os
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import zstandard


RACK_APP = "/Applications/VCV Rack 2 Free.app/Contents/MacOS/Rack"
PLUGINS_DIR = os.path.expanduser(
    "~/Library/Application Support/Rack2/plugins-mac-arm64"
)


def _read_patch_modules(vcv_path: str) -> list[tuple[str, str]]:
    """Return [(plugin, model), ...] for all modules in a .vcv file."""
    with open(vcv_path, "rb") as f:
        raw = zstandard.ZstdDecompressor().stream_reader(f).read()
    tf = tarfile.open(fileobj=io.BytesIO(raw))
    patch = json.loads(tf.extractfile("patch.json").read())
    return [(m["plugin"], m["model"]) for m in patch.get("modules", [])]


def screenshot_patch(
    vcv_path: str,
    output_dir: str | None = None,
    zoom: float = 2.0,
    timeout: float = 30.0,
) -> dict[str, str]:
    """
    Screenshot every module present in vcv_path.

    Returns a dict mapping "Plugin/Model" -> absolute PNG path.
    Saves PNGs to output_dir (default: a temp dir that persists until
    the caller deletes it, or a caller-supplied directory).
    """
    vcv_path = os.path.abspath(vcv_path)
    modules = _read_patch_modules(vcv_path)

    # Deduplicate while preserving order
    seen: set[tuple[str, str]] = set()
    unique_modules: list[tuple[str, str]] = []
    for pm in modules:
        if pm not in seen and pm[0] != "Core":
            seen.add(pm)
            unique_modules.append(pm)

    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="vcv_screenshots_")
    os.makedirs(output_dir, exist_ok=True)

    # Rack needs a user dir with plugins accessible.
    # Use a temp user dir with a symlink to the real plugins dir.
    user_dir = tempfile.mkdtemp(prefix="vcv_userdir_")
    plugins_link = os.path.join(user_dir, "plugins-mac-arm64")
    os.symlink(PLUGINS_DIR, plugins_link)

    proc = subprocess.Popen(
        [RACK_APP, "-t", str(zoom), "-u", user_dir, vcv_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for screenshots to appear; Rack doesn't exit automatically.
    screenshots_dir = os.path.join(user_dir, "screenshots")
    deadline = time.time() + timeout
    last_count = 0
    stable_since: float | None = None

    while time.time() < deadline:
        time.sleep(1.0)
        if not os.path.isdir(screenshots_dir):
            continue
        # Count all PNGs
        count = sum(
            1
            for root, _, files in os.walk(screenshots_dir)
            for f in files
            if f.endswith(".png")
        )
        if count != last_count:
            last_count = count
            stable_since = None
        else:
            if stable_since is None:
                stable_since = time.time()
            elif time.time() - stable_since > 3.0:
                break  # stable for 3s -- done

    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

    # Collect screenshots for the modules in the patch
    result: dict[str, str] = {}
    for plugin, model in unique_modules:
        src = os.path.join(screenshots_dir, plugin, f"{model}.png")
        if os.path.isfile(src):
            dest_dir = os.path.join(output_dir, plugin)
            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, f"{model}.png")
            shutil.copy2(src, dest)
            result[f"{plugin}/{model}"] = dest

    # Clean up temp user dir
    shutil.rmtree(user_dir, ignore_errors=True)

    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <patch.vcv> [output_dir]")
        sys.exit(1)

    vcv = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Screenshotting modules in {vcv}...")
    paths = screenshot_patch(vcv, output_dir=out)

    if not paths:
        print("No screenshots captured.")
        sys.exit(1)

    print(f"Captured {len(paths)} module screenshots:")
    for key, path in paths.items():
        print(f"  {key}: {path}")
