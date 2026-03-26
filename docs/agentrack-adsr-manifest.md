# AgentRack ADSR: Canonical Manifest Design

The first step the design calls for: one module, fully specified across all
five layers. If an agent can answer the test question from this manifest alone,
the design is sound.

**Test question:** "Can this module be used to create a short pluck on filter
cutoff from a sequencer gate source?"

---

## Layer 0: Port types (the true atoms)

Composition happens at ports. Before specifying the module, define the type
system ports inhabit. A port type has two parts:

**Signal class** -- what kind of electrical signal this is:

```
gate          binary, threshold at 1V, 0V or ~10V
trigger       gate with guaranteed pulse width ≤ 1ms
cv_unipolar   continuous, range [0, 10] V
cv_bipolar    continuous, range [-5, +5] V
audio         continuous, nominal ±5V, expected to be audible
```

**Semantic role** -- what the signal *means* in musical terms:

```
trigger_source        fires events; drives onset-based modules
envelope_contour      time-varying contour for shaping other signals
amplitude_control     scales audio amplitude proportionally
filter_cutoff_cv      shifts filter frequency
pitch_cv              1V/oct pitch offset
modulation_source     general-purpose modulator (role TBD by patch)
```

A port's full type is `signal_class / semantic_role`. Compatibility between
ports requires signal class match or declared conversion, and semantic role
compatibility (declared in the affordance layer, not inferred).

Examples:
```
Sequence.GATE      : gate / trigger_source
ADSR.gate_in       : gate / trigger_source         -- same type, compatible
ADSR.env_out       : cv_unipolar / envelope_contour
VCA.cv_in          : cv_unipolar / amplitude_control  -- same class, compatible role
Voice.cutoff_cv_in : cv_unipolar / filter_cutoff_cv   -- same class, compatible role
```

The agent wires by role, not by name. It does not need to know that "env_out"
is spelled that way. It needs to know that `envelope_contour` is compatible
with `amplitude_control` and `filter_cutoff_cv`.

---

## The canonical ADSR manifest

```yaml
# agentrack.adsr.v1.yaml

identity:
  module_id:   "agentrack.adsr.v1"
  name:        "ADSR Envelope"
  version:     "1.0.0"
  category:    "control_envelope"
  summary: >
    Generates a unipolar contour with attack, decay, sustain, and release
    phases in response to a gate signal. Primary use: shaping amplitude or
    filter cutoff per-note.
  ensemble_role: "dynamics"

ports:
  inputs:
    - id:            0
      name:          gate_in
      type:          gate
      semantic_role: trigger_source
      required:      true
      description: >
        High signal (>1V) starts attack phase. Falling edge starts release.
        Accepts gate or trigger; trigger treated as very short gate.

    - id:            1
      name:          retrig_in
      type:          trigger
      semantic_role: retrigger_source
      required:      false
      description: >
        Rising edge forces attack restart from current level. Use when
        legato behavior (no gate-off between notes) is needed.

  outputs:
    - id:            0
      name:          env_out
      type:          cv_unipolar
      semantic_role: envelope_contour
      range:         {min: 0.0, max: 10.0, unit: volts}
      description: >
        Envelope contour. Suitable for amplitude shaping, filter cutoff
        modulation, wavetable position, or any unipolar CV destination.

parameters:
  - id:            0
    name:          attack
    semantic_role: attack_time
    kind:          continuous
    unit:          seconds
    scale:         linear
    range:         {min: 0.001, max: 10.0}
    default:       0.01
    modulatable:   true
    description:   "Time to rise from 0V to 10V after gate onset."
    presets:
      click:       0.001
      percussive:  0.005
      standard:    0.01
      slow:        0.3
      pad:         1.5

  - id:            1
    name:          decay
    semantic_role: decay_time
    kind:          continuous
    unit:          seconds
    scale:         linear
    range:         {min: 0.001, max: 10.0}
    default:       0.2
    modulatable:   true
    description:   "Time to fall from 10V to sustain level after attack peak."
    presets:
      tight:       0.05
      pluck:       0.15
      standard:    0.2
      long:        1.0

  - id:            2
    name:          sustain
    semantic_role: sustain_level
    kind:          continuous
    unit:          normalized   # 0.0 = 0V out, 1.0 = 10V out
    scale:         linear
    range:         {min: 0.0, max: 1.0}
    default:       0.7
    modulatable:   true
    description: >
      Level held at output while gate remains high after decay.
      0.0 = fully percussive (envelope dies after decay regardless of gate).
      1.0 = no decay audible (stays at peak while gate held).

  - id:            3
    name:          release
    semantic_role: release_time
    kind:          continuous
    unit:          seconds
    scale:         linear
    range:         {min: 0.001, max: 20.0}
    default:       0.3
    modulatable:   true
    description:   "Time to fall from current level to 0V after gate goes low."
    presets:
      snap:        0.01
      short:       0.1
      standard:    0.3
      long:        1.5
      infinite:    20.0

behavior_contract:
  deterministic:   true       # same inputs always produce same outputs
  stateful:        true       # output depends on history (current phase)
  output_polarity: unipolar
  output_bounded:  true
  output_range:    {min: 0.0, max: 10.0, unit: volts}

  phase_model:
    attack:
      trigger:     "gate rising edge"
      direction:   monotonic_increasing
      start:       current_level   # retrigger: from where it is, not from 0
      end:         10.0
      duration:    attack_param_seconds
    decay:
      trigger:     "attack phase complete"
      direction:   monotonic_decreasing
      start:       10.0
      end:         sustain_level_volts
      duration:    decay_param_seconds
    sustain:
      trigger:     "decay phase complete while gate still high"
      direction:   constant
      level:       sustain_level_volts
    release:
      trigger:     "gate falling edge (any phase)"
      direction:   monotonic_decreasing
      start:       current_level
      end:         0.0
      duration:    release_param_seconds
    idle:
      trigger:     "release phase complete"
      output:      0.0
      guaranteed:  true   # output is exactly 0V in this state

  guarantees:
    - "output is always in [0, 10] V"
    - "output is exactly 0V in idle phase (not approximately)"
    - "attack phase is strictly monotonic increasing"
    - "release phase is strictly monotonic decreasing"
    - "retrigger on gate-high restarts attack from current_level, not from 0"
    - "sustain=0.0 makes envelope fully percussive -- gate duration irrelevant"

affordances:
  accepts_from:
    - role: trigger_source
      notes: "any gate or trigger source; trigger treated as very short gate"
    - role: retrigger_source
      notes: "optional retrig input only"

  can_drive:
    - role:    amplitude_control
      how:     direct
      notes:   "connect env_out to VCA cv_in; scale 0-10V controls 0-100% amplitude"

    - role:    filter_cutoff_cv
      how:     direct_or_attenuated
      notes: >
        connect env_out to filter cutoff CV. For partial sweep, route through
        Attenuate model first to set depth independently of envelope shape.

    - role:    modulation_source
      how:     attenuated
      notes:   "general modulation -- always attenuate to control depth"

  musical_uses:
    - label:   pluck
      recipe:  "attack=0.001, decay=0.1, sustain=0.0, release=0.05"
      note:    "sustain=0 makes gate duration irrelevant -- shape is attack+decay only"

    - label:   pad
      recipe:  "attack=0.5, decay=0.3, sustain=0.8, release=1.5"

    - label:   percussive_filter_sweep
      recipe:  "attack=0.001, decay=0.15, sustain=0.0, release=0.1"
      routing: "env_out → Attenuate(SCALE=0.4) → Voice.cutoff_cv_in"
      note:    "sweep depth set by Attenuate, shape set by ADSR params"

    - label:   gate_following
      recipe:  "attack=0.001, decay=0.001, sustain=1.0, release=0.01"
      note:    "output tracks gate almost exactly -- on=10V, off=0V"

probe_interface:
  actions:
    - name:      describe_affordances
      returns:   this manifest
    - name:      current_state
      returns:
        phase:   "idle | attack | decay | sustain | release"
        output:  "current output voltage"
    - name:      set_parameter
      arguments: [parameter_name, value_in_declared_units]
    - name:      compatible_destinations
      arguments: [output_port_name]
      returns:   list of compatible semantic roles and example modules
```

---

## The test case: agent reasoning trace

**Question:** "Can this module be used to create a short pluck on filter cutoff
from a sequencer gate source?"

```
agent reads manifest

step 1: does this accept from a sequencer gate source?
  affordances.accepts_from includes role=trigger_source ✓
  Sequence.GATE has type=gate, role=trigger_source ✓
  → valid upstream connection

step 2: can the output drive filter cutoff?
  affordances.can_drive includes role=filter_cutoff_cv ✓
  notes say: "route through Attenuate for partial sweep"
  → valid downstream connection

step 3: can it produce a short pluck?
  musical_uses includes label=pluck
  recipe: attack=0.001, decay=0.1, sustain=0.0, release=0.05
  behavior_contract.guarantees: sustain=0.0 makes envelope fully percussive
  → shape is attack+decay only, gate duration irrelevant
  → "short" = decay=0.1 (100ms), qualifies as pluck

step 4: what is the routing?
  Sequence.GATE → ADSR.gate_in (gate/trigger_source match ✓)
  ADSR.env_out  → Attenuate.IN (cv_unipolar passes through)
  Attenuate.OUT → Voice.cutoff_cv_in (cv_unipolar/filter_cutoff_cv ✓)

answer: YES
parameters: attack=0.001, decay=0.1, sustain=0.0, release=0.05
routing: Sequence.GATE → ADSR.gate_in
         ADSR.env_out  → Attenuate(SCALE=0.3) → Voice.cutoff_cv_in
```

The agent answered without reading source code, without knowing port IDs, and
without running the patch. Every step was closed by the manifest.

---

## What this design requires of the module author

The five layers are not symmetric in effort:

| Layer              | Who provides it    | How hard      |
|--------------------|--------------------|---------------|
| DSP implementation | module author      | existing work |
| Identity           | module author      | trivial       |
| Port semantics     | module author      | easy          |
| Parameter types    | module author      | easy          |
| Behavioral contract| module author      | **hard**      |
| Affordances        | module author      | medium        |
| Probe interface    | framework (shared) | one-time      |

The behavioral contract is the authoring burden. Stating that "attack is
monotonic increasing" and "output is exactly 0V in idle" requires the author
to think formally about their DSP, which most module authors have not done.

This is the tradeoff: the author does hard thinking once, so the agent never
has to do empirical reverse engineering again.
