"""
Rings into Clouds 24 - Rebuilt with signal flow order and AgentRack filter + reverb
"""
import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder

pb = PatchBuilder()

# Signal flow order: sampler -> resonator -> texture -> ladder -> saphire -> audio

# 1. Random Sampler (Marbles) - generates gates and CV
sampler = pb.module("AudibleInstruments", "Marbles",  # VCV: "Random Sampler"
    data={'t_deja_vu': False, 'x_deja_vu': False, 't_mode': 1, 'x_mode': 0, 't_range': 1, 'x_range': 1, 'external': False, 'x_scale': 2, 'y_divider_index': 4, 'x_clock_source_internal': 0},
    **{
        "T_deja_vu": 0.0,
        "X_deja_vu": 0.0,
        "Deja_vu_probability": 0.8398,
        "Clock_rate": 0.1253,
        "Probability_distribution": 0.4108,
        "T_mode": 0.0,
        "X_mode": 0.0,
        "Loop_length": 0.6361,
        "Gate_bias": 0.7819,
        "Distribution_bias": 0.5542,
        "Clock_range_mode": 0.0,
        "Output_voltage_range_mode": 0.0,
        "External_processing_mode": 0.0,
        "Randomness_amount": 0.306,
        "Smoothness": 0.7337,
    })

# 2. Resonator (Rings) - modal synthesis excited by Marbles
resonator = pb.module("AudibleInstruments", "Rings",  # VCV: "Resonator"
    data={'polyphony': 0, 'model': 0, 'easterEgg': False},
    **{
        "Polyphony": 0.0,
        "Resonator_type": 0.0,
        "Frequency": 30.0,
        "Structure": 0.359,
        "Brightness": 0.3686,
        "Damping": 0.5651,
        "Position": 0.3976,
        "Brightness_CV": 0.0293,
        "Frequency_CV": 0.0,
        "Damping_CV": 0.0453,
        "Structure_CV": 0.0,
        "Position_CV": -0.09,
    })

# 3. Texture Synthesizer (Clouds) - granular processing
texture = pb.module("AudibleInstruments", "Clouds",  # VCV: "Texture Synthesizer"
    data={'playback': 0, 'quality': 0, 'blendMode': 0},
    **{
        "Freeze": 0.0,
        "Mode": 0.0,
        "Load_save": 0.0,
        "Grain_position": 1.0,
        "Grain_size": 1.0,
        "Grain_pitch": 0.0,
        "Audio_input_gain": 0.8024,
        "Grain_density": 0.141,
        "Grain_texture": 0.5349,
        "Dry_wet": 0.6602,
        "Stereo_spread": 0.4831,
        "Feedback_amount": 0.0,
        "Reverb_amount": 0.8626,
    })

# 4. Ladder filter - fully open cutoff for transparent filtering
ladder = pb.module("AgentRack", "Ladder",
    Cutoff=14.2877,  # log2(20000) = fully open
    Resonance=0.0,
    Spread=0.0,
    Shape=0.0)

# 5. Saphire reverb - AgentRack convolution reverb
saphire = pb.module("AgentRack", "Saphire",
    Mix=0.35,
    Time=0.7,
    Tone=0.65,
    IR=38.0)

# 6. Audio output
audio = pb.module("Core", "AudioInterface2",
    data={'audio': {'driver': 6, 'deviceName': 'Speakers (High Definition Audio Device)', 'sampleRate': 48000.0, 'blockSize': 256, 'inputOffset': 0, 'outputOffset': 0}, 'dcFilter': True})

# Wiring: sampler -> resonator -> texture -> ladder -> saphire -> audio
pb.connect(sampler.out_id(0), resonator.i.Strum)  # T₁ (gate) -> Strum
pb.connect(sampler.out_id(6), resonator.i.Pitch__1V_oct_)  # X₃ (CV) -> Pitch

pb.connect(resonator.o.Odd, texture.i.Left)  # Resonator output -> Texture input

pb.connect(texture.o.Left, ladder.i.Audio)  # Texture left -> Ladder input
pb.connect(ladder.o.Out, saphire.i.In_L)  # Ladder -> Saphire left
pb.connect(texture.o.Right, saphire.i.In_R)  # Texture right -> Saphire right (unfiltered)

pb.connect(saphire.o.Out_L, audio.i.Left_input)  # Saphire -> Audio interface
pb.connect(saphire.o.Out_R, audio.i.Right_input)

print(pb.status)
for w in pb.warnings: print("WARN:", w)

out = "/Users/palaitis/Development/vcv-rack/patches/rings-to-clouds/24/patch.vcv"
pb.save(out)
print(f"Saved: {out}")
