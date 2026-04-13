"""
Rings into Clouds 10 - Rebuilt with signal flow order, Ladder filter, and Plateau reverb
"""
import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder
import math

pb = PatchBuilder()

# Signal flow order: sampler -> resonator -> texture -> ladder -> reverb -> audio

# 1. Sampler (Random Sampler / Marbles) - generates gates and CV
sampler = pb.module("AudibleInstruments", "Marbles",  # VCV: "Random Sampler"
    data={'t_deja_vu': False, 'x_deja_vu': False, 't_mode': 1, 'x_mode': 0, 
          't_range': 2, 'x_range': 1, 'external': False, 'x_scale': 2, 
          'y_divider_index': 4, 'x_clock_source_internal': 0},
    **{
        "T_deja_vu": 0.0,
        "X_deja_vu": 0.0,
        "Deja_vu_probability": 0.347,
        "Clock_rate": -0.5133,
        "Probability_distribution": 0.3313,
        "T_mode": 0.0,
        "X_mode": 0.0,
        "Loop_length": 0.688,
        "Gate_bias": 0.6301,
        "Distribution_bias": 0.4084,
        "Clock_range_mode": 0.0,
        "Output_voltage_range_mode": 0.0,
        "External_processing_mode": 0.0,
        "Randomness_amount": 0.512,
        "Smoothness": 0.8229,
    })

# 2. Resonator (Rings) - physical modeling resonator
resonator = pb.module("AudibleInstruments", "Rings",  # VCV: "Resonator"
    data={'polyphony': 1, 'model': 0, 'easterEgg': False},
    **{
        "Polyphony": 0.0,
        "Resonator_type": 0.0,
        "Frequency": 30.0,
        "Structure": 0.3554,
        "Brightness": 0.2904,
        "Damping": 0.9277,
        "Position": 0.0916,
        "Brightness_CV": 0.0,
        "Frequency_CV": 0.0,
        "Damping_CV": 0.0,
        "Structure_CV": 0.0,
        "Position_CV": 0.0,
    })

# 3. Texture Synthesizer (Clouds) - granular processor
texture = pb.module("AudibleInstruments", "Clouds",  # VCV: "Texture Synthesizer"
    data={'playback': 0, 'quality': 0, 'blendMode': 0},
    **{
        "Freeze": 0.0,
        "Mode": 0.0,
        "Load_save": 0.0,
        "Grain_position": 1.0,
        "Grain_size": 0.3133,
        "Grain_pitch": 0.0,
        "Audio_input_gain": 0.7012,
        "Grain_density": 0.3482,
        "Grain_texture": 0.8952,
        "Dry_wet": 0.8434,
        "Stereo_spread": 0.4807,
        "Feedback_amount": 0.353,
        "Reverb_amount": 0.9952,
    })

# 4. Ladder filter - fully open cutoff
ladder = pb.module("AgentRack", "Ladder",
    **{
        "Cutoff": 14.2877,  # Fully open: log2(20000) Hz
        "Resonance": 0.0,
        "Spread": 0.0,
        "Shape": 0.0,
        "Resonance_mode": 2.0,
    })

# 5. Plateau reverb (Valley) - Saphire alternative
reverb = pb.module("Valley", "Plateau",
    **{
        "Dry_level": 0.5,
        "Wet_level": 0.5,
    })

# 6. Audio output
audio = pb.module("Core", "AudioInterface2",
    data={'audio': {'driver': 6, 'deviceName': 'Speakers (High Definition Audio Device)', 
                    'sampleRate': 48000.0, 'blockSize': 256, 'inputOffset': 0, 'outputOffset': 0}, 
          'dcFilter': True})

# Cables - signal flow
# Sampler provides CV modulation and gates
pb.connect(sampler.out_id(3), sampler.in_id(4))  # Y -> T jitter (self-modulation)
pb.connect(sampler.out_id(1), resonator.i.Strum)  # T₂ -> Strum (gate trigger)
pb.connect(sampler.out_id(5), resonator.i.Pitch__1V_oct_)  # X₂ -> Pitch (CV)

# Audio path: resonator -> texture -> ladder -> reverb -> audio
pb.connect(resonator.o.Odd, texture.i.Left)  # Resonator output to Clouds
pb.connect(texture.o.Left, ladder.i.Audio)  # Texture left to Ladder input
pb.connect(ladder.o.Out, reverb.i.Left)  # Ladder to reverb left
pb.connect(ladder.o.Out, reverb.i.Right)  # Ladder to reverb right
pb.connect(reverb.o.Left, audio.i.Left_input)  # Reverb to audio left
pb.connect(reverb.o.Right, audio.i.Right_input)  # Reverb to audio right

print(pb.status)
for w in pb.warnings: 
    print("WARN:", w)

out = "/Users/palaitis/Development/vcv-rack/patches/rings-to-clouds/10/patch.vcv"
pb.save(out)
print(f"Saved: {out}")
