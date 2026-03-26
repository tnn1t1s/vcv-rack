"""
Dub techno patch -- Rack 2 recreation of /tmp/dub.vcv

Original (Rack 0.6, 44 modules) -> simplified recreation using only registered modules.

Module substitutions:
  ImpromptuModular/Clocked     -> Clocked-Clkd
  JW-Modules/GridSeq           -> SEQ3 (melody, 8-step)
  Autodafe/8x16 Trigger Seq    -> SEQ3 (drums, 8-step, all gates on)
  VultCompacts/Knock           -> Befaco/Kickall
  Autodafe/Drums-Claps         -> dropped (simplification)
  Hora-treasureFree/HiHat      -> dropped (simplification)
  Bogaudio-VCO x3              -> Fundamental/VCO x3 (same function)
  AudibleInstruments/Shades    -> Bogaudio-Mix4 (VCO summing)
  Blamsoft-XFXF35              -> Fundamental/VCF
  Befaco/Rampage               -> Bogaudio-ADSR x2 (amp + filter)
  AS/DelayPlusStereoFx         -> AlrightDevices/Chronoblob2
  Befaco/SpringReverb x2       -> Valley/Plateau
  mscHack/Mix_9_3_4            -> Bogaudio-Mix4 (final stereo mix)
  AS/TriLFO                    -> Bogaudio-LFO x3
  Core/AudioInterface          -> Core/AudioInterface2

Signal flow:
  clock CLK1 -> seq_mel (melody, half speed)
  clock CLK0 -> seq_drums (drum pattern, full speed)
  seq_drums TRIG -> kick GATE

  seq_mel TRIG -> adsr_amp GATE, adsr_filt GATE
  seq_mel CV1  -> vco1/vco2/vco3 VOCT

  vco1/2/3 SAW -> vco_mix IN1/IN2/IN3
  vco_mix OUT_L -> vcf IN
  vcf LPF -> vca IN1
  adsr_amp ENV -> vca CV (required for VCA to open)
  vca OUT1 -> reverb IN_L + IN_R
  reverb OUT_L -> delay IN_L
  reverb OUT_R -> delay IN_R
  delay OUT_L -> mixer IN1
  kick OUT   -> mixer IN2
  mixer OUT_L -> audio IN_L
  mixer OUT_R -> audio IN_R

  LFO modulation:
  lfo1 SIN -> vcf FREQ  (slow filter sweep)
  lfo2 TRI -> vcf FREQ  (medium filter texture)
  lfo3 SIN -> vca CV    ... not here, already connected to adsr; skip
  adsr_filt ENV -> vcf FREQ (envelope filter sweep)

Usage:
  cd /path/to/vcv-rack
  python3 -m patches.dub_techno_rack2
  # or
  python3 patches/dub_techno_rack2.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vcvpatch.builder import PatchBuilder
from vcvpatch.core import COLORS

OUTPUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests", "dub_techno_rack2.vcv"
)


def build() -> str:
    pb = PatchBuilder()

    # ---- Clock ---------------------------------------------------------------
    # BPM=126, CLK1 = half speed (melody), CLK0 = master (kick/drums)
    clock = pb.module("ImpromptuModular", "Clocked-Clkd",
                      BPM=126, RUN=1, RATIO1=2, RATIO2=4)

    # ---- Melodic sequencer (CLK1, half speed) --------------------------------
    seq_mel = pb.module("Fundamental", "SEQ3")

    # ---- Drum sequencer (CLK0, full speed -- all 8 gates active) -------------
    # All GATE params = 1 so every step fires, giving a kick every beat.
    gate_all = {f"GATE_{i}": 1 for i in range(8)}
    seq_drums = pb.module("Fundamental", "SEQ3", **gate_all)

    # ---- Kick drum -----------------------------------------------------------
    kick = pb.module("Befaco", "Kickall",
                     FREQ=0.3, DECAY=0.5, TONE=0.4, DRIVE=0.6)

    # ---- 3 VCOs (detuned for thickness) -------------------------------------
    # FREQ param is coarse tune (0.0 = middle C area); no OCT param in Rack 2 VCO.
    # V/OCT input handles pitch tracking; slight FREQ offset gives detuning.
    vco1 = pb.module("Fundamental", "VCO")
    vco2 = pb.module("Fundamental", "VCO", FREQ=0.03)    # slightly detuned
    vco3 = pb.module("Fundamental", "VCO", FREQ=-12.0)   # sub-bass (coarse tune down)

    # ---- VCO mixer (replacing Shades) ----------------------------------------
    vco_mix = pb.module("Bogaudio", "Bogaudio-Mix4")

    # ---- Filter (replacing Blamsoft XFXF35) ----------------------------------
    vcf = pb.module("Fundamental", "VCF", FREQ=0.35, RES=0.45)

    # ---- Amplitude envelope --------------------------------------------------
    adsr_amp = pb.module("Bogaudio", "Bogaudio-ADSR",
                         ATTACK=0.01, DECAY=0.3, SUSTAIN=0.6, RELEASE=0.5)

    # ---- Filter envelope (replacing Rampage rise output) ---------------------
    adsr_filt = pb.module("Bogaudio", "Bogaudio-ADSR",
                          ATTACK=0.01, DECAY=0.2, SUSTAIN=0.25, RELEASE=0.6)

    # ---- VCA ----------------------------------------------------------------
    vca = pb.module("Fundamental", "VCA")

    # ---- LFOs (replacing AS TriLFO) -----------------------------------------
    lfo1 = pb.module("Bogaudio", "Bogaudio-LFO", FREQ=0.13, SLOW=1)  # slow sweep
    lfo2 = pb.module("Bogaudio", "Bogaudio-LFO", FREQ=0.3,  SLOW=1)  # medium
    lfo3 = pb.module("Bogaudio", "Bogaudio-LFO", FREQ=0.07, SLOW=1)  # very slow drift

    # ---- Reverb (replacing 2x SpringReverb) ---------------------------------
    reverb = pb.module("Valley", "Plateau",
                       DRY=1.0, WET=0.45, SIZE=0.8, DECAY=0.75)

    # ---- Delay (replacing AS DelayPlusStereoFx) -----------------------------
    delay = pb.module("AlrightDevices", "Chronoblob2",
                      FEEDBACK=0.5, MIX=0.35)

    # ---- Final stereo mixer (replacing mscHack Mix_9_3_4) -------------------
    mixer = pb.module("Bogaudio", "Bogaudio-Mix4")

    # ---- Audio output -------------------------------------------------------
    audio = pb.module("Core", "AudioInterface2")

    # =========================================================================
    # WIRING
    # =========================================================================

    # ---- Clock -> sequencers ------------------------------------------------
    pb.chain(clock.o.CLK1, seq_mel.i.CLOCK)         # half speed -> melody
    pb.chain(clock.o.CLK0, seq_drums.i.CLOCK)        # full speed -> drums

    # ---- Drum seq -> kick ---------------------------------------------------
    pb.chain(seq_drums.o.TRIG, kick.i.GATE)

    # ---- Melody seq -> envelopes and VCO pitch ------------------------------
    pb.chain(seq_mel.o.TRIG, adsr_amp.i.GATE)
    pb.chain(seq_mel.o.TRIG, adsr_filt.i.GATE)
    pb.chain(seq_mel.o.CV1,  vco1.i.VOCT)
    pb.chain(seq_mel.o.CV1,  vco2.i.VOCT)
    pb.chain(seq_mel.o.CV1,  vco3.i.VOCT)

    # ---- VCOs -> VCO mixer ---------------------------------------------------
    pb.chain(vco1.o.SAW, vco_mix.i.IN1)
    pb.chain(vco2.o.SAW, vco_mix.i.IN2)
    pb.chain(vco3.o.SAW, vco_mix.i.IN3)

    # ---- VCO mix -> filter --------------------------------------------------
    pb.chain(vco_mix.o.OUT_L, vcf.i.IN)

    # ---- Filter -> VCA ------------------------------------------------------
    pb.chain(vcf.o.LPF, vca.i.IN1)

    # ---- Amp envelope -> VCA (required for VCA to open) --------------------
    pb.chain(adsr_amp.o.ENV, vca.i.CV)

    # ---- VCA -> reverb -> delay -> final mixer ------------------------------
    pb.chain(vca.o.OUT1, reverb.i.IN_L)
    pb.chain(vca.o.OUT1, reverb.i.IN_R)
    pb.chain(reverb.o.OUT_L, delay.i.IN_L)
    pb.chain(reverb.o.OUT_R, delay.i.IN_R)
    pb.chain(delay.o.OUT_L, mixer.i.IN1)

    # ---- Kick -> final mixer ------------------------------------------------
    pb.chain(kick.o.OUT, mixer.i.IN2)

    # ---- Final mixer -> audio output ----------------------------------------
    pb.chain(mixer.o.OUT_L, audio.i.IN_L)
    pb.chain(mixer.o.OUT_R, audio.i.IN_R)

    # =========================================================================
    # MODULATION
    # =========================================================================

    # Filter envelope sweep (replacing Rampage -> filter CV)
    adsr_filt.modulates(vcf.i.FREQ, via="ENV", attenuation=0.45)

    # Slow LFO -> filter cutoff (the main dub techno filter wobble)
    lfo1.modulates(vcf.i.FREQ, via="SIN", attenuation=0.35)

    # Medium LFO adds texture to the filter
    lfo2.modulates(vcf.i.FREQ, via="TRI", attenuation=0.2)

    # Very slow LFO drifts the reverb size (spaciousness modulation)
    lfo3.modulates(reverb.i.SIZE_CV, via="SIN", attenuation=0.25)

    # =========================================================================
    # PROOF & SAVE
    # =========================================================================

    print(pb.status)

    if not pb.proven:
        print("\nProof report:")
        print(pb.report())
        sys.exit(1)

    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    compiled = pb.compile()
    compiled.save(OUTPUT)
    print(f"Saved: {OUTPUT}")
    return OUTPUT


if __name__ == "__main__":
    build()
