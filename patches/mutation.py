"""
Mutation Engine v2 -- Ab Minor Drift pattern through Plaits FM + resonant filter.

Signal flow:
  Clock(x4) → Sequencer16 CLOCK
  Seq16 CV   → Quantizer (Ab root) → Plaits VOCT
  Seq16 TRIG → Envelopes TRIG1 + TRIG2
  Seq16 TRIG → Plaits TRIGGER  (internal LPG for attack click texture)
  LFO1 (0.07Hz sine) → Plaits MORPH  (slow FM character morph)
  LFO2 (0.35Hz sine) → Filter VOCT   (pitch-tracks filter cutoff for resonant sweep)
  Envelopes ENV2      → Filter FM     (envelope also sweeps filter)
  Plaits OUT → Filter IN → VCA IN → Chronoblob2 IN_L+R → Plateau → Audio
  Envelopes ENV1 → VCA CV             (amplitude envelope)
"""

import math
import os
import sys

from vcvpatch.builder import PatchBuilder

OUTPUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests", "mutation.vcv"
)

PLUGIN = "SlimeChild-Substation"

# Ab Minor Drift pattern (from docs/patterns/sequencer16-patterns.md)
# RANGE_SW=1: STEP values are direct volts (1V/oct, C4=0V)
STEPS = [0.6626, 0.6826, 0.6861, 0.6927, 0.6667, 0.5281, 0.5092, 0.6625,
         0.6912, 0.7083, 0.6957, 0.9986, 0.7337, 0.4336, 0.6638, 0.7437]
TRIGS = [1, 0, 0, 0, 0, 0, 1, 1, 0, 1, 0, 0, 0, 1, 0, 1]


def build() -> str:
    pb = PatchBuilder()

    # --- Clock ---
    clock = pb.module(PLUGIN, "SlimeChild-Substation-Clock",
                      TEMPO=math.log2(128 / 60), RUN=1, MULT=4)

    # --- Sequencer: Ab Minor Drift pattern ---
    seq_params = {}
    for i, (pitch, trig) in enumerate(zip(STEPS, TRIGS)):
        seq_params[f"STEP{i+1}"] = pitch
        seq_params[f"TRIG{i+1}"] = float(trig)
    seq_params["LENGTH"]   = 16.0
    seq_params["RANGE_SW"] = 1.0
    seq = pb.module("CountModula", "Sequencer16", **seq_params)

    # --- Quantizer: Ab root ---
    # ROOT=8 = Ab/G# (semitones from C: C=0,C#=1,D=2,D#=3,E=4,F=5,F#=6,G=7,Ab=8)
    quant = pb.module(PLUGIN, "SlimeChild-Substation-Quantizer",
                      ROOT=8, OCTAVE=0)

    # --- Plaits: FM synthesis ---
    # MODEL=0.29 ~ two-operator FM model
    # FREQ=-2: 2 octaves below A4 base, seq VOCT adds ~0.4-0.75V → Ab2-A2 register
    # MORPH_ATTENUVERTER=0.55: LFO1 will modulate MORPH through this
    # DECAY=0.4: medium internal LPG decay (adds attack click texture when TRIGGER fires)
    plaits = pb.module("AudibleInstruments", "Plaits",
                       MODEL=0.29,
                       FREQ=-2.0,
                       HARMONICS=0.65,
                       TIMBRE=0.4,
                       MORPH=0.5,
                       MORPH_ATTENUVERTER=0.55,
                       LPG_COLOUR=0.35,
                       DECAY=0.4)

    # --- LFO1: very slow → Plaits MORPH (14s cycle, shifts FM character) ---
    lfo1 = pb.module("Bogaudio", "Bogaudio-LFO",
                     FREQ=-3.5,   # ~0.07 Hz
                     SCALE=1.0)

    # --- LFO2: medium → Filter VOCT (pitch-tracked cutoff, ~3s cycle) ---
    lfo2 = pb.module("Bogaudio", "Bogaudio-LFO",
                     FREQ=-1.2,   # ~0.35 Hz
                     SCALE=1.0)

    # --- Envelopes: ENV1 = amplitude, ENV2 = filter sweep ---
    # EG1: fast attack, medium decay → amplitude punch
    # EG2: instant attack, longer decay → sweeping filter open on each note
    envs = pb.module(PLUGIN, "SlimeChild-Substation-Envelopes",
                     EG1_ATTACK=-3.0,   # fastest attack (~8ms)
                     EG1_DECAY=-0.8,    # medium-short decay
                     EG2_ATTACK=-3.0,   # instant filter attack
                     EG2_DECAY=-0.3,    # longer filter sweep (gives notes a wah tail)
                     HOLD=0)            # AD mode (trigger-based)

    # --- Filter: ladder lowpass, resonant ---
    # FREQ=2.5: closed-ish base cutoff (~15Hz), ENV2 will sweep it open
    # RES=0.9: near self-oscillation for that "rez" character
    # FM=0.7: attenuverter open so ENV2 can drive the filter dramatically
    filt = pb.module(PLUGIN, "SlimeChild-Substation-Filter",
                     FREQ=2.5,
                     RES=0.9,
                     FM=0.7)

    # --- VCA: closed by default, ENV1 opens it ---
    # Known quirk: LEVEL resets to 1.0 on patch load -- set to 0 in GUI after opening
    vca = pb.module(PLUGIN, "SlimeChild-Substation-VCA", LEVEL=0)

    # --- Delay: short triplet bleed effect ---
    delay = pb.module("AlrightDevices", "Chronoblob2",
                      FEEDBACK=0.05,
                      TIME=0.23,
                      MIX=0.4)

    # --- Reverb: large hall ---
    reverb = pb.module("Valley", "Plateau",
                       DRY=1.0,
                       WET=0.55,
                       SIZE=0.88,
                       DECAY=0.80,
                       DIFFUSION=8.0)

    audio = pb.module("Core", "AudioInterface2")

    # --- Wiring ---

    # Clock → Sequencer
    pb.chain(clock.o.MULT, seq.i.CLOCK)

    # Pitch: Seq → Quantizer → Plaits
    pb.chain(seq.o.CV,    quant.i.IN)
    pb.chain(quant.o.OUT, plaits.i.VOCT)

    # Trigger: Seq → Plaits (LPG click) + Envelopes
    pb.chain(seq.o.TRIG, plaits.i.TRIGGER)
    pb.chain(seq.o.TRIG, envs.i.TRIG1)
    pb.chain(seq.o.TRIG, envs.i.TRIG2)

    # LFO1 → Plaits MORPH (slow FM character shift)
    pb.chain(lfo1.o.SIN, plaits.i.MORPH)

    # LFO2 → Filter VOCT (pitch-tracked cutoff sweep)
    pb.chain(lfo2.o.SIN, filt.i.VOCT)

    # ENV2 → Filter FM (envelope sweeps filter open on each note)
    pb.chain(envs.o.ENV2, filt.i.FM)

    # Audio chain: Plaits → Filter → VCA
    pb.chain(plaits.o.OUT, filt.i.IN)
    pb.chain(filt.o.OUT,   vca.i.IN)

    # ENV1 → VCA CV (amplitude envelope)
    pb.chain(envs.o.ENV1, vca.i.CV)

    # VCA → Delay (mono to both channels for stereo width from Chronoblob2)
    pb.chain(vca.o.OUT, delay.i.IN_L)
    pb.chain(vca.o.OUT, delay.i.IN_R)

    # Delay → Reverb → Audio
    pb.chain(delay.o.OUT_L,  reverb.i.IN_L)
    pb.chain(delay.o.OUT_R,  reverb.i.IN_R)
    pb.chain(reverb.o.OUT_L, audio.i.IN_L)
    pb.chain(reverb.o.OUT_R, audio.i.IN_R)

    print(pb.status)
    if not pb.proven:
        print("\nProof report:")
        print(pb.report())
        sys.exit(1)

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    patch = pb.build()
    patch.save(OUTPUT)
    print(f"Saved: {OUTPUT}")
    return OUTPUT


if __name__ == "__main__":
    build()
