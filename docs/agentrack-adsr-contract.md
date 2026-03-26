# The Self-Describing Module: ADSR as a Case Study

## The problem stated plainly

A conventional ADSR module has four knobs and two jacks. To use it correctly
an agent must know:

- What units the knobs are in (seconds? normalized 0-1? log-seconds?)
- What the output voltage range is (0-10V? 0-1V? bipolar?)
- Whether retrigger restarts from zero or from current level
- Which input is required and which are optional
- What downstream modules can meaningfully receive the ENV output
- What happens if GATE goes low during the attack phase

None of this is in the patch file. None of it is discoverable by
`rack_introspect`. The agent must reverse-engineer it from source code,
documentation, or empirical testing. This is the gap.

The proposal: a module should publish all of this as a machine-readable
**contract** that the agent can load, query, and reason against.

---

## What a contract is

A contract is not documentation. Documentation is for humans to read.
A contract is a structured artifact the agent executes against:

- **Discovery**: "find me a module that covers the dynamics dimension"
- **Validation**: "is this ENV output compatible with that VCA CV input?"
- **Fitting**: "what ATTACK value gives me 50ms?" (answer: 0.05, it's linear seconds)
- **Proof**: "does my ensemble have a dynamics model?" (check ensemble_role fields)
- **Composition**: "what can legally connect to ENV?" (read compatible_destinations)

The contract makes the agent's reasoning about the module **closed** -- it
does not need to reach outside the contract to answer any of these questions.

---

## What the ADSR contract looks like

```json
{
  "plugin":  "AgentRack",
  "model":   "ADSR",
  "version": "1.0.0",

  "what_it_is": "envelope generator",
  "what_it_does": "Maps a gate signal to a time-varying amplitude trajectory.
                   Output rises during attack, falls to sustain level during
                   decay, holds while gate is high, then falls to zero during
                   release.",
  "ensemble_role": "dynamics",

  "behavioral_guarantees": [
    "output range is always [0, 10] V -- never outside this",
    "output is exactly 0V after RELEASE seconds following gate-low",
    "output reaches exactly 10V at end of attack if gate remains high",
    "retrigger on gate-high during decay restarts attack from current level, not from 0",
    "all time parameters are in seconds with linear scaling -- 0.05 means 50ms",
    "SUSTAIN is in volts -- 7.0 means 7V held level, not 70% of something"
  ],

  "params": [
    {
      "id":          0,
      "name":        "ATTACK",
      "unit":        "seconds",
      "scale":       "linear",
      "min":         0.001,
      "max":         10.0,
      "default":     0.01,
      "description": "Time to rise from 0V to 10V after gate goes high.",
      "agent_hints": {
        "percussive":  0.001,
        "plucked":     0.005,
        "standard":    0.01,
        "pad":         0.5,
        "slow_swell":  2.0
      }
    },
    {
      "id":          1,
      "name":        "DECAY",
      "unit":        "seconds",
      "scale":       "linear",
      "min":         0.001,
      "max":         10.0,
      "default":     0.3,
      "description": "Time to fall from 10V to SUSTAIN level after attack completes."
    },
    {
      "id":          2,
      "name":        "SUSTAIN",
      "unit":        "volts",
      "scale":       "linear",
      "min":         0.0,
      "max":         10.0,
      "default":     7.0,
      "description": "Level held at output while gate remains high after decay."
    },
    {
      "id":          3,
      "name":        "RELEASE",
      "unit":        "seconds",
      "scale":       "linear",
      "min":         0.001,
      "max":         10.0,
      "default":     0.2,
      "description": "Time to fall from current level to 0V after gate goes low."
    }
  ],

  "inputs": [
    {
      "id":           0,
      "name":         "GATE",
      "type":         "gate",
      "required":     true,
      "threshold_v":  1.0,
      "description":  "Gate signal. Rising edge (crossing 1V upward) starts attack.
                       Falling edge (crossing 1V downward) starts release.",
      "semantic_role": "trigger",
      "compatible_sources": [
        {"role": "gate_output",    "example": "Sequence.GATE"},
        {"role": "trigger_output", "example": "Sequence.TRIG"},
        {"role": "clock_output",   "example": "Clock.CLOCK"}
      ]
    },
    {
      "id":           1,
      "name":         "RETRIG",
      "type":         "gate",
      "required":     false,
      "description":  "Optional. Rising edge forces attack restart from current level.",
      "semantic_role": "retrigger"
    }
  ],

  "outputs": [
    {
      "id":           0,
      "name":         "ENV",
      "type":         "cv",
      "range_v":      [0, 10],
      "scale":        "linear",
      "description":  "Envelope output. Follows ADSR trajectory.",
      "semantic_role": "amplitude_envelope",
      "compatible_destinations": [
        {
          "role":    "amplitude_control",
          "example": "VCA.CV",
          "notes":   "standard use -- gates audio in proportion to envelope"
        },
        {
          "role":    "filter_modulation",
          "example": "Voice.CUTOFF",
          "notes":   "sweeps filter open on each note; route through Attenuate first
                      to control sweep depth"
        },
        {
          "role":    "any_cv_destination",
          "example": "Attenuate.IN",
          "notes":   "can drive any CV input; range is 0-10V"
        }
      ]
    }
  ],

  "composition_rules": [
    "GATE must be connected -- patch is invalid without it",
    "ENV output is 0-10V; if downstream expects 0-1V scale, route through Attenuate(SCALE=0.1)",
    "for filter sweep: connect ENV to Voice.CUTOFF through Attenuate to control sweep depth independently of envelope shape",
    "for dual use (amplitude + filter): fan ENV out to both VCA.CV and Attenuate → Voice.CUTOFF"
  ]
}
```

---

## What changes for the agent

Without contract:

```
agent reads docs → guesses ATTACK is in seconds → hopes it's linear →
sets value → patch runs → sounds wrong → debug → read source → fix
```

With contract:

```python
adsr = agent.find_model(ensemble_role="dynamics")
# → finds ADSR, reads contract

agent.fit(adsr, "ATTACK", target="percussive")
# → reads agent_hints["percussive"] = 0.001 → sets ATTACK=0.001

agent.connect(adsr.ENV, vca.CV)
# → checks: ENV.semantic_role="amplitude_envelope",
#           VCA.CV.compatible_sources includes "amplitude_envelope"
#   → valid, connects

agent.verify_ensemble()
# → checks ensemble_role coverage across all models
# → "dynamics" covered by ADSR ✓
```

The agent does not need to know anything about ADSR internals. It queries the
contract, fits against it, and the proof follows from the contract's guarantees.

---

## The two-layer structure

The contract has two distinct layers:

**Layer 1: structural** (what rack_introspect can partially discover today)
- Param IDs, ranges, defaults
- Input/output port IDs and types

**Layer 2: semantic** (what no existing tool discovers)
- What the module *means*
- What behaviors are *guaranteed*
- What connections are *compatible*
- What *role* this plays in an ensemble
- What *units* and *scale* parameters use
- What *agent_hints* map natural descriptions to values

Layer 1 is derivable from the C++ binary. Layer 2 must be authored by the
module developer and published alongside the module. It cannot be inferred
from the DSP code.

This is the authoring burden the module developer takes on in exchange for
the module being agent-composable without reverse engineering.

---

## The key invariant

A module is agent-composable if and only if an agent can:

1. **Discover** it by semantic role without knowing its name
2. **Fit** any parameter using natural-language descriptions or natural units
3. **Validate** any connection without reading source code
4. **Prove** its contribution to the ensemble from its declared role

If any of these require reading source code, checking GitHub, or empirical
testing -- the module is not agent-composable. It is human-composable only.

The contract is the mechanism that closes all four.
