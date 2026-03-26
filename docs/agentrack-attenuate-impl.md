# Attenuate: Full Stack Walkthrough

The simplest meaningful unit. One knob, one input, one output.
`OUT = IN × SCALE`

This walks through every layer from C++ to agent reasoning.

---

## Layer 1: Rack surface (C++)

```cpp
struct Attenuate : AgentModule {

    enum ParamId  { SCALE_PARAM,  NUM_PARAMS  };
    enum InputId  { IN_INPUT,     NUM_INPUTS  };
    enum OutputId { OUT_OUTPUT,   NUM_OUTPUTS };

    Attenuate() {
        config(NUM_PARAMS, NUM_INPUTS, NUM_OUTPUTS);
        configParam (SCALE_PARAM,  0.f, 1.f, 1.f, "Scale");
        configInput (IN_INPUT,              "In");
        configOutput(OUT_OUTPUT,            "Out");
    }

    void process(const ProcessArgs&) override {
        float scale = params[SCALE_PARAM].getValue();
        float in    = inputs[IN_INPUT].getVoltage();
        outputs[OUT_OUTPUT].setVoltage(in * scale);
    }
};
```

Three observations:

1. Enum order == configInput/configOutput order. Port IDs are deterministic.
2. `process()` is one line. The entire behavior is `OUT = IN × SCALE`.
3. No attenuverter. No hidden state. No load-time reset. Nothing to misuse.

---

## Layer 2: Contract (pure semantic)

```yaml
module_id:  "agentrack.attenuate.v1"
ensemble_role: "none"

ports:
  IN:   {signal_class: cv,  semantic_role: passthrough, direction: input}
  OUT:  {signal_class: cv,  semantic_role: passthrough, direction: output}

params:
  SCALE: {unit: normalized, scale: linear, min: 0.0, max: 1.0, default: 1.0}

guarantees:
  - "OUT = IN × SCALE at every sample"
  - "SCALE=1.0 is unity gain"
  - "SCALE=0.0 produces exactly 0V"
  - "signal class of IN is preserved at OUT"
  - "semantic role of IN is preserved at OUT"
```

The `passthrough` role is what makes this composable. It means: Attenuate
does not change the meaning of the signal, only its magnitude. An
`envelope_contour` going in is still an `envelope_contour` going out,
just smaller.

---

## Layer 3: Projection (VCV Rack context map)

```yaml
module_id:   "agentrack.attenuate.v1"
runtime:     "vcv-rack"
rack_plugin: "AgentRack"
rack_model:  "Attenuate"

port_map:
  IN:  {rack_id: 0}
  OUT: {rack_id: 0}

param_map:
  SCALE: {rack_id: 0}
```

This is the only place `rack_id` appears. The contract and the agent
never see it.

---

## The passthrough role in the compatibility graph

`passthrough` needs one addition to `ROLE_COMPAT`:

```python
ROLE_COMPAT["passthrough"] = set(ROLE_COMPAT.keys())  # drives any role
# Every role also accepts passthrough from upstream
for role in ROLE_COMPAT:
    ROLE_COMPAT[role].add("passthrough")
```

Effect: Attenuate is transparent to the compatibility graph. Any connection
valid without it is valid through it.

```
LFO.env_out (envelope_contour)
  → can_connect → Attenuate.IN (passthrough)  ✓
                → Attenuate.OUT (passthrough)
                → can_connect → VCA.cv_in (amplitude_control)  ✓
```

The semantic chain `envelope_contour → passthrough → amplitude_control`
is valid because `passthrough` passes through on both sides.

---

## Agent use

```python
# Agent wants to drive a filter cutoff with 30% of an LFO sweep

lfo_out = PortSpec(
    name="OUT", direction="output",
    signal_class="cv_bipolar", semantic_role="modulation_source",
    range_v=(-5.0, 5.0),
)

att_in  = PortSpec(name="IN",  direction="input",
                   signal_class="cv", semantic_role="passthrough")
att_out = PortSpec(name="OUT", direction="output",
                   signal_class="cv", semantic_role="passthrough",
                   range_v=(-5.0, 5.0))   # inherited from IN

filt_in = PortSpec(name="CUTOFF_CV", direction="input",
                   signal_class="cv_unipolar", semantic_role="filter_cutoff_cv")

print(can_connect(lfo_out, att_in))    # ✓ modulation_source → passthrough
print(can_connect(att_out, filt_in))   # ✓ passthrough → filter_cutoff_cv
# agent sets SCALE=0.3 → 30% of LFO reaches the filter
```

---

## What this module does NOT have

- No attenuverter (the knob IS the attenuation, directly)
- No hidden state
- No unit conversion
- No offset
- No nonlinearity
- No second channel

One thing. Done once. Done honestly.

---

## The .vcv cable/param representation

When the interpreter emits a patch containing this module, it reads
the projection and produces:

```json
{
  "id": 42,
  "plugin": "AgentRack",
  "model": "Attenuate",
  "params": [
    {"id": 0, "value": 0.3}
  ]
}
```

Cable from LFO to Attenuate:
```json
{"outputModuleId": 17, "outputId": 0,
 "inputModuleId":  42, "inputId":  0}
```

Cable from Attenuate to filter:
```json
{"outputModuleId": 42, "outputId": 0,
 "inputModuleId":  99, "inputId":  2}
```

The agent set `SCALE=0.3` in semantic terms. The interpreter read
`param_map.SCALE.rack_id = 0` from the projection and emitted
`{"id": 0, "value": 0.3}`. The agent never saw `rack_id: 0`.
