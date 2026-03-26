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

**Attenuators belong in the Attenuate module, not embedded in other modules.**
Do not add a dedicated attenuator knob to a CV input just to make it convenient.
Route CV through Attenuate. This keeps modules smaller and the signal graph
explicit.

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

## Manifest / getManifest()

Every module inherits `AgentModule` and overrides `getManifest()`. The manifest
is machine-readable JSON used by the Inspector and the agent.

Watch out: raw string literals `R"(...)"` terminate at the first `)"`. If any
guarantee string contains `)"`, replace the closing paren with a comma or
restructure the sentence.

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
