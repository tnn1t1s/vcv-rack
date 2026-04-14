"""
Rings into Clouds 08 - Rebuilt with signal flow order and added Ladder filter
"""
import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder
import math

pb = PatchBuilder()

# Signal flow order: sampler -> resonator -> texture -> ladder -> audio

# 1. Marbles (Random Sampler) - clock and CV source
sampler = pb.module("AudibleInstruments", "Marbles",  # VCV: "Random Sampler"
    data={'t_deja_vu': False, 'x_deja_vu': False, 't_mode': 0, 'x_mode': 0, 't_range': 1, 'x_range': 0, 'external': False, 'x_scale': 2, 'y_divider_index': 8, 'x_clock_source_internal': 0},
    **{
        "T_deja_vu": 0.0,
        "X_deja_vu": 0.0,
        "Deja_vu_probability": 0.2217,
        "Clock_rate": -0.2313,
        "Probability_distribution": 0.6434,
        "T_mode": 0.0,
        "X_mode": 0.0,
        "Loop_length": 0.6482,
        "Gate_bias": 0.312,
        "Distribution_bias": 0.5795,
        "Clock_range_mode": 0.0,
        "Output_voltage_range_mode": 0.0,
        "External_processing_mode": 0.0,
        "Randomness_amount": 0.7229,
        "Smoothness": 0.7048,
    })

# 2. Rings (Resonator) - physical modeling oscillator
resonator = pb.module("AudibleInstruments", "Rings",  # VCV: "Resonator"
    data={'polyphony': 1, 'model': 0, 'easterEgg': False},
    **{
        "Polyphony": 0.0,
        "Resonator_type": 0.0,
        "Frequency": 30.0,
        "Structure": 0.3518,
        "Brightness": 0.3602,
        "Damping": 0.6783,
        "Position": 0.3301,
        "Brightness_CV": 0.0,
        "Frequency_CV": 0.0,
        "Damping_CV": 0.0,
        "Structure_CV": 0.0,
        "Position_CV": 0.0,
    })

# 3. Clouds (Texture Synthesizer) - granular processor
texture = pb.module("AudibleInstruments", "Clouds",  # VCV: "Texture Synthesizer"
    data={'playback': 1, 'quality': 2, 'blendMode': 2},
    **{
        "Freeze": 0.0,
        "Mode": 0.0,
        "Load_save": 0.0,
        "Grain_position": 0.3277,
        "Grain_size": 0.1337,
        "Grain_pitch": 1.0,
        "Audio_input_gain": 1.0,
        "Grain_density": 0.7349,
        "Grain_texture": 0.2723,
        "Dry_wet": 0.806,
        "Stereo_spread": 1.0,
        "Feedback_amount": 0.3482,
        "Reverb_amount": 0.7843,
    })

# 4. Ladder - low-pass filter (fully open cutoff = log2(20000) = 14.2877)
ladder = pb.module("AgentRack", "Ladder",
    **{
        "Cutoff": 14.2877,  # Fully open: log2(20000 Hz)
        "Resonance": 0.0,
        "Spread": 0.0,
        "Shape": 0.0,
        "Resonance_mode": 2.0,
    })

# 5. Audio Interface - output
audio = pb.module("Core", "AudioInterface2",
    data={'audio': {'driver': 6, 'deviceName': 'Speakers (High Definition Audio Device)', 'sampleRate': 48000.0, 'blockSize': 256, 'inputOffset': 0, 'outputOffset': 0}, 'dcFilter': True})

# Cables - signal flow
# Marbles -> Rings
pb.connect(sampler.out_id(0), resonator.i.Strum)  # T₁ gate output
pb.connect(sampler.out_id(4), resonator.i.Pitch__1V_oct_)  # X₁ CV output

# Rings -> Clouds
pb.connect(resonator.o.Odd, texture.i.Left)

# Clouds -> Ladder (stereo)
pb.connect(texture.o.Left, ladder.i.Audio)

# Ladder -> Audio
pb.connect(ladder.o.Out, audio.i.Left_input)
pb.connect(ladder.o.Out, audio.i.Right_input)  # Mono to stereo

print(pb.status)
for w in pb.warnings: 
    print("WARN:", w)

out = "/Users/palaitis/Development/vcv-rack/patches/rings-to-clouds/08/patch.vcv"
pb.save(out)
print(f"Saved: {out}")
