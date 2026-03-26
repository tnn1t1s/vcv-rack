"""
publish_agent.py -- ADK sub-agent for VCV Rack patch publishing.

Tools are dumb primitives. The agent provides all reasoning.

Screenshot workflow:
  1. screenshot_raw captures the Rack window, resizes to 1x logical pixels,
     saves to disk, and stores the path in session state.
  2. before_model_callback injects the image into every LLM turn so the model
     can see it.
  3. The agent calls crop_image with the pixel coordinates it visually determines.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import signal
import subprocess
import tarfile
import tempfile
import time
import zstandard

from dotenv import load_dotenv
load_dotenv()

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.tool_context import ToolContext
from google.genai import types

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RACK_APP = "/Applications/VCV Rack 2 Free.app/Contents/MacOS/Rack"
PLUGINS_DIR = os.path.expanduser(
    "~/Library/Application Support/Rack2/plugins-mac-arm64"
)


# ---------------------------------------------------------------------------
# Internal helpers (not tools)
# ---------------------------------------------------------------------------

def _read_patch(vcv_path: str) -> dict:
    with open(vcv_path, "rb") as f:
        raw = zstandard.ZstdDecompressor().stream_reader(f).read()
    tf = tarfile.open(fileobj=io.BytesIO(raw))
    return json.loads(tf.extractfile("patch.json").read())


def _rack_window_geometry() -> tuple[int, int, int, int] | None:
    result = subprocess.run(
        ["osascript", "-e", """
        tell application "System Events"
            tell process "Rack"
                set pos to position of window 1
                set sz to size of window 1
                return (item 1 of pos) & "," & (item 2 of pos) & "," & (item 1 of sz) & "," & (item 2 of sz)
            end tell
        end tell
        """],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    import re
    nums = re.findall(r'\d+', result.stdout)
    if len(nums) != 4:
        return None
    return tuple(int(n) for n in nums)


def _rack_is_running() -> bool:
    result = subprocess.run(
        ["osascript", "-e",
         'tell application "System Events" to get name of every process'],
        capture_output=True, text=True,
    )
    return "Rack" in result.stdout


def _bring_rack_front():
    subprocess.run(
        ["osascript", "-e", """
        tell application "System Events"
            tell process "Rack"
                set frontmost to true
                perform action "AXRaise" of window 1
            end tell
        end tell
        """],
        capture_output=True,
    )


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def open_patch(vcv_path: str, tool_context: ToolContext = None) -> dict:
    """
    Open a .vcv patch file in VCV Rack and wait for the window to appear.

    Args:
        vcv_path: Path to the .vcv file.
    """
    vcv_path = os.path.abspath(vcv_path)
    if not os.path.isfile(vcv_path):
        return {"status": "error", "message": f"File not found: {vcv_path}"}

    subprocess.Popen(["open", vcv_path])
    for _ in range(20):
        time.sleep(0.5)
        if _rack_is_running() and _rack_window_geometry():
            return {"status": "ok", "vcv_path": vcv_path}

    return {"status": "error", "message": "Rack did not open within 10s"}


async def screenshot_raw(output_path: str,
                         tool_context: ToolContext = None) -> dict:
    """
    Capture the current VCV Rack window as a 1x (logical pixel) PNG.

    Brings Rack to the front, captures at native resolution, then downscales
    to logical pixel dimensions so crop coordinates are unambiguous.
    The image is stored in session state for the model to inspect.

    Args:
        output_path: Where to save the PNG on disk.
    """
    if not _rack_is_running():
        return {"status": "error", "message": "VCV Rack is not running. Call open_patch first."}

    _bring_rack_front()
    time.sleep(0.5)

    geo = _rack_window_geometry()
    if geo is None:
        return {"status": "error", "message": "Cannot get Rack window geometry"}

    x, y, w, h = geo
    result = subprocess.run(
        ["screencapture", "-R", f"{x},{y},{w},{h}", output_path],
        capture_output=True,
    )
    if result.returncode != 0:
        return {"status": "error", "message": "screencapture failed"}

    # Downscale to logical pixels (1x) so model coordinates are unambiguous
    from PIL import Image
    img = Image.open(output_path)
    if img.size != (w, h):
        img = img.resize((w, h), Image.LANCZOS)
        img.save(output_path)

    if tool_context is not None:
        tool_context.state["screenshot_path"] = output_path

    return {"status": "ok", "path": output_path, "width": w, "height": h}


def crop_image(src_path: str, dst_path: str,
               x: int, y: int, width: int, height: int,
               tool_context: ToolContext = None) -> dict:
    """
    Crop a PNG to the given pixel rectangle and save the result.

    Coordinates are in logical pixels matching what screenshot_raw reports.

    Args:
        src_path: Source PNG path (as returned by screenshot_raw).
        dst_path: Output PNG path.
        x:        Left edge of crop box in pixels.
        y:        Top edge of crop box in pixels.
        width:    Width of crop box in pixels.
        height:   Height of crop box in pixels.
    """
    from PIL import Image
    try:
        img = Image.open(src_path)
        cropped = img.crop((x, y, x + width, y + height))
        cropped.save(dst_path)
        if tool_context is not None:
            tool_context.state["screenshot_path"] = None
        return {"status": "ok", "path": dst_path, "size": [width, height]}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def screenshot_modules(vcv_path: str, output_dir: str,
                       zoom: float = 2.0,
                       tool_context: ToolContext = None) -> dict:
    """
    Render individual module screenshots for every module in the patch.

    Uses VCV Rack's built-in -t flag. Returns paths organized by plugin/model.

    Args:
        vcv_path:   Path to the .vcv file.
        output_dir: Directory to save PNGs into.
        zoom:       Screenshot zoom level (default 2.0 for retina quality).
    """
    vcv_path = os.path.abspath(vcv_path)
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    patch = _read_patch(vcv_path)
    module_set = {
        (m["plugin"], m["model"])
        for m in patch.get("modules", [])
        if m.get("plugin") != "Core"
    }

    user_dir = tempfile.mkdtemp(prefix="vcv_userdir_")
    os.symlink(PLUGINS_DIR, os.path.join(user_dir, "plugins-mac-arm64"))

    proc = subprocess.Popen(
        [RACK_APP, "-t", str(zoom), "-u", user_dir, vcv_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    screenshots_dir = os.path.join(user_dir, "screenshots")
    deadline = time.time() + 40
    last_count, stable_since = 0, None
    while time.time() < deadline:
        time.sleep(1.0)
        if not os.path.isdir(screenshots_dir):
            continue
        count = sum(1 for _, _, files in os.walk(screenshots_dir)
                    for f in files if f.endswith(".png"))
        if count != last_count:
            last_count = count
            stable_since = None
        else:
            if stable_since is None:
                stable_since = time.time()
            elif time.time() - stable_since > 3.0:
                break

    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()

    captured: dict[str, str] = {}
    for plugin, model in module_set:
        src = os.path.join(screenshots_dir, plugin, f"{model}.png")
        if os.path.isfile(src):
            dest_dir = os.path.join(output_dir, plugin)
            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, f"{model}.png")
            shutil.copy2(src, dest)
            captured[f"{plugin}/{model}"] = dest

    shutil.rmtree(user_dir, ignore_errors=True)
    missing = [f"{p}/{m}" for p, m in module_set if f"{p}/{m}" not in captured]
    return {"status": "ok", "captured": captured, "missing": missing, "output_dir": output_dir}


# ---------------------------------------------------------------------------
# Before-model callback: inject screenshot into vision context
# ---------------------------------------------------------------------------

def _inject_screenshot(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> LlmResponse | None:
    """
    If a screenshot is in session state, inject it as an image Part into
    the last user message so the model can see it.
    """
    path = callback_context.state.get("screenshot_path")
    if not path or not os.path.isfile(path):
        return None

    import base64
    with open(path, "rb") as f:
        data = f.read()

    image_part = types.Part(
        inline_data=types.Blob(mime_type="image/png", data=data)
    )

    for content in reversed(llm_request.contents):
        if content.role == "user":
            content.parts.append(image_part)
            break

    return None


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

_INSTRUCTION = """
You are the VCV Rack publishing agent. You handle screenshots and visual output.

## Tools

- `open_patch(vcv_path)`: Open a .vcv file in VCV Rack.
- `screenshot_raw(output_path)`: Capture the full VCV Rack window as a 1x PNG.
  Returns width and height in logical pixels. The image is automatically
  injected into your context so you can see it immediately.
- `crop_image(src_path, dst_path, x, y, width, height)`: Crop a PNG.
  Coordinates are in the same logical pixel space as screenshot_raw reports.
- `screenshot_modules(vcv_path, output_dir)`: Render individual module PNGs.

## Workflow for a cropped patch screenshot

1. Call `open_patch(vcv_path)` if Rack is not already open.
2. Call `screenshot_raw(output_path)` -- you will see the image.
3. Visually identify the bounding box of the synth modules only:
   - Exclude the title bar and menu bar at the top -- the top edge of the
     crop should start at the top of the module panels themselves.
   - Exclude the rack rail/bar at the bottom -- the bottom edge of the crop
     should end at the bottom of the module panels, not the rack enclosure.
   - On the left, include a small strip of empty rack (20-40px) as margin.
   - On the right: it is critical that the last synth module (e.g. VCA) is
     fully visible and not clipped. It is acceptable to include a small sliver
     of the AUDIO module on the right edge if needed. Never clip a synth module.
     Add at least 30px of margin past the right edge of the last synth module.
4. Call `crop_image(src_path=output_path, dst_path=<cropped_path>, x=..., y=..., width=..., height=...)`.
5. Return the cropped path.

The image dimensions are exactly as reported by screenshot_raw (width x height logical pixels).
Use those dimensions to reason about where the module area sits in the image.
"""

publish_agent = Agent(
    name="vcv_publish",
    model=LiteLlm(model="openrouter/google/gemini-3.1-pro-preview"),
    description=(
        "Opens VCV Rack patches and captures cropped screenshots. "
        "Delegate all screenshot and publishing tasks here."
    ),
    instruction=_INSTRUCTION,
    tools=[open_patch, screenshot_raw, crop_image, screenshot_modules],
    before_model_callback=_inject_screenshot,
)
