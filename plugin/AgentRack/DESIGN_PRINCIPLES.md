# AgentRack Module Design Principles

Lessons learned building these modules. Apply to every new module.

---

## Audio levels

**Normalize audio at the boundary.** Divide input voltages by 5V on the way in,
multiply by 5V on the way out. All internal DSP operates in the -1..1 range.

```cpp
float in = inputs[IN_INPUT].getVoltage() / 5.f;
// ... DSP ...
outputs[OUT_OUTPUT].setVoltage(result * 5.f);
```

---

## Mix controls

**Use constant-power crossfade.** A linear `dry = 1-mix, wet = mix` blend has a
-3dB dip at center and makes the wet path sound louder or quieter depending on
its gain. The correct formula:

```cpp
float dry_g = std::cos(mix_p * float(M_PI) * 0.5f);
float wet_g = std::sin(mix_p * float(M_PI) * 0.5f);
output = dry * dry_g + wet * wet_g;
```

This keeps total power flat at every mix position.

---

## Wet signal gain (convolution, reverb, effects)

**Normalize the effect's impulse so wet ≈ dry in loudness.** For convolution
reverb, normalize the raw IR to unit energy after loading:

```cpp
float energy = 0.f;
for (int i = 0; i < len; i++)
    energy += ir_L[i] * ir_L[i] + ir_R[i] * ir_R[i];
if (energy > 0.f) {
    float scale = 1.f / std::sqrt(energy);
    for (int i = 0; i < len; i++) { ir_L[i] *= scale; ir_R[i] *= scale; }
}
```

The same principle applies to any effect with a gain that depends on a loaded
buffer or table: normalize the source, not the output.

---

## Attenuators

**Prefer explicit graph attenuation, but allow embedded modulation depth when it
is intrinsic to the module contract.** Do not add ad hoc CV attenuators just to
make a panel more convenient. Route general-purpose CV through Attenuate so the
signal graph stays explicit.

Embedded depth controls are allowed when they are part of the meaning of the
module itself, for example per-stage ADSR modulation. In those cases:

- `Attenuate` remains the behavioral reference.
- Use a shared AgentRack component/library implementation rather than inline
  one-off math.
- Keep the modulation law explicit and consistent across modules.
- Clamp after modulation in the native parameter domain.

This keeps the signal graph legible without forcing obviously intrinsic control
contracts out into a separate patching step.

---

## Shared library design

**Prefer semantic value types over utility piles or class hierarchies.** When a
shared internal library is needed, start from the smallest domain object that
matches the behavior.

Prefer:

- a small value type with explicit fields
- one or two meaningful methods
- namespacing that states the domain before the operation

Avoid:

- loose `Utils` / `Helpers` headers
- abstract base class trees when behavior does not actually differ
- generic frameworks introduced before repeated need is proven

Example:

```cpp
struct Parameter {
    const char* name;
    float base;
    float min;
    float max;

    float modulate(float depth, float cvVolts) const;
};
```

This is better than a `Parameter` ABC with subclasses such as
`CutoffFrequency`, `Mix`, or `DecayTime` when the actual behavior is still just
"bounded scalar with modulation". Keep one behavior, let meaning come from
names, manifests, and surrounding semantics.

---

## Rack IDs

**Never reorder enum entries.** Rack stores params/inputs/outputs as raw integer
IDs in patch JSON. Inserting a new entry in the middle silently corrupts every
saved patch that uses the module. Always append new entries before `NUM_PARAMS`
/ `NUM_INPUTS` / `NUM_OUTPUTS`.

```cpp
enum ParamId { EXISTING_A, EXISTING_B, NEW_PARAM, NUM_PARAMS };  // ok
enum ParamId { NEW_PARAM, EXISTING_A, EXISTING_B, NUM_PARAMS };  // breaks old patches
```

---

## Panel

- Background: skateboard deck art cropped with PIL to the interior rectangle
  (alpha-based bounds), composited on white, scaled to panel dimensions.
- Title bar: dark semi-transparent rect at top, white text, abbreviated name
  (3-4 chars max). No other labels on panel.
- No SVG panel. Use `rack::widget::Widget` + NanoVG drawing directly.

---

## Semantics

**Do not create a parallel manifest when Rack already knows the interface.**
`configParam()`, `configInput()`, and `configOutput()` are the source of truth
for module structure. The Inspector and any external agent should derive names
and live values from Rack's runtime metadata instead of a second handwritten
JSON description.

Semantics may become useful later, but only when there is clear meaning that
Rack's native metadata cannot express without ambiguity. Do not add a
`getManifest()`-style layer "just in case".

---

## Oversampling

For nonlinear DSP (wavefolder, ladder filter), oversample at 2x minimum. Run the
inner loop twice per sample, output the average:

```cpp
float out = 0.f;
for (int os = 0; os < 2; os++) {
    // ... update state ...
    out += y;
}
out *= 0.5f;
```

---

## Mono fold

Stereo modules should fold mono gracefully:

```cpp
float in_R = inputs[IN_R_INPUT].isConnected()
           ? inputs[IN_R_INPUT].getVoltage() / 5.f
           : in_L;
```
