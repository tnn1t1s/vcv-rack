# Slime Child Substation: A Practical Guide to Polyrhythm, Sub-Bass, and Saturation in VCV Rack

*Using the Substation toolkit to build a patch that does things most modular setups require twice the modules to achieve*

---

If you spend time in the VCV Rack community, you'll notice a pattern: most synthesis tutorials show you how to connect a clock to a sequencer to a VCO to a filter to a VCA. The chain is always the same. It works. It sounds fine. But it rarely surprises you.

Slime Child Audio's Substation module pack breaks that pattern. It's a tightly designed toolkit where every module has an opinion about what synthesis should feel like. The PolySeq doesn't just sequence -- it creates interlocking rhythmic structures from a single clock. The SubOscillator doesn't just generate low frequencies -- it gives you mathematically pure subharmonics at exact integer divisions of your base pitch. The Envelopes module has a behavior called "semi-interruptable" that changes how you think about percussive sounds.

This guide walks through building a patch that uses all eight Substation modules. By the end you'll have a working bass synthesizer with polyrhythmic sequencing, scale quantization, and saturation that you can actually perform with.

---

## The Patch We're Building

Here's the complete signal flow before we go into detail:

```
Clock (MULT x4) ──► PolySeq (CLOCK)
                         │
                    SEQ_A (CV) ──► Quantizer ──► SubOsc V/OCT
                    TRIG1 (gate) ──► Envelopes (TRIG1 + TRIG2)

SubOsc BASE ──┐
SubOsc SUB1 ──┼──► Mixer ──► Filter ──► VCA ──► Audio Out
SubOsc SUB2 ──┘         ▲           ▲
                   Envelopes ENV2   Envelopes ENV1
                   (filter sweep)   (amplitude)
```

The Clock drives everything. The PolySeq generates both the rhythm (TRIG outputs) and the pitch material (SEQ outputs). The Quantizer constrains that pitch to a musical scale. The SubOscillator layers the pitch across three octaves. The Mixer blends those layers with saturation. The Filter shapes the tone with an envelope sweep. The VCA opens and closes with the amplitude envelope.

Nine modules total. Let's build it from the bottom up.

---

## Section 1: Syncopated Rhythm with the PolySeq

The PolySeq looks intimidating at first. It has four rhythmic dividers (DIV1 through DIV4), three output sequences (A, B, C), and a routing matrix that connects dividers to sequences. Once you understand the routing matrix, everything clicks.

### How the Dividers Work

Each divider is an independent rhythmic subdivision of the incoming clock. At DIV=1 the divider fires on every clock pulse. At DIV=3 it fires every third pulse. At DIV=4 it fires every fourth pulse.

This alone is useful for basic subdivision. But the power comes from what happens next.

### The Routing Matrix

Each divider can be independently routed to any combination of the three sequences (A, B, C). When a divider fires, it advances every sequence it's routed to. When it doesn't fire, those sequences hold.

This means sequences A, B, and C can advance at completely different rates from a single clock -- without needing three separate clocks.

**Example: a 3-against-4 polyrhythm**

Set up two dividers:
- DIV1 = 3, routed to A (fires every 3 pulses)
- DIV2 = 4, routed to B (fires every 4 pulses)

Sequence A now cycles at a 3-pulse rate. Sequence B cycles at a 4-pulse rate. They realign every 12 pulses. That's a classic 3:4 polyrhythm, and you get it without any mult cables or clock dividers.

**Creating syncopation**

Syncopation is about events landing *between* the expected beats. One approach: use a divider set to an odd number (3 or 5) against a quarter-note clock.

With the clock running at 16th notes (MULT=4):
- DIV1 = 1 fires on every 16th note (straight)
- DIV1 = 3 fires on the 1st, 4th, 7th, 10th... 16th note -- which creates an off-beat pattern that syncopates against a 4/4 grid

Try routing one divider to TRIG (for gates/drums) and another to SEQ_A (for pitch), with different divisors. The pitch and rhythm will drift apart and realign in a cycle, creating an evolving pattern from a simple setup.

### Step Values

Each sequence has four step values (A1 through A4). These are normalized voltages from -1 to +1, which after quantization become musical intervals. You're not programming specific notes here -- you're programming *relationships* between notes. The quantizer decides which actual pitches those relationships map to.

Set A1=0, A2=0.25, A3=-0.17, A4=0.42. Those four numbers, quantized to C minor, become the root, a third, a seventh below, and a fifth above -- a minor seventh arpeggio that lands on different beats depending on which divider is advancing the sequence.

**Practical tip for syncopation:** Set STEPS to a number that's out of phase with your rhythmic divider. If your divider fires every 3 pulses and your sequence has 4 steps, you get a 3:4 rotation that sounds much more alive than a locked-to-the-beat phrase.

---

## Section 2: Multi-Mode Quantization

The Quantizer is straightforward on the surface: CV in, scale-quantized CV out. But a few things make it worth understanding in detail.

### Root and Octave CV Inputs

The ROOT input (port 0) and OCT input (port 1) can be modulated with CV. This means you can transpose the scale in real time. Route a slow LFO to ROOT and the entire melody shifts through different modal colors as the LFO sweeps. Route an envelope to OCT to drop the melody by an octave on every strong beat.

In a live performance context, try connecting a MIDI-to-CV module's pitch output to ROOT. Now the scale root tracks your MIDI controller. Play a chord on the keyboard and the sequencer melody reorganizes itself around that chord's root.

### Quantizing Multiple Sources

Nothing stops you from running two different CV signals through separate quantizer instances (or the same instance at different times). A common technique: use SEQ_A for the main melody (quantized to the full scale) and SEQ_B for a rhythmically offset accent line (quantized to just the pentatonic subset of the same scale). Both are in key but they have different tonal density.

Since the PolySeq has three independent sequences, you could run all three through separate quantizer instances and have three simultaneous melodic voices, each quantized to the same root but possibly different scale modes.

### Scale Selection

The SCALE param selects from multiple scale presets. Combined with ROOT, this gives you a large vocabulary of tonal options. For bass music, minor pentatonic (no half-steps, nothing clashes) is forgiving. For more harmonic interest, Dorian mode (natural minor with a raised sixth) has a characteristic bittersweet quality that works well against sub-bass.

---

## Section 3: Sub-Octave Layering

The SubOscillator generates three simultaneous outputs from a single V/OCT input: BASE (the fundamental), SUB1 (BASE divided by SUBDIV1), and SUB2 (BASE divided by SUBDIV2).

### Integer Divisions and Why They Matter

The subdivision is always an integer. SUBDIV1=2 gives you exactly one octave below the fundamental -- frequency divided by 2. SUBDIV1=4 gives two octaves below. SUBDIV1=3 gives an octave plus a perfect fifth below (the suboctave and the 5th are the closest consonant intervals below the root).

This is different from just pitch-shifting or tuning another oscillator down. Integer division means the subharmonic is always *in tune* with the fundamental, regardless of what pitch the fundamental is playing. When the fundamental changes, the subharmonics follow correctly. There's no tuning drift.

**For bass music this is significant.** A typical bass patch uses two oscillators detuned slightly for width. The Substation approach uses mathematically locked subharmonics for depth -- one octave and two octaves below, both perfectly in phase alignment with the fundamental at the moment of attack.

### Mixing the Layers

Route all three outputs (BASE, SUB1, SUB2) into the Mixer's three channels. The level balance changes the character dramatically:

- **Equal levels (0.7, 0.7, 0.7):** full, dense, somewhat muddy in the low end
- **Tapering levels (0.8, 0.5, 0.2):** present fundamental with supporting sub-bass, sits well in a mix
- **Inverted taper (0.2, 0.5, 0.8):** emphasized sub with recessed fundamental -- good for rumble and drone
- **Only SUB1 and SUB2 (0, 0.8, 0.6):** pure sub-bass with no fundamental, sits very low in the spectrum

The SUB1 and SUB2 CV inputs allow dynamic control over the subdivision amount. Connect a sequencer CV here to change the subharmonic relationship over time -- jumping between SUBDIV=2 and SUBDIV=4 creates a rhythmic octave drop effect.

---

## Section 4: Saturation in the Mixer

The Mixer's DRIVE parameter adds harmonic saturation to the mixed signal before it hits the output. This is a soft-clip style saturation that adds odd harmonics (3rd, 5th, 7th) as the signal is pushed harder.

### Why Saturation After Mixing?

Saturating after mixing means all three sub layers are processed together. The interaction between the fundamental and the subharmonics creates intermodulation -- the saturation circuit responds to the combined signal, not just each layer individually. This produces a warmer, more complex harmonic content than saturating each oscillator separately.

With DRIVE at 0 the mixer is transparent. Around 0.2-0.3 you start to hear subtle harmonic richness, especially on transients. Past 0.5 the sound becomes visibly distorted. For sub-bass, anything above 0.3 tends to thin out the low end, so treat it like seasoning rather than the main ingredient.

### The Chain Input

The Mixer has a CHAIN input and output designed for linking multiple Mixer modules. Route the CHAIN output of one Mixer into the CHAIN input of a second Mixer and you have a 6-channel summing bus. The CHAIN GAIN param on the receiving mixer controls how much of the chained signal comes through. This is how you scale the Substation ecosystem up to larger patches without losing the saturating mixer character.

---

## Section 5: Semi-Interruptable Envelopes

Most envelope generators in modular synthesis have a specific behavior when you trigger them during an active stage: some restart from zero (retriggering), some ignore the new trigger (non-retriggering), some jump immediately to the new attack phase from wherever the envelope currently is.

The Substation Envelopes are "semi-interruptable" -- a new trigger starts a new attack from the *current envelope level*, not from zero. If the envelope is at 0.7 and you fire a new trigger, the attack starts from 0.7 and rises to the peak. If it's at 0.2, it starts from 0.2.

### Why This Sounds Natural

Human-played instruments behave this way. A plucked string that gets plucked again before it decays to silence doesn't restart from silence -- it starts from whatever energy it had remaining. The semi-interruptable behavior preserves this physical intuition.

For syncopated rhythms this is particularly important. When you're firing gates at irregular intervals (which the PolySeq encourages), some notes will fire while the previous note is still decaying. The envelope response sounds smooth and connected rather than choppy.

### HOLD Mode

Setting HOLD=1 converts the AD (attack-decay) envelope to AR (attack-release). While the gate is held high, the envelope sustains at peak. When the gate goes low, it decays. This is how most ADSR envelopes work by default, but having both modes in one module means you can have one envelope gate-sensitive (ENV1 for amplitude) and the other fire-and-forget (ENV2 for filter sweep) -- same trigger source, different behaviors.

In the demo patch, both envelopes run in AD mode from the PolySeq TRIG1 output. The amplitude envelope (EG1) has a short decay for a percussive pluck character. The filter envelope (EG2) has a longer decay for a gradual cutoff sweep that lingers after the note attack.

---

## Putting It All Together: Performance Ideas

Now that you understand each module, here are variations to try:

**Evolving polyrhythm:** Add a second divider (DIV2=5, routed to B), run SEQ_B through a second Quantizer instance, and route the result to a second audio voice. Two sequences at 4 and 5 steps will stay out of phase for 20 steps before aligning. That's five bars of material from eight parameter settings.

**Dynamic scale transposition:** Connect PolySeq SEQ_C (unquantized, raw) through a slow attenuator to the Quantizer ROOT input. As the sequence cycles, the root shifts by small CV increments, pulling the scale center with it. Over time the melody drifts through related modes without you touching anything.

**Rhythmic saturation:** Run Envelopes ENV1 into the Mixer LEVEL CV input (CV1 or CV2). Now the mix level pulses with the envelope -- the saturation kicks in harder on each attack and softens during decay. This gives a pumping, rhythmic compression-like effect entirely in the analog signal path.

**Sub-bass texture:** Modulate SUBDIV1 with PolySeq SEQ_B so the subharmonic relationship changes with the sequence. Instead of a fixed octave-below relationship, the bass shifts between different harmonic intervals on different steps. On steps where SEQ_B pushes SUBDIV1 toward 3, you get the octave+fifth below. On steps where it pushes toward 2, you get the clean octave. The melody and its harmonic shadow move in tandem.

---

## Closing Notes

The Substation modules reward the same approach all good modular synthesis rewards: start simple, understand each module's behavior deeply, then combine them in ways the individual modules didn't anticipate.

The PolySeq is the most sophisticated module in the set and also the one with the highest ceiling. The routing matrix concept -- independent rhythmic dividers each advancing sequences at their own rate -- is borrowed from polyrhythmic music traditions where multiple timelines coexist rather than one master timeline subdividing downward. Once you hear a 3-against-4-against-5 polyrhythm emerge from three divider settings and a single clock, you'll wonder why you ever needed a more complex sequencer.

The patch files for this tutorial are available in the companion repository. The `slimechild_demo.vcv` file loads all eight modules pre-wired and ready to hear.

---

*All patches were built and verified with VCV Rack 2 Free using the Substation v2.2.6 plugin.*
