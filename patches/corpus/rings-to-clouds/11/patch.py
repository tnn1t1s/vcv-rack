"""
Rings into Clouds 11 - Improved
Signal flow: Marbles (sampler) -> Rings (resonator) -> Clouds (texture) -> Ladder -> Plateau reverb -> Audio
"""
import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder
import math

pb = PatchBuilder()

# 1. SAMPLER (source) - declared first in signal flow
sampler = pb.module("AudibleInstruments", "Marbles",  # VCV: "Random Sampler"
    data={'t_deja_vu': False, 'x_deja_vu': False, 't_mode': 1, 'x_mode': 0, 't_range': 2, 'x_range': 0, 'external': False, 'x_scale': 5, 'y_divider_index': 4, 'x_clock_source_internal': 0},
    **{
        "T_deja_vu": 0.0,
        "X_deja_vu": 0.0,
        "Deja_vu_probability": 0.347,
        "Clock_rate": -0.5133,
        "Probability_distribution": 0.6096,
        "T_mode": 0.0,
        "X_mode": 0.0,
        "Loop_length": 0.688,
        "Gate_bias": 0.6301,
        "Distribution_bias": 0.4084,
        "Clock_range_mode": 0.0,
        "Output_voltage_range_mode": 0.0,
        "External_processing_mode": 0.0,
        "Randomness_amount": 0.0,
        "Smoothness": 0.8229,
    })

# 2. RESONATOR
resonator = pb.module("AudibleInstruments", "Rings",  # VCV: "Resonator"
    data={'polyphony': 1, 'model': 0, 'easterEgg': False},
    **{
        "Polyphony": 0.0,
        "Resonator_type": 0.0,
        "Frequency": 30.0,
        "Structure": 0.3494,
        "Brightness": 0.3349,
        "Damping": 0.7699,
        "Position": 0.1735,
        "Brightness_CV": 0.0,
        "Frequency_CV": 0.0,
        "Damping_CV": 0.0,
        "Structure_CV": 0.0,
        "Position_CV": 0.0,
    })

# 3. TEXTURE SYNTHESIZER
texture = pb.module("AudibleInstruments", "Clouds",  # VCV: "Texture Synthesizer"
    data={'playback': 0, 'quality': 0, 'blendMode': 0},
    **{
        "Freeze": 0.0,
        "Mode": 0.0,
        "Load_save": 0.0,
        "Grain_position": 0.3,
        "Grain_size": 0.7,
        "Grain_pitch": 0.0,
        "Audio_input_gain": 0.8036,
        "Grain_density": 0.3133,
        "Grain_texture": 0.6928,
        "Dry_wet": 0.7699,
        "Stereo_spread": 0.8229,
        "Feedback_amount": 0.4229,
        "Reverb_amount": 0.8193,
    })

# 4. LADDER FILTER - fully open cutoff
# Cutoff is log2(Hz), fully open = log2(20000) = 14.2877
ladder = pb.module("AgentRack", "Ladder",
    **{
        "Cutoff": math.log2(20000),  # Fully open = 14.2877
        "Resonance": 0.0,
    })

# 5. PLATEAU REVERB (using correct param names)
plateau = pb.module("Valley", "Plateau",
    **{
        "Dry_level": 0.5,
        "Wet_level": 0.5,
        "Decay": 0.65,
    })

# 6. AUDIO OUTPUT (final sink)
audio = pb.module("Core", "AudioInterface2",
    data={'audio': {'driver': 6, 'deviceName': 'Speakers (High Definition Audio Device)', 'sampleRate': 48000.0, 'blockSize': 256, 'inputOffset': 0, 'outputOffset': 0}, 'dcFilter': True})

# === WIRING ===

# Marbles self-modulation
pb.connect(sampler.out_id(3), sampler.i.T_jitter)  # Y (bipolar CV output)

# Marbles -> Rings
pb.connect(sampler.out_id(0), resonator.i.Strum)  # T₁ (gate output)
pb.connect(sampler.out_id(6), resonator.i.Pitch__1V_oct_)  # X₃ (CV output)

# Rings -> Clouds
pb.connect(resonator.o.Odd, texture.i.Left)

# Clouds -> Ladder (stereo - both channels to mono filter input)
pb.connect(texture.o.Left, ladder.i.Audio)
pb.connect(texture.o.Right, ladder.i.Audio)

# Ladder -> Plateau (stereo - duplicate mono output to both reverb inputs)
pb.connect(ladder.o.Out, plateau.i.Left)
pb.connect(ladder.o.Out, plateau.i.Right)

# Plateau -> Audio (stereo)
pb.connect(plateau.o.Left, audio.i.Left_input)
pb.connect(plateau.o.Right, audio.i.Right_input)

print(pb.status)
for w in pb.warnings: 
    print("WARN:", w)

out = __file__.replace("patch.py", "patch.vcv")
pb.save(out)
print(f"Saved: {out}")
