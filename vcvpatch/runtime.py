"""
Runtime interaction with a running VCV Rack process.

Provides:
  RackConnection -- connect to a user-opened Rack instance (MIDI + autosave readback)
  RackSession    -- lifecycle manager for a headless Rack subprocess (for tests)
  MidiMapBuilder -- builds extra_data for Core/MidiMap modules
  MidiMapSpec    -- one CC->param mapping descriptor

Primary workflow (RackConnection):
  1. Build a patch with a Core/MidiMap module (via MidiMapBuilder) and save to .vcv
  2. User opens the patch in VCV Rack normally (GUI, not headless)
  3. Python calls RackConnection.connect() to open a virtual CoreMIDI port
  4. Python calls set_param() to send MIDI CCs -> Rack params change live
  5. Python calls read_state() / read_param() to read back from the autosave

  Required: pip install mido python-rtmidi
  The virtual port "vcvpatch_control" is opened by RackConnection; the patch's
  Core/MidiMap module must be configured with deviceName="vcvpatch_control".

State readback:
  Reads the Rack autosave at AUTOSAVE_JSON (plain JSON, always current).
"""

from __future__ import annotations

import json
import os
import random
import signal
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


RACK_BIN = "/Applications/VCV Rack 2 Free.app/Contents/MacOS/Rack"
AUTOSAVE_JSON = os.path.expanduser(
    "~/Library/Application Support/Rack2/autosave/patch.json"
)
_VIRTUAL_PORT_NAME = "vcvpatch_control"


# ---------------------------------------------------------------------------
# MidiMapSpec + MidiMapBuilder
# ---------------------------------------------------------------------------

@dataclass
class MidiMapSpec:
    """Describes one MIDI CC -> module param mapping."""
    cc: int           # MIDI CC number 0-127
    module_id: int    # target module's integer ID (Module.id)
    param_id: int     # target param integer ID
    min_val: float    # param range minimum
    max_val: float    # param range maximum


class MidiMapBuilder:
    """
    Builds the ``extra_data`` dict for a Core/MidiMap module.

    Usage::

        mmb = MidiMapBuilder()
        mmb.map(cc=1, module_id=vco.id, param_id=2)
        mmb.map(cc=2, module_id=vcf.id, param_id=0)
        # Pass mmb.build() as extra_data when adding the module:
        patch.add("Core", "MidiMap", extra_data=mmb.build())
        # Build RackSession with the specs:
        session = RackSession(path, mmb.to_specs({1: (-2.0, 2.0), 2: (0.0, 1.0)}))
    """

    def __init__(self, driver_id: int = 1, device_name: str = _VIRTUAL_PORT_NAME, channel: int = -1):
        """
        Args:
            driver_id:   RtMidi API enum value used by VCV Rack as the driver ID.
                         1 = MACOSX_CORE (CoreMIDI). Confirmed from libRack.dylib.
            device_name: MIDI port name. VCV Rack matches by name, not index.
                         Defaults to the virtual port name opened by RackSession.
            channel:     MIDI channel (-1 = all channels).
        """
        self._maps: list[dict] = []
        self._driver_id = driver_id
        self._device_name = device_name
        self._channel = channel

    def map(self, cc: int, module_id: int, param_id: int) -> "MidiMapBuilder":
        """Register a CC->param mapping. Returns self for chaining."""
        self._maps.append({"cc": cc, "moduleId": module_id, "paramId": param_id})
        return self

    def build(self) -> dict:
        """Return the ``data`` dict for the MidiMap module's JSON ``data`` field."""
        return {
            "maps": list(self._maps),
            "channels": 0,
            "midi": {
                "driver": self._driver_id,
                "deviceName": self._device_name,
                "channel": self._channel,
            },
        }

    def to_specs(self, ranges: dict[int, tuple[float, float]]) -> list[MidiMapSpec]:
        """
        Convert registered mappings to MidiMapSpec list for RackSession.

        Args:
            ranges: ``{cc: (min_val, max_val)}`` for each CC number.
                    CCs not present default to (0.0, 1.0).
        """
        specs = []
        for m in self._maps:
            cc = m["cc"]
            lo, hi = ranges.get(cc, (0.0, 1.0))
            specs.append(MidiMapSpec(
                cc=cc,
                module_id=m["moduleId"],
                param_id=m["paramId"],
                min_val=lo,
                max_val=hi,
            ))
        return specs


# ---------------------------------------------------------------------------
# RackConnection  (primary API: connect to user-opened Rack instance)
# ---------------------------------------------------------------------------

class RackConnection:
    """
    Connect to a user-opened VCV Rack instance for live param control.

    The patch must already be open in Rack (with GUI, not headless) and must
    contain a Core/MidiMap module pre-configured for the 'vcvpatch_control'
    virtual MIDI port (built via MidiMapBuilder).

    Usage::

        mmb = MidiMapBuilder()
        mmb.map(cc=1, module_id=vco_id, param_id=freq_param_id)
        # ... save patch with mmb.build() as MidiMap extra_data ...

        specs = mmb.to_specs({1: (-2.0, 2.0)})
        with RackConnection(specs) as conn:
            conn.connect()
            conn.set_param(vco_id, freq_param_id, 0.5, min_val=-2.0, max_val=2.0)
            val = conn.read_param(vco_id, freq_param_id)
    """

    def __init__(self, midi_mappings: Optional[list[MidiMapSpec]] = None):
        self.midi_mappings = midi_mappings or []
        self._midi_port = None
        self._spec_map: dict[tuple[int, int], MidiMapSpec] = {
            (s.module_id, s.param_id): s for s in self.midi_mappings
        }

    def connect(self) -> None:
        """
        Open the virtual MIDI port.

        Call this after the user has opened the patch in Rack. The CoreMIDI
        virtual port will appear in Rack's MIDI device list and the pre-configured
        MidiMap module will connect to it by name.

        Raises:
            RuntimeError: if mido/python-rtmidi is not installed, or port cannot
                          be opened.
        """
        try:
            import mido
            self._midi_port = mido.open_output(_VIRTUAL_PORT_NAME, virtual=True)
        except ImportError as exc:
            raise RuntimeError(
                "mido not installed. Install with: pip install mido python-rtmidi"
            ) from exc
        except Exception as exc:
            raise RuntimeError(
                f"Could not open virtual MIDI port '{_VIRTUAL_PORT_NAME}': {exc}"
            ) from exc

    def disconnect(self) -> None:
        """Close the virtual MIDI port."""
        if self._midi_port is not None:
            try:
                self._midi_port.close()
            except Exception:
                pass
            self._midi_port = None

    def set_param(
        self,
        module_id: int,
        param_id: int,
        value: float,
        min_val: float = 0.0,
        max_val: float = 1.0,
    ) -> None:
        """
        Set a module parameter via MIDI CC.

        The (module_id, param_id) pair must have a MidiMapSpec registered at
        construction time. The value is scaled to the CC range using the spec's
        min/max (the min_val/max_val args here are ignored if a spec is found).
        """
        if self._midi_port is None:
            raise RuntimeError(
                "Not connected. Call connect() first."
            )
        spec = self._spec_map.get((module_id, param_id))
        if spec is None:
            raise RuntimeError(
                f"No MIDI mapping registered for module {module_id} param {param_id}. "
                "Add it to MidiMapBuilder before building the patch."
            )
        self._send_cc(spec.cc, value, spec.min_val, spec.max_val)

    def _send_cc(self, cc: int, value: float, min_val: float, max_val: float) -> None:
        import mido
        span = max_val - min_val
        cc_val = round((value - min_val) / span * 127) if span != 0 else 0
        cc_val = max(0, min(127, cc_val))
        self._midi_port.send(mido.Message("control_change", channel=0, control=cc, value=cc_val))

    def read_state(self) -> dict:
        """Read current Rack autosave and return the patch dict."""
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            try:
                with open(AUTOSAVE_JSON, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                time.sleep(0.1)
        raise RuntimeError(f"Could not read autosave at {AUTOSAVE_JSON}")

    def read_param(self, module_id: int, param_id: int) -> Optional[float]:
        """Read the current value of one param from the autosave. Returns None if not found."""
        try:
            state = self.read_state()
        except RuntimeError:
            return None
        for mod in state.get("modules", []):
            if mod.get("id") == module_id:
                for p in mod.get("params", []):
                    if p.get("id") == param_id:
                        return float(p["value"])
        return None

    def __enter__(self) -> "RackConnection":
        return self

    def __exit__(self, *args) -> None:
        self.disconnect()


# ---------------------------------------------------------------------------
# RackSession  (subprocess lifecycle -- used for automated tests only)
# ---------------------------------------------------------------------------

class RackSession:
    """
    Lifecycle manager for a headless VCV Rack process.

    Manages: subprocess, optional MIDI virtual port, autosave readback.

    Example::

        with RackSession("/tmp/patch.vcv", midi_mappings) as sess:
            sess.launch(timeout=15.0)
            sess.set_param(module_id, param_id, 0.75, 0.0, 1.0)
            state = sess.read_state()
    """

    def __init__(
        self,
        patch_path: str,
        midi_mappings: Optional[list[MidiMapSpec]] = None,
        rack_bin: str = RACK_BIN,
    ):
        self.patch_path = patch_path
        self.midi_mappings = midi_mappings or []
        self.rack_bin = rack_bin
        self._proc: Optional[subprocess.Popen] = None
        self._midi_port = None   # mido virtual output port (if available)
        # Map (module_id, param_id) -> MidiMapSpec for fast lookup
        self._spec_map: dict[tuple[int, int], MidiMapSpec] = {
            (s.module_id, s.param_id): s for s in self.midi_mappings
        }

    # -- Lifecycle -----------------------------------------------------------

    def launch(self, timeout: float = 15.0) -> None:
        """
        Start VCV Rack headlessly with self.patch_path.

        Opens a virtual MIDI port (if mido is available and mappings are
        configured), then waits until the autosave shows all expected modules.

        Raises:
            FileNotFoundError: if rack_bin or patch_path does not exist.
            RuntimeError: if Rack does not become ready within timeout.
        """
        if not os.path.isfile(self.rack_bin):
            raise FileNotFoundError(
                f"VCV Rack binary not found at {self.rack_bin!r}. "
                "Install VCV Rack 2 at /Applications/VCV Rack 2 Free.app"
            )
        if not os.path.isfile(self.patch_path):
            raise FileNotFoundError(f"Patch file not found: {self.patch_path!r}")

        # Count modules in the patch file so we can detect readiness
        expected_modules = self._count_patch_modules(self.patch_path)

        # Open virtual MIDI port BEFORE launching Rack (so Rack can see it)
        if self.midi_mappings:
            self._open_midi_port()

        self._proc = subprocess.Popen(
            [self.rack_bin, "-h", self.patch_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        self._wait_ready(expected_modules, timeout)

    def is_alive(self) -> bool:
        """True if the Rack subprocess is still running."""
        return self._proc is not None and self._proc.poll() is None

    def stop(self, timeout: float = 3.0) -> None:
        """Gracefully terminate the Rack process."""
        if self._midi_port is not None:
            try:
                self._midi_port.close()
            except Exception:
                pass
            self._midi_port = None

        if self._proc is not None:
            if self._proc.poll() is None:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
            self._proc = None

    # -- Param control -------------------------------------------------------

    def set_param(
        self,
        module_id: int,
        param_id: int,
        value: float,
        min_val: float = 0.0,
        max_val: float = 1.0,
    ) -> None:
        """
        Set a module parameter via MIDI CC while Rack is running.

        Requires:
          - mido + python-rtmidi installed
          - Session launched with midi_mappings including this (module_id, param_id)
          - Core/MidiMap module present in the patch, configured for the virtual port

        Args:
            module_id: The integer module ID (Module.id).
            param_id:  The integer param ID.
            value:     Target value in [min_val, max_val].
            min_val:   Param minimum (for CC scaling; ignored if spec has its own range).
            max_val:   Param maximum (for CC scaling; ignored if spec has its own range).
        """
        if self._midi_port is None:
            raise RuntimeError(
                "No MIDI port open. Launch the session with midi_mappings configured "
                "and mido + python-rtmidi installed to enable live param control."
            )
        spec = self._spec_map.get((module_id, param_id))
        if spec is None:
            raise RuntimeError(
                f"No MIDI mapping registered for module {module_id} param {param_id}. "
                "Add it to MidiMapBuilder before calling launch()."
            )
        self._send_cc(spec.cc, value, spec.min_val, spec.max_val)

    def _send_cc(self, cc: int, value: float, min_val: float, max_val: float) -> None:
        """Scale value to 0-127 and send a MIDI CC on the virtual port."""
        import mido
        span = max_val - min_val
        cc_val = round((value - min_val) / span * 127) if span != 0 else 0
        cc_val = max(0, min(127, cc_val))
        self._midi_port.send(mido.Message("control_change", channel=0, control=cc, value=cc_val))

    # -- State readback ------------------------------------------------------

    def read_state(self) -> dict:
        """
        Read the current autosave and return the patch dict.

        Returns the parsed patch.json, which reflects Rack's live state
        (params updated by user or MIDI) within ~1-2 seconds.
        """
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            try:
                with open(AUTOSAVE_JSON, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                time.sleep(0.1)
        raise RuntimeError(f"Could not read autosave at {AUTOSAVE_JSON}")

    def read_param(self, module_id: int, param_id: int) -> Optional[float]:
        """
        Read the current value of one param from the autosave.

        Returns None if the module or param is not found.
        """
        try:
            state = self.read_state()
        except RuntimeError:
            return None
        for mod in state.get("modules", []):
            if mod.get("id") == module_id:
                for p in mod.get("params", []):
                    if p.get("id") == param_id:
                        return float(p["value"])
        return None

    # -- Context manager -----------------------------------------------------

    def __enter__(self) -> "RackSession":
        return self

    def __exit__(self, *args) -> None:
        self.stop()

    # -- Internal helpers ----------------------------------------------------

    def _count_patch_modules(self, path: str) -> int:
        from vcvpatch.serialize import load_vcv
        patch = load_vcv(path)
        return len(patch.get("modules", []))

    def _open_midi_port(self) -> None:
        try:
            import mido
            self._midi_port = mido.open_output(_VIRTUAL_PORT_NAME, virtual=True)
        except ImportError:
            pass  # mido not installed; set_param will raise if called
        except Exception:
            pass  # virtual port creation failed; set_param will raise if called

    def _wait_ready(self, expected_modules: int, timeout: float) -> None:
        """Poll autosave until module count matches or timeout elapses."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._proc is not None and self._proc.poll() is not None:
                raise RuntimeError(
                    f"VCV Rack exited unexpectedly (code {self._proc.returncode})."
                )
            try:
                with open(AUTOSAVE_JSON, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if len(data.get("modules", [])) >= expected_modules:
                    return
            except (json.JSONDecodeError, OSError, FileNotFoundError):
                pass
            time.sleep(0.2)
        raise RuntimeError(
            f"VCV Rack did not become ready within {timeout}s. "
            f"Expected {expected_modules} modules in autosave."
        )


# ---------------------------------------------------------------------------
# MIDI driver discovery helper
# ---------------------------------------------------------------------------

def list_midi_inputs() -> list[str]:
    """
    Return available MIDI input port names (requires mido + python-rtmidi).

    Run this to find the port name for your virtual port after creating it.
    """
    try:
        import mido
        return mido.get_input_names()
    except ImportError:
        return ["mido not installed -- pip install mido python-rtmidi"]


# ---------------------------------------------------------------------------
# CLI: discovery helper
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("vcvpatch.runtime -- MIDI discovery")
    print()
    print(f"VCV Rack binary:  {RACK_BIN}")
    print(f"  exists: {os.path.isfile(RACK_BIN)}")
    print()
    print(f"Autosave path:    {AUTOSAVE_JSON}")
    print(f"  exists: {os.path.isfile(AUTOSAVE_JSON)}")
    print()
    try:
        import mido
        print("mido available:", mido.__version__)
        print("MIDI inputs:", mido.get_input_names())
        print("MIDI outputs:", mido.get_output_names())
    except ImportError:
        print("mido not installed. Install with: pip install mido python-rtmidi")
