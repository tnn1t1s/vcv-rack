# Runtime Interaction

`vcvpatch.runtime` lets the agent (or a script) interact with a running VCV Rack
instance -- no GUI required for state readback; MIDI live control requires the
patch to be open (GUI or headless).

Three capabilities:

1. **Headless execution** -- launch Rack with `-h`; wait for the patch to load (`RackSession`, used for tests)
2. **Runtime param control** -- change module params while Rack runs via MIDI CC (`RackConnection`)
3. **State readback** -- read current param values from the Rack autosave

---

## Architecture

```
Python agent
    |
    |-- compile_and_save() ---------> patch.vcv  (zstd tar, proven)
    |
    |-- connect_to_rack() ---------> opens virtual MIDI port "vcvpatch_control"
    |        |                           (user has patch open in GUI Rack)
    |        v
    |   mido virtual port      ~/Library/.../autosave/patch.json
    |
    |-- set_param_live() --------> MIDI CC via RackConnection
    |-- read_live_state() -------> json.load(autosave/patch.json)
    |-- disconnect_from_rack() --> closes virtual MIDI port

RackSession (for headless testing only):
    |-- launch()  -> Rack -h patch.vcv
    |-- set_param() -> MIDI CC (requires mido) -- no stop/relaunch fallback
    |-- read_state() / read_param() -> autosave readback
    |-- stop()
```

The autosave at `~/Library/Application Support/Rack2/autosave/patch.json` is plain
JSON, written by Rack continuously. Reading it requires no IPC.

---

## Prerequisites

### VCV Rack

Install VCV Rack 2 Free at the expected path:

```
/Applications/VCV Rack 2 Free.app
```

Or set a custom path via `RackSession(rack_bin=...)`.

### Python deps (MIDI control)

MIDI-based live param control requires `mido` and `python-rtmidi`:

```
pip install vcvpatch[runtime]
# or: pip install mido python-rtmidi
```

MIDI control is required for `set_param_live`. Without these packages,
`RackConnection.set_param` and `RackSession.set_param` will raise at call time.

---

## Primary workflow: RackConnection (GUI Rack)

The primary agent workflow connects to a user-opened (or headlessly-launched)
Rack instance. The patch must contain a `Core/MidiMap` module pre-configured for
the virtual port `vcvpatch_control` (built via `MidiMapBuilder`).

```python
from vcvpatch.runtime import RackConnection, MidiMapSpec

specs = [
    MidiMapSpec(cc=1, module_id=vco_id, param_id=2, min_val=-2.0, max_val=2.0),
]
with RackConnection(specs) as conn:
    conn.connect()      # opens virtual MIDI port
    conn.set_param(vco_id, 2, 0.5, min_val=-2.0, max_val=2.0)
    val = conn.read_param(vco_id, 2)
```

---

## Headless launch (RackSession -- tests only)

`RackSession` launches a headless Rack subprocess. Use this for automated tests,
not for the primary agent loop (which connects to a user-opened Rack instance).

```python
from vcvpatch.runtime import RackSession

with RackSession("tests/my_patch.vcv") as sess:
    sess.launch(timeout=15.0)   # blocks until patch is loaded
    assert sess.is_alive()
    # Rack is now running headlessly; audio engine is active
```

Readiness is detected by polling the autosave until its `modules` count matches
the patch file. Timeout raises `RuntimeError`.

---

## State readback

Both `RackConnection` and `RackSession` expose the same readback API:

```python
state = conn.read_state()   # returns the autosave dict
for mod in state["modules"]:
    print(mod["plugin"], mod["model"], mod["params"])

# Read one param by module ID and param ID:
val = conn.read_param(module_id=12345678, param_id=0)
print(f"param 0 = {val}")
```

`read_state()` retries for up to 2 seconds to handle the brief window when Rack
is writing the file. `read_param()` returns `None` if not found.

---

## Runtime param control

### MIDI CC via RackConnection (primary method)

Requires `mido` + `python-rtmidi`. A virtual CoreMIDI port named
`vcvpatch_control` is created before calling `connect()`. `Core/MidiMap` must be
pre-built into the patch (at patch-build time via `MidiMapBuilder`) to route CC
messages to target params.

```python
from vcvpatch.runtime import RackConnection, MidiMapBuilder, MidiMapSpec
from vcvpatch.serialize import load_vcv, save_vcv

mmb = MidiMapBuilder()
mmb.map(cc=1, module_id=vco_id, param_id=2)   # FREQ param
mmb.map(cc=2, module_id=vcf_id, param_id=0)   # FREQ param

# Inject MidiMap into the patch using patch.add():
# patch.add("Core", "MidiMap", extra_data=mmb.build())
# (Pass mmb.build() as extra_data at patch-build time, before compile_and_save)

specs = mmb.to_specs({1: (-2.0, 2.0), 2: (0.0, 1.0)})
with RackConnection(specs) as conn:
    conn.connect()
    conn.set_param(vco_id, 2, 0.5)   # instant, scales using spec's min/max
```

**Note on driver ID**: `MidiMapBuilder` defaults to `driver_id=1` (CoreMIDI on
macOS). VCV Rack matches the virtual port by device name (`vcvpatch_control`),
not by index, so the name-based match is reliable. Run `python3 -m vcvpatch.runtime`
to list available MIDI ports and verify connectivity.

### MIDI CC via RackSession (headless tests)

`RackSession.set_param` works identically but requires MIDI mappings to be passed
at construction time. **There is no stop-patch-relaunch fallback** -- if `mido`
is not installed or the mapping is absent, `set_param` raises immediately.

```python
with RackSession("tests/my_patch.vcv", midi_mappings=specs) as sess:
    sess.launch()
    sess.set_param(module_id, param_id, 0.8, min_val=0.0, max_val=1.0)
    val = sess.read_param(module_id, param_id)
```

---

## Agent tools

The agent exposes four tools backed by `RackConnection`:

| Tool | Description |
|------|-------------|
| `connect_to_rack(midi_specs_json)` | Open virtual MIDI port; pass CC->param mappings as JSON |
| `set_param_live(module_id, param_id, value)` | Send MIDI CC to change a param |
| `read_live_state()` | Read all current param values from the autosave |
| `disconnect_from_rack()` | Close the virtual MIDI port |

Example agent workflow:

```
# 1. Build and prove the patch, including a pre-configured Core/MidiMap:
new_patch
add_module vco Fundamental VCO {"FREQ": 0.0}
add_module out Core AudioInterface2 {}
connect_audio vco.SAW out.IN_L
connect_audio vco.SAW out.IN_R
compile_and_save tests/drone.vcv

# 2. User opens tests/drone.vcv in VCV Rack (GUI), then:
connect_to_rack '[{"module_id": 12345678, "param_id": 2, "cc": 1, "min": -2.0, "max": 2.0}]'

# 3. Iterate on params
set_param_live 12345678 2 1.0     # one octave up
read_live_state                   # inspect all current param values

# 4. Clean up
disconnect_from_rack
```

`reset_patch` resets the patch builder and disconnects any active `RackConnection`.

> **TODO: verify** -- The CLAUDE.md and agent workflow section of the old doc
> described `launch_patch` and `stop_rack` tools. These do not exist in `agent/tools.py`
> as of the current implementation. If a headless-launch tool is added in the future,
> it would wrap `RackSession`. Confirm whether these are planned.

---

## File locations

| Path | Description |
|------|-------------|
| `vcvpatch/runtime.py` | `RackSession`, `RackConnection`, `MidiMapBuilder`, `MidiMapSpec` |
| `agent/tools.py` | `connect_to_rack`, `set_param_live`, `read_live_state`, `disconnect_from_rack` |
| `AUTOSAVE_JSON` | `~/Library/Application Support/Rack2/autosave/patch.json` |
| `RACK_BIN` | `/Applications/VCV Rack 2 Free.app/Contents/MacOS/Rack` |

---

## Caveats

- **Headless audio**: Rack's `-h` mode runs the audio engine but may not open
  a hardware audio device. Patches with `Core/AudioInterface2` will process
  audio internally; actual sound output depends on your audio driver config.
- **MIDI driver ID**: `MidiMapBuilder` defaults to `driver_id=1` (CoreMIDI).
  VCV Rack matches by port name (`vcvpatch_control`), so no numeric ID calibration
  is needed as long as the name matches.
- **Autosave timing**: Rack writes the autosave every ~1 second. `read_param`
  may reflect values up to ~1s old.
- **`patch_proven` is unaffected**: `Core/MidiMapNode` is a `ControllerNode`
  with no required CV and no audio outputs. Adding it to a patch never changes
  `patch_proven`.
- **No stop-patch-relaunch fallback**: Unlike what older docs described, neither
  `RackConnection` nor `RackSession` falls back to stopping and relaunching Rack.
  If MIDI is unavailable, `set_param` raises immediately.
