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

### Current truth split

Plateau is still a structural non-overlap case:
- discovered metadata provides the param surface below
- the supplement/registry layer only contributes the stereo `Left` / `Right` IO names

So there is no overlapping param reconciliation for Plateau yet. Treat the discovered
param table below as authoritative for controls, and the stereo IO names below as the
current product truth for ports.

### Params (verified from discovered JSON, plugin 2.4.5)

**Main controls:**

| ID | Param name | Default | Range | Historical shorthand | Notes |
|----|------------|---------|-------|----------------------|-------|
| 0 | Dry level | 1.0 | 0-1 | `DRY` | |
| 1 | Wet level | 0.5 | 0-1 | `WET` | |
| 2 | Pre-delay | 0 | 0-0.5 | `PRE_DELAY` | |
| 3 | Input low cut | 10 | 0-10 | `SIZE` | historical shorthand only |
| 4 | Input high cut | 10 | 0-10 | `DIFFUSION` | historical shorthand only |
| 5 | Size | 0.5 | 0-1 | `DECAY` | historical shorthand only |
| 6 | Diffusion | 10 | 0-10 | `REVERB_HPF` | historical shorthand only |
| 7 | Decay | 0.54995 | 0.1-0.9999 | `REVERB_LPF` | historical shorthand only |
| 8 | Reverb high cut | 10 | 0-10 | `IN_HPF` | historical shorthand only |
| 9 | Reverb low cut | 10 | 0-10 | `IN_LPF` | historical shorthand only |
| 10 | Modulation rate | 0 | 0-1 | `FREEZE` | historical shorthand only |
| 11 | Modulation shape | 0.5 | 0-1 | `MOD_SPEED` | historical shorthand only |
| 12 | Modulation depth | 0.5 | 0-16 | `MOD_SHAPE` | historical shorthand only |
| 13 | Hold | 0 | 0-1 | `MOD_DEPTH` | historical shorthand only |
| 14 | Clear | 0 | 0-1 | `TUNED` | historical shorthand only |
| 15 | Hold toggle | 0 | 0-1 | `DIFFUSE_IN` | historical shorthand only |
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

Use the discovered param names and IDs above:

```python
reverb = patch.add("Valley", "Plateau",
    position=[0, 1],
    # id 0 = Dry level
    # id 1 = Wet level
    # id 5 = Size
    # id 7 = Decay
)
# Then set params by discovered ID:
# patch.set_param(reverb, 0, 1.0)   # Dry = 1.0
# patch.set_param(reverb, 1, 0.45)  # Wet = 0.45
# patch.set_param(reverb, 5, 0.8)   # Size = 0.8
# patch.set_param(reverb, 7, 0.75)  # Decay = 0.75
```

### Ports

**Inputs:**

| ID | Current names | Notes |
|----|---------------|-------|
| 0 | `Left` | Audio left |
| 1 | `Right` | Audio right |

**Outputs:**

| ID | Current names | Notes |
|----|---------------|-------|
| 0 | `Left` | Processed audio left |
| 1 | `Right` | Processed audio right |

### Typical patch role

Stereo room/hall reverb inserted after the main mix or on a send/return bus. Common settings in this project's patches:

- Spacious room: `DRY=1.0, WET=0.45, Size(id5)=0.8, Decay(id7)=0.75`
- Subtle tail: `DRY=1.0, WET=0.25, Size(id5)=0.5, Decay(id7)=0.55`

Connect Mix4 OUT_L/OUT_R -> Plateau IN_L/IN_R -> downstream processing or AudioInterface.

### Gotchas

- Plateau still needs a richer supplement if we want full param reconciliation. Today the params come from discovered metadata and the stereo IO names come from the supplement layer.
- CV input modulation is scaled by the corresponding CV depth param (ids 17-28). All CV depth params default to 0, so patching a CV input has no effect until the depth param is set.
- Hold (id 13) freezes the reverb tail indefinitely. Clear (id 14) flushes the buffer.
- Decay range is 0.1 to 0.9999 -- the module clamps it; do not set above 0.9999 (infinite reverb).
- `PlateauNode` routes both IN_L and IN_R to both OUT_L and OUT_R, so a mono source into IN_L alone will produce stereo output.
