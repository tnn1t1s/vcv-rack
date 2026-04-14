"""
Rings into Clouds 16 - Improved
Signal flow: Marbles (sampler) → Rings (resonator) → Clouds (texture) → Ladder (filter) → Plateau (reverb) → Audio
"""
import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder
import math

pb = PatchBuilder()

# Signal flow order: sampler first
sampler = pb.module("AudibleInstruments", "Marbles",  # VCV: "Random Sampler"
    data={'t_deja_vu': False, 'x_deja_vu': False, 't_mode': 1, 'x_mode': 0, 't_range': 1, 'x_range': 0, 'external': False, 'x_scale': 2, 'y_divider_index': 4, 'x_clock_source_internal': 0},
    **{
        "T_deja_vu": 0.0,
        "X_deja_vu": 0.0,
        "Deja_vu_probability": 0.6301,
        "Clock_rate": -0.2602,
        "Probability_distribution": 0.5,
        "T_mode": 0.0,
        "X_mode": 0.0,
        "Loop_length": 0.2831,
        "Gate_bias": 0.3627,
        "Distribution_bias": 0.5024,
        "Clock_range_mode": 0.0,
        "Output_voltage_range_mode": 0.0,
        "External_processing_mode": 0.0,
        "Randomness_amount": 0.0,
        "Smoothness": 0.8072,
    })

# Then resonator
resonator = pb.module("AudibleInstruments", "Rings",  # VCV: "Resonator"
    data={'polyphony': 0, 'model': 1, 'easterEgg': True},
    **{
        "Polyphony": 0.0,
        "Resonator_type": 0.0,
        "Frequency": 33.1808,
        "Structure": 0.6807,
        "Brightness": 0.3193,
        "Damping": 0.8916,
        "Position": 1.0,
        "Brightness_CV": 0.5067,
        "Frequency_CV": 0.0,
        "Damping_CV": 0.0,
        "Structure_CV": 0.2293,
        "Position_CV": 0.0,
    })

# Then texture synthesizer
texture = pb.module("AudibleInstruments", "Clouds",  # VCV: "Texture Synthesizer"
    data={'playback': 2, 'quality': 0, 'blendMode': 0},
    **{
        "Freeze": 0.0,
        "Mode": 0.0,
        "Load_save": 0.0,
        "Grain_position": 1.0,
        "Grain_size": 1.0,
        "Grain_pitch": 0.0,
        "Audio_input_gain": 0.3313,
        "Grain_density": 0.147,
        "Grain_texture": 0.1145,
        "Dry_wet": 1.0,
        "Stereo_spread": 1.0,
        "Feedback_amount": 0.3843,
        "Reverb_amount": 1.0,
    })

# Then ladder filter with fully open cutoff (log2(20000) = 14.2877)
ladder = pb.module("AgentRack", "Ladder",
    Cutoff=14.2877,  # Fully open: log2(20000 Hz)
    Resonance=0.0,
    Spread=0.0,
    Shape=0.0)

# Then reverb with correct hyphenated names
reverb = pb.module("Valley", "Plateau",
    **{
        "Dry_level": 0.5,
        "Wet_level": 0.5,
        "Pre-delay": 0.0,
        "Decay": 0.54,
        "Size": 0.5,
        "Diffusion": 0.5,
        "Modulation_rate": 0.1,
        "Modulation_depth": 0.2
    })

# Finally audio output
audio = pb.module("Core", "AudioInterface2",
    data={'audio': {'driver': 6, 'deviceName': 'Speakers (High Definition Audio Device)', 'sampleRate': 48000.0, 'blockSize': 256, 'inputOffset': 0, 'outputOffset': 0}, 'dcFilter': True})

# Cables - signal flow from left to right
# Marbles CV outputs to Rings modulation inputs
pb.connect(sampler.out_id(3), resonator.i.Brightness)      # out_id(3) = Y (bipolar CV)
pb.connect(sampler.out_id(3), resonator.i.Structure)       # out_id(3) = Y (bipolar CV)
pb.connect(sampler.out_id(2), resonator.i.Strum)           # out_id(2) = T₃ (gate output)

# Rings audio to Clouds
pb.connect(resonator.o.Odd, texture.i.Left)

# Marbles CV to Clouds texture parameter
pb.connect(sampler.out_id(3), texture.i.Texture)           # out_id(3) = Y (bipolar CV)

# Clouds stereo out to Ladder (left channel)
pb.connect(texture.o.Left, ladder.i.Audio)

# Ladder to Plateau reverb (correct port names: Left and Right)
pb.connect(ladder.o.Out, reverb.i.Left)
pb.connect(ladder.o.Out, reverb.i.Right)

# Plateau reverb to audio interface (need to check output names)
pb.connect(reverb.o.Left, audio.i.Left_input)
pb.connect(reverb.o.Right, audio.i.Right_input)

print(pb.status)
for w in pb.warnings: 
    print("WARN:", w)

out = "/Users/palaitis/Development/vcv-rack/patches/rings-to-clouds/16/patch.vcv"
pb.save(out)
print(f"Saved: {out}")
