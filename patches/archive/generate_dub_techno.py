"""
Generates a dub techno patch using best-in-class free modules.

Required plugins (all free -- install via VCV Library menu):
  - Befaco          (EvenVCO oscillator)
  - Valley          (Plateau reverb)
  - AlrightDevices  (Chronoblob2 tape delay)
  - Bogaudio        (LFO, S&H, envelopes, mixer)
  - ImpromptuModular (Clocked master clock)

Usage:
    uv run python -m patches.generate_dub_techno
    uv run python -m patches.generate_dub_techno --bpm 110 --key 10 --seed 7    # Bb minor
    uv run python -m patches.generate_dub_techno --seed 99 --key 3 --scale dorian
"""

import argparse
import os
import random
import sys
from vcvpatch import Patch


# ---------------------------------------------------------------------------
# Music theory
# ---------------------------------------------------------------------------

SCALE_INTERVALS = {
    "minor":      [0, 2, 3, 5, 7, 8, 10],
    "major":      [0, 2, 4, 5, 7, 9, 11],
    "dorian":     [0, 2, 3, 5, 7, 9, 10],
    "phrygian":   [0, 1, 3, 5, 7, 8, 10],
    "minor_pent": [0, 3, 5, 7, 10],
    "blues":      [0, 3, 5, 6, 7, 10],
}


def voct(semitones_from_c4):
    return semitones_from_c4 / 12.0


def scale_notes(root, scale, octaves=2):
    intervals = SCALE_INTERVALS.get(scale, SCALE_INTERVALS["minor"])
    return [voct(root + i + o * 12) for o in range(octaves) for i in intervals]


def make_sequence(notes, length=8, rng=None, density=0.65):
    if rng is None:
        rng = random.Random()
    weights = [1.0 / (i + 1) ** 0.5 for i in range(len(notes))]
    cvs = rng.choices(notes, weights=weights, k=length)
    gates = [True] + [rng.random() < density for _ in range(length - 1)]
    for i in [0, 4]:
        if i < length:
            gates[i] = True
    return cvs, gates


# ---------------------------------------------------------------------------
# Patch builder
# ---------------------------------------------------------------------------

def build(
    bpm=115.0,
    root=0,
    scale="minor",
    detune=8.0,
    filter_freq=0.35,
    filter_res=0.45,
    reverb_size=0.85,
    reverb_decay=0.80,
    reverb_wet=0.40,
    delay_feedback=0.55,
    delay_mix=0.35,
    lfo1_rate=0.15,
    lfo2_rate=0.30,
    lfo3_rate=0.55,
    amp_attack=0.02,  amp_decay=0.25, amp_sustain=0.70, amp_release=0.50,
    filt_attack=0.01, filt_decay=0.30, filt_sustain=0.20, filt_release=0.60,
    filt_env_amt=0.45,
    seed=42,
):
    rng = random.Random(seed)
    patch = Patch(zoom=0.85)

    print(f"Generating: BPM={bpm}, key={root}, scale={scale}, seed={seed}")

    # Module HP widths -- positions are in HP units starting at 0
    # Row 0: clock(14) seq(22) osc1(8) osc2(8) vcf1(8) vcf2(8)
    #         adsr_amp(8) adsr_filt(8) vca(8) lfo1(8) lfo2(8) lfo3(8) noise(6) sh(8)
    # Row 1: reverb(18) delay(20) audio(8)

    # -- Clock (ImpromptuModular Clocked) ------------------------------------

    clock = patch.add("ImpromptuModular", "Clocked-Clkd", position=[0, 0],
                      BPM=bpm,
                      RUN=1,      # start playing immediately
                      RATIO1=4,   # CLK1 = 16th notes -> drives sequencer
                      RATIO2=2,   # CLK2 = 8th notes  -> drives delay sync
                      RATIO3=1)   # CLK3 = quarter     -> drives S&H

    # -- Sequencer -----------------------------------------------------------

    seq = patch.add("Fundamental", "SEQ3", position=[14, 0], TEMPO=bpm, RUN=1)

    notes = scale_notes(root, scale, octaves=2)
    cvs, gates = make_sequence(notes, length=8, rng=rng, density=0.65)

    print(f"  Sequence:  {[f'{v:+.2f}V' for v in cvs]}")
    print(f"  Gates:     {''.join('X' if g else '.' for g in gates)}")

    for step, cv in enumerate(cvs):
        seq._param_values[4 + step] = cv
    for step, gate in enumerate(gates):
        seq._param_values[28 + step] = 10.0 if gate else 0.0

    # -- Oscillators (Befaco EvenVCO -- analog-warm, no aliasing) -----------

    osc1 = patch.add("Befaco", "EvenVCO", position=[36, 0],
                     OCTAVE=-2, TUNE=0.0)

    osc2 = patch.add("Befaco", "EvenVCO", position=[44, 0],
                     OCTAVE=-2, TUNE=detune / 100.0)

    # -- Cascaded filters ----------------------------------------------------

    vcf1 = patch.add("Fundamental", "VCF", position=[52, 0],
                     FREQ=filter_freq, RES=filter_res, FREQ_CV=filt_env_amt)

    vcf2 = patch.add("Fundamental", "VCF", position=[60, 0],
                     FREQ=filter_freq + 0.06, RES=filter_res * 0.5,
                     FREQ_CV=filt_env_amt * 0.4)

    # -- Envelopes -----------------------------------------------------------

    adsr_amp = patch.add("Bogaudio", "Bogaudio-ADSR", position=[68, 0],
                         ATTACK=amp_attack, DECAY=amp_decay,
                         SUSTAIN=amp_sustain, RELEASE=amp_release)

    adsr_filt = patch.add("Bogaudio", "Bogaudio-ADSR", position=[76, 0],
                          ATTACK=filt_attack, DECAY=filt_decay,
                          SUSTAIN=filt_sustain, RELEASE=filt_release)

    # -- VCA -----------------------------------------------------------------

    vca = patch.add("Fundamental", "VCA", position=[84, 0])

    # -- LFOs ----------------------------------------------------------------

    lfo1 = patch.add("Bogaudio", "Bogaudio-LFO", position=[92, 0],
                     FREQ=lfo1_rate, OFFSET=5.0, SCALE=5.0)  # unipolar

    lfo2 = patch.add("Bogaudio", "Bogaudio-LFO", position=[100, 0],
                     FREQ=lfo2_rate)

    lfo3 = patch.add("Bogaudio", "Bogaudio-LFO", position=[108, 0],
                     FREQ=lfo3_rate, OFFSET=5.0, SCALE=5.0)  # unipolar tremolo

    # -- S&H on noise --------------------------------------------------------

    noise = patch.add("Fundamental", "Noise", position=[116, 0])

    sh = patch.add("Bogaudio", "Bogaudio-SampleHold", position=[122, 0])

    # -- Effects row (row 1) -------------------------------------------------

    # DRY=1 passes signal through even before reverb tail builds up
    reverb = patch.add("Valley", "Plateau", position=[0, 1],
                       DRY=1.0, WET=reverb_wet,
                       SIZE=reverb_size, DIFFUSION=0.75,
                       DECAY=reverb_decay,
                       REVERB_LPF=0.75, IN_LPF=0.85,
                       MOD_SPEED=0.5, MOD_DEPTH=0.3)

    delay = patch.add("AlrightDevices", "Chronoblob2", position=[18, 1],
                      FEEDBACK=delay_feedback, MIX=delay_mix)

    audio = patch.add("Core", "AudioInterface2", position=[38, 1])

    # -----------------------------------------------------------------------
    # WIRING
    # -----------------------------------------------------------------------

    print("  Wiring...")

    # Clock -> sequencer (16th-note clock for tight sequencing)
    patch.connect(clock.o.CLK1, seq.i.CLOCK)
    patch.connect(clock.o.RESET, seq.i.RESET)

    # Sequencer -> oscillator pitch
    patch.connect(seq.o.CV1, osc1.VOCT)
    patch.connect(seq.o.CV1, osc2.VOCT)

    # Sequencer trigger -> both envelopes
    patch.connect(seq.TRIG, adsr_amp.i.GATE)
    patch.connect(seq.TRIG, adsr_filt.i.GATE)

    # S&H: 8th-note clock samples white noise -> slow random CV
    patch.connect(clock.o.CLK2, sh.i.CLOCK1)
    patch.connect(noise.WHITE,  sh.i.IN1)

    # Both oscillators -> VCF1 (VCV sums multiple cables into one input)
    patch.connect(osc1.SAW,  vcf1.IN)
    patch.connect(osc2.SAW,  vcf1.IN)

    # Cascade filters
    patch.connect(vcf1.LPF, vcf2.IN)

    # Filter envelope -> VCF1 cutoff
    patch.connect(adsr_filt.ENV, vcf1.i.FREQ)

    # LFO1 slow triangle -> VCF1 cutoff (dub wobble)
    patch.connect(lfo1.o.TRI, vcf1.i.FREQ)

    # LFO2 sine -> VCF2 cutoff (second filter drifts)
    patch.connect(lfo2.o.SIN, vcf2.i.FREQ)

    # S&H random -> VCF2 resonance (subtle unpredictability)
    patch.connect(sh.o.OUT1, vcf2.i.RES)

    # VCF2 LPF -> VCA
    patch.connect(vcf2.LPF, vca.IN)

    # Amp envelope -> VCA
    patch.connect(adsr_amp.ENV, vca.CV)

    # LFO3 -> VCA (tremolo)
    patch.connect(lfo3.o.TRI, vca.CV)

    # VCA -> reverb (mono in, stereo processing)
    patch.connect(vca.OUT, reverb.i.IN_L)
    patch.connect(vca.OUT, reverb.i.IN_R)

    # LFO2 -> reverb size (reverb character breathes with LFO)
    patch.connect(lfo2.o.SIN, reverb.i.SIZE_CV)

    # Reverb -> delay -> audio out
    patch.connect(reverb.o.OUT_L, delay.i.IN_L)
    patch.connect(reverb.o.OUT_R, delay.i.IN_R)
    patch.connect(clock.o.CLK2,   delay.i.CLOCK)
    patch.connect(delay.o.OUT_L,  audio.i.IN_L)
    patch.connect(delay.o.OUT_R,  audio.i.IN_R)

    return patch


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bpm",    type=float, default=115)
    parser.add_argument("--key",    type=int,   default=0,       help="Root semitones from C4")
    parser.add_argument("--scale",  type=str,   default="minor", help=str(list(SCALE_INTERVALS)))
    parser.add_argument("--detune", type=float, default=8.0,     help="Oscillator detune in cents")
    parser.add_argument("--reverb", type=float, default=0.40,    help="Reverb wet 0-1")
    parser.add_argument("--seed",   type=int,   default=42)
    parser.add_argument("--out",    type=str,   default=None)
    args = parser.parse_args()

    out = args.out or f"patches/dub_techno_seed{args.seed}_bpm{int(args.bpm)}.vcv"

    patch = build(bpm=args.bpm, root=args.key, scale=args.scale,
                  detune=args.detune, reverb_wet=args.reverb, seed=args.seed)
    patch.save(out)

    print(f"\nOpen:  open \"{out}\"")
    print(f"\nVariations:")
    print("  uv run python -m patches.generate_dub_techno --seed 7  --bpm 110 --key 10")
    print("  uv run python -m patches.generate_dub_techno --seed 99 --key 3  --scale dorian")
