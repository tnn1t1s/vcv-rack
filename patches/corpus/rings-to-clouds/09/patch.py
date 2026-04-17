"""
Rings into Clouds 09 - Improved
Signal flow: Marbles (sampler) -> Rings (resonator) -> Clouds (texture) -> Ladder (filter) -> Audio
"""
import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder
import math

pb = PatchBuilder()

# 1. SAMPLER (leftmost - source of gates and CV)
sampler = pb.module("AudibleInstruments", "Marbles",  # VCV: "Random Sampler"
    data={'t_deja_vu': False, 'x_deja_vu': False, 't_mode': 0, 'x_mode': 0, 't_range': 2, 'x_range': 0, 'external': False, 'x_scale': 2, 'y_divider_index': 8, 'x_clock_source_internal': 0},
    **{
        "T_deja_vu": 0.0,
        "X_deja_vu": 0.0,
        "Deja_vu_probability": 0.3373,
        "Clock_rate": -0.3566,
        "Probability_distribution": 0.7157,
        "T_mode": 0.0,
        "X_mode": 0.0,
        "Loop_length": 0.7084,
        "Gate_bias": 0.6614,
        "Distribution_bias": 0.3807,
        "Clock_range_mode": 0.0,
        "Output_voltage_range_mode": 0.0,
        "External_processing_mode": 0.0,
        "Randomness_amount": 0.7494,
        "Smoothness": 0.6663,
    })

# 2. RESONATOR (receives trigger and pitch from sampler)
resonator = pb.module("AudibleInstruments", "Rings",  # VCV: "Resonator"
    data={'polyphony': 0, 'model': 3, 'easterEgg': False},
    **{
        "Polyphony": 0.0,
        "Resonator_type": 0.0,
        "Frequency": 36.2169,
        "Structure": 0.5,
        "Brightness": 0.212,
        "Damping": 0.6904,
        "Position": 0.3855,
        "Brightness_CV": 0.288,
        "Frequency_CV": 0.0,
        "Damping_CV": 0.0,
        "Structure_CV": 0.0,
        "Position_CV": 0.0,
    })

# 3. TEXTURE SYNTHESIZER (receives audio from resonator)
texture = pb.module("AudibleInstruments", "Clouds",  # VCV: "Texture Synthesizer"
    data={'playback': 0, 'quality': 0, 'blendMode': 0},
    **{
        "Freeze": 0.0,
        "Mode": 0.0,
        "Load_save": 0.0,
        "Grain_position": 0.5434,
        "Grain_size": 0.7916,
        "Grain_pitch": 0.0,
        "Audio_input_gain": 0.5663,
        "Grain_density": 0.841,
        "Grain_texture": 0.5422,
        "Dry_wet": 0.7133,
        "Stereo_spread": 0.5181,
        "Feedback_amount": 0.0,
        "Reverb_amount": 0.9036,
    })

# 4. LADDER FILTER (receives stereo from texture, fully open cutoff)
# Cutoff is log2(Hz): fully open = log2(20000) = 14.2877
ladder_left = pb.module("AgentRack", "Ladder",
    Cutoff=14.2877,  # Fully open
    Resonance=0.0,
    Spread=0.0,
    Shape=0.0,
    Resonance_mode=2.0)

ladder_right = pb.module("AgentRack", "Ladder",
    Cutoff=14.2877,  # Fully open
    Resonance=0.0,
    Spread=0.0,
    Shape=0.0,
    Resonance_mode=2.0)

# 5. AUDIO OUTPUT (final sink)
audio = pb.module("Core", "AudioInterface2",
    data={'audio': {'driver': 6, 'deviceName': 'Speakers (High Definition Audio Device)', 'sampleRate': 48000.0, 'blockSize': 256, 'inputOffset': 0, 'outputOffset': 0}, 'dcFilter': True})

# WIRING (signal flow order)
# Sampler internal feedback and control
pb.connect(sampler.out_id(3), sampler.in_id(4))  # Y -> T jitter (creates variation)

# Sampler to Resonator
pb.connect(sampler.out_id(1), resonator.i.Strum)  # T₂ -> Strum (trigger)
pb.connect(sampler.out_id(5), resonator.i.Pitch__1V_oct_)  # X₂ -> Pitch (V/oct)

# Resonator to Texture
pb.connect(resonator.o.Odd, texture.i.Left)  # Odd output -> Texture left input

# Texture to Ladder filters (stereo)
pb.connect(texture.o.Left, ladder_left.i.Audio)  # Texture left -> Ladder left
pb.connect(texture.o.Right, ladder_right.i.Audio)  # Texture right -> Ladder right

# Ladder filters to Audio
pb.connect(ladder_left.o.Out, audio.i.Left_input)  # Ladder left -> Audio left
pb.connect(ladder_right.o.Out, audio.i.Right_input)  # Ladder right -> Audio right

# Status check
print(pb.status)
for w in pb.warnings:
    print("WARN:", w)

# Save
out = __file__.replace("patch.py", "patch.vcv")
pb.save(out)
print(f"Saved: {out}")
