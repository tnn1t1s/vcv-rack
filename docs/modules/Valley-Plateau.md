# Valley / Plateau Module Reference

Plugin ID: `Valley`
Model ID: `Plateau`
Discovered cache version: `2.4.5`
All param IDs verified by `rack_introspect` -- see `vcvpatch/discovered/Valley/Plateau/2.4.5.json`.

**Preferred over:** `dbRackModules/MVerb` (non-introspectable; crashes during headless instantiation).

---

## Plateau

High-quality stereo Dattorro-topology reverb with extensive CV modulation inputs.

**Graph node class:** `PlateauNode` (AudioProcessorNode)
**Routes:** IN_L(0) -> OUT_L(0), OUT_R(1); IN_R(1) -> OUT_L(0), OUT_R(1)

### WARNING: Registry param IDs do not match the discovered JSON

The `registry.py` entry for Plateau maps names to IDs that conflict with what `rack_introspect` returns. The discovered JSON is authoritative (it reads directly from `paramQuantities` at runtime). Use the discovered JSON IDs in the table below.

**Example mismatch:**
- Registry says `SIZE=3` -- but discovered id 3 is "Input low cut", and "Size" is id 5.
- Registry says `DECAY=5` -- but discovered id 5 is "Size", and "Decay" is id 7.

**Always use the discovered param IDs below when building patches programmatically.**

### Params (verified from discovered JSON, plugin 2.4.5)

**Main controls:**

| ID | Discovered name | Default | Range | Registry name | Notes |
|----|-----------------|---------|-------|--------------|-------|
| 0 | Dry level | 1.0 | 0-1 | `DRY` | Registry ID matches |
| 1 | Wet level | 0.5 | 0-1 | `WET` | Registry ID matches |
| 2 | Pre-delay | 0 | 0-0.5 | `PRE_DELAY` | Registry ID matches |
| 3 | Input low cut | 10 | 0-10 | `SIZE` (WRONG) | Registry maps SIZE here; actual Size is id 5 |
| 4 | Input high cut | 10 | 0-10 | `DIFFUSION` (WRONG) | Registry maps DIFFUSION here |
| 5 | Size | 0.5 | 0-1 | `DECAY` (WRONG) | Registry maps DECAY here |
| 6 | Diffusion | 10 | 0-10 | `REVERB_HPF` (WRONG) | Registry maps REVERB_HPF here |
| 7 | Decay | 0.54995 | 0.1-0.9999 | `REVERB_LPF` (WRONG) | Registry maps REVERB_LPF here |
| 8 | Reverb high cut | 10 | 0-10 | `IN_HPF` (WRONG) | |
| 9 | Reverb low cut | 10 | 0-10 | `IN_LPF` (WRONG) | |
| 10 | Modulation rate | 0 | 0-1 | `FREEZE` (WRONG) | |
| 11 | Modulation shape | 0.5 | 0-1 | `MOD_SPEED` (WRONG) | |
| 12 | Modulation depth | 0.5 | 0-16 | `MOD_SHAPE` (WRONG) | |
| 13 | Hold | 0 | 0-1 | `MOD_DEPTH` (WRONG) | |
| 14 | Clear | 0 | 0-1 | `TUNED` (WRONG) | |
| 15 | Hold toggle | 0 | 0-1 | `DIFFUSE_IN` (WRONG) | |
| 16 | (unnamed) | 0 | 0-1 | -- | Purpose unknown |

**CV depth attenuverter params** (scale each CV input; range -1 to 1, default 0 = no effect):

| ID | Discovered name |
|----|-----------------|
| 17 | Dry CV depth |
| 18 | Wet CV depth |
| 19 | Input low cut CV |
| 20 | Input high cut CV |
| 21 | Size CV |
| 22 | Diffusion CV |
| 23 | Decay CV |
| 24 | Reverb high cut CV |
| 25 | Reverb low cut CV |
| 26 | Mod speed CV |
| 27 | Mod shape CV |
| 28 | Mod depth CV |

**Mode toggles:**

| ID | Discovered name | Default | Range | Notes |
|----|-----------------|---------|-------|-------|
| 29 | Tuned mode | 0 | 0-1 | Pitch-tracks the reverb to musical intervals |
| 30 | Diffuse input | 1 | 0-1 | Pre-diffuses the input signal |

### Setting params programmatically

Since the registry names are wrong, use `patch.add()` with explicit ID kwargs or use the discovered JSON IDs directly:

```python
reverb = patch.add("Valley", "Plateau",
    pos=[0, 1],
    # Use discovered IDs, not registry names (registry is broken for this module):
    # id 0 = Dry level
    # id 1 = Wet level
    # id 5 = Size
    # id 7 = Decay
)
# Then set params by discovered ID:
# patch.set_param(reverb, 0, 1.0)   # Dry=1.0
# patch.set_param(reverb, 1, 0.45)  # Wet=0.45
# patch.set_param(reverb, 5, 0.8)   # Size=0.8
# patch.set_param(reverb, 7, 0.75)  # Decay=0.75
```

Or use the registry names only for DRY, WET, and PRE_DELAY (IDs 0-2 are correct). Avoid all other registry names until `registry.py` is fixed.

### Ports

**Inputs:**

| ID | Registry names | Notes |
|----|---------------|-------|
| 0 | `IN_L`, `L` | Audio left |
| 1 | `IN_R`, `R` | Audio right |
| 2 | `DRY_CV` | Modulates dry level |
| 3 | `WET_CV` | Modulates wet level |
| 4 | `PRE_DELAY_CV` | Modulates pre-delay |
| 5 | `SIZE_CV` | Modulates room size |
| 6 | `DIFFUSION_CV` | Modulates diffusion |
| 7 | `DECAY_CV` | Modulates decay |
| 8 | `REVERB_HPF_CV` | Modulates reverb high-pass filter |
| 9 | `REVERB_LPF_CV` | Modulates reverb low-pass filter |
| 10 | `IN_HPF_CV` | Modulates input high-pass filter |
| 11 | `IN_LPF_CV` | Modulates input low-pass filter |
| 12 | `FREEZE_CV` | Freeze gate |
| 13 | `MOD_SPEED_CV` | Modulates modulation rate |
| 14 | `MOD_SHAPE_CV` | Modulates modulation shape |
| 15 | `MOD_DEPTH_CV` | Modulates modulation depth |
| 16 | `CLEAR` | Clear/flush reverb buffer |

**Note:** Registry input IDs are separate from param IDs and appear to be correct for inputs.

**Outputs:**

| ID | Registry names | Notes |
|----|---------------|-------|
| 0 | `OUT_L`, `L` | Processed audio left |
| 1 | `OUT_R`, `R` | Processed audio right |

### Typical patch role

Stereo room/hall reverb inserted after the main mix or on a send/return bus. Common settings in this project's patches:

- Spacious room: `DRY=1.0, WET=0.45, Size(id5)=0.8, Decay(id7)=0.75`
- Subtle tail: `DRY=1.0, WET=0.25, Size(id5)=0.5, Decay(id7)=0.55`

Connect Mix4 OUT_L/OUT_R -> Plateau IN_L/IN_R -> downstream processing or AudioInterface.

### Gotchas

- **Registry param IDs 3-30 are wrong.** Always use the discovered JSON IDs for any param other than DRY (0), WET (1), and PRE_DELAY (2).
- CV input modulation is scaled by the corresponding CV depth param (ids 17-28). All CV depth params default to 0, so patching a CV input has no effect until the depth param is set.
- Hold (id 13) freezes the reverb tail indefinitely. Clear (id 14) flushes the buffer.
- Decay range is 0.1 to 0.9999 -- the module clamps it; do not set above 0.9999 (infinite reverb).
- `PlateauNode` routes both IN_L and IN_R to both OUT_L and OUT_R, so a mono source into IN_L alone will produce stereo output.
