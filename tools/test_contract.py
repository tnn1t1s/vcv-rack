#!/usr/bin/env python3
"""
Prove the contract system works.
Test: "Can ADSR create a short pluck on filter cutoff from a sequencer gate source?"
"""

import sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.dirname(__file__)))

from vcvpatch.contract import can_connect, plan_patch, PortSpec, ROLE_COMPAT
from vcvpatch.models.adsr import ADSR

REGISTRY = {ADSR.module_id: ADSR}

# ------------------------------------------------------------------
# Test 1: can_connect -- direct cases
# ------------------------------------------------------------------

print("=" * 60)
print("TEST 1: can_connect")
print("=" * 60)

adsr_gate_in = ADSR.port("gate_in")
adsr_env_out = ADSR.port("env_out")

# A sequencer GATE output (trigger_source → trigger_source should pass)
seq_gate_out = PortSpec(
    name="GATE", direction="output",
    signal_class="gate", semantic_role="trigger_source",
)

# A VCA amplitude control input
vca_cv_in = PortSpec(
    name="CV", direction="input",
    signal_class="cv_unipolar", semantic_role="amplitude_control",
    range_v=(0.0, 10.0),
)

# A filter cutoff CV input (same range -- no adapter needed)
filter_cutoff_in = PortSpec(
    name="CUTOFF_CV", direction="input",
    signal_class="cv_unipolar", semantic_role="filter_cutoff_cv",
    range_v=(0.0, 10.0),
)

# A filter cutoff CV input with narrow range (adapter needed)
filter_cutoff_narrow = PortSpec(
    name="CUTOFF_CV", direction="input",
    signal_class="cv_unipolar", semantic_role="filter_cutoff_cv",
    range_v=(0.0, 5.0),    # only accepts 0-5V
)

# A bad connection: audio into gate
audio_in = PortSpec(
    name="AUDIO_IN", direction="input",
    signal_class="audio", semantic_role="amplitude_control",
)

cases = [
    ("seq GATE  → ADSR gate_in",            seq_gate_out,  adsr_gate_in),
    ("ADSR env  → VCA amplitude_control",   adsr_env_out,  vca_cv_in),
    ("ADSR env  → filter_cutoff_cv",        adsr_env_out,  filter_cutoff_in),
    ("ADSR env  → filter_cutoff (narrow)",  adsr_env_out,  filter_cutoff_narrow),
    ("ADSR env  → audio_in (wrong class)",  adsr_env_out,  audio_in),
    ("ADSR env  → ADSR gate_in (bad role)", adsr_env_out,  adsr_gate_in),
]

for label, out, inp in cases:
    result = can_connect(out, inp)
    symbol = "✓" if result else "✗"
    print(f"\n  {symbol} {label}")
    print(f"    {result.explanation}")
    if result.adapter:
        print(f"    adapter: {result.adapter.type} -- {result.adapter.notes}")

# ------------------------------------------------------------------
# Test 2: plan_patch -- the pluck test
# ------------------------------------------------------------------

print("\n" + "=" * 60)
print("TEST 2: plan_patch -- 'short pluck on filter cutoff'")
print("=" * 60)

intent = {
    "description":    "short pluck on filter cutoff from sequencer gate source",
    "ensemble_roles": ["dynamics"],
    "source_roles":   ["trigger_source"],
    "target_roles":   ["filter_cutoff_cv"],
    "musical_use":    "pluck",
}

plan = plan_patch(intent, REGISTRY)

print("\nReasoning trace:")
for line in plan.explanation:
    print(f"  {line}")

print(f"\nModules:  {plan.modules}")
print(f"\nWires:")
for w in plan.wires:
    adapter_note = f"  [adapter: {w.adapter.type}]" if w.adapter else ""
    print(f"  {w.from_module}.{w.from_port} → {w.to_module}.{w.to_port}{adapter_note}")

print(f"\nParams:")
for p in plan.params:
    print(f"  {p.module}: {p.param} = {p.value} {p.unit}  ({p.reason})")

print(f"\nGaps: {plan.gaps if plan.gaps else 'none'}")

print("\n" + "=" * 60)
verdict = "PASS" if not plan.gaps and plan.modules and plan.params else "FAIL"
print(f"VERDICT: {verdict}")
print("=" * 60)

# ------------------------------------------------------------------
# Test 3: role compatibility graph -- spot checks
# ------------------------------------------------------------------

print("\nTEST 3: role compatibility graph")
print(f"  envelope_contour can drive: {sorted(ROLE_COMPAT['envelope_contour'])}")
print(f"  trigger_source   can drive: {sorted(ROLE_COMPAT['trigger_source'])}")
print(f"  modulation_source can drive: {sorted(ROLE_COMPAT['modulation_source'])}")

# ------------------------------------------------------------------
# Test 4: passthrough transparency (Attenuate in the chain)
# LFO.OUT (modulation_source) → Attenuate.IN (passthrough)
#                             → Attenuate.OUT (passthrough)
#                             → Filter.CUTOFF_CV (filter_cutoff_cv)
# Both hops must be valid; chain must equal direct LFO→Filter connection.
# ------------------------------------------------------------------

from vcvpatch.models.attenuate import Attenuate

print("\n" + "=" * 60)
print("TEST 4: passthrough transparency")
print("=" * 60)

lfo_out = PortSpec(
    name="OUT", direction="output",
    signal_class="cv_bipolar", semantic_role="modulation_source",
    range_v=(-5.0, 5.0),
)
att_in  = Attenuate.port("IN")
att_out = Attenuate.port("OUT")
filt_in = PortSpec(
    name="CUTOFF_CV", direction="input",
    signal_class="cv_unipolar", semantic_role="filter_cutoff_cv",
    range_v=(0.0, 10.0),
)

# Override signal_class on att_out to match what passes through (bipolar LFO)
# In practice the interpreter tracks this; here we construct it manually.
att_out_realized = PortSpec(
    name="OUT", direction="output",
    signal_class="cv_bipolar", semantic_role="passthrough",
    range_v=(-5.0, 5.0),
)

hop1 = can_connect(lfo_out, att_in)
hop2 = can_connect(att_out_realized, filt_in)
direct = can_connect(lfo_out, filt_in)

print(f"\n  LFO.OUT (modulation_source) → Attenuate.IN (passthrough)")
symbol = "✓" if hop1 else "✗"
print(f"    {symbol} {hop1.explanation}")

print(f"\n  Attenuate.OUT (passthrough) → Filter.CUTOFF_CV (filter_cutoff_cv)")
symbol = "✓" if hop2 else "✗"
print(f"    {symbol} {hop2.explanation}")

print(f"\n  Direct: LFO.OUT → Filter.CUTOFF_CV (reference)")
symbol = "✓" if direct else "✗"
print(f"    {symbol} {direct.explanation}")

chain_valid = bool(hop1) and bool(hop2)
direct_valid = bool(direct)
consistency = chain_valid == direct_valid

print(f"\n  Chain valid:  {chain_valid}")
print(f"  Direct valid: {direct_valid}")
print(f"  Consistent:   {consistency}")

verdict4 = "PASS" if chain_valid and consistency else "FAIL"
print(f"\n  VERDICT: {verdict4} -- passthrough is {'transparent' if consistency else 'NOT TRANSPARENT'}")
