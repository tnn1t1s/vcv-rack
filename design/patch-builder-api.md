# PatchBuilder API Design

## Goal

A fluent API where signal routing reads left-to-right as actual signal flow,
proof state is accurate at every intermediate step, and common mistakes
(wrong attenuator, unconnected CV) are caught at compile time -- not at
"open in Rack and hear silence" time.

## Shape

```python
pb = PatchBuilder()

lfo   = pb.module("Fundamental", "LFO",  FREQ=0.4)
vco   = pb.module("Fundamental", "VCO",  FREQ=0.0, PW=0.5)
vcf   = pb.module("Fundamental", "VCF",  FREQ=0.6)
audio = pb.module("Core", "AudioInterface2")

(pb.chain(vco.SQR, vcf.i.IN)
     .fan_out(audio.i.IN_L, audio.i.IN_R, color=COLORS["green"]))

(lfo.modulates(vco.i.PWM,    attenuation=0.5, color=COLORS["blue"])
    .modulates(vcf.i.CUTOFF, attenuation=0.5, color=COLORS["purple"]))

compiled = pb.compile()   # raises PatchCompileError if not proven
compiled.save(OUT_PATH)   # returns path, no stdout
```

## Key design decisions

### chain() infers the output port

`chain(vco.SQR, vcf.i.IN)` sets tail to `vcf.i.IN` (an input). When
`fan_out()` is called, the chain asks the SignalGraph node for
`audio_out_for({in_port_id})` and picks `min(outputs)` as the source.
For VCF with IN=port 3, that gives LPF=port 0. No magic -- uses the
same routing table already declared in `modules.py`.

### Auto-attenuator via _port_attenuators

`modulates()` looks up `NODE_REGISTRY[dst].port_attenuators[port_id]`
and writes the attenuation value directly into `dst._param_values`.
Because `node.params` IS `module._param_values` (same dict, passed by
reference at node construction), the graph sees the update immediately.
The user never needs to know param IDs.

### compile() is the proof gate

`save()` calls `compile()` internally. `compile()` raises
`PatchCompileError` (with the full graph report embedded) if
`patch_proven` is False. There is no way to save an unproven patch
without explicitly bypassing compile.

### Attenuators are part of the proof

A wired CV input with a zero attenuator is not a warning -- it is
silence. `patch_proven` includes `not attenuator_errors` as condition 4.
This is correct because attenuator state is a signal flow property, not
an advisory hint.

### save() has no side effects

`CompiledPatch.save()` returns the path on success and lets exceptions
from `save_vcv` propagate. No stdout output. The caller decides whether
to print anything.

## Class map

```
PatchBuilder
  .module()       -> ModuleHandle      (adds Module + Node to graph)
  .chain()        -> SignalChain       (creates audio cables)
  .compile()      -> CompiledPatch     (validates, freezes patch dict)
  .save()         -> PatchBuilder      (compile + save, returns self)
  .proven         -> bool              (delegates to graph.patch_proven)
  .warnings       -> list[str]
  .status         -> str
  .report()       -> str
  .describe()     -> str

ModuleHandle
  .<PORT>         -> Port              (delegates to Module.__getattr__)
  .i.<PORT>       -> Port (input)
  .o.<PORT>       -> Port (output)
  .modulates()    -> ModuleHandle      (CV cable + auto-attenuator, chainable)

SignalChain
  .to()           -> SignalChain
  .fan_out()      -> SignalChain
  .tail           -> Port

CompiledPatch
  .patch_dict     -> dict
  .graph          -> SignalGraph
  .save()         -> str (path)
```
