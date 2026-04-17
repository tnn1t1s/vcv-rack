"""
Rings into Clouds 18 - Rebuilt with Ladder and Saphire
Signal flow: Marbles (sampler) -> Rings (resonator) -> Clouds (texture) -> Ladder (filter) -> Saphire (reverb) -> Audio
"""
import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder
import math

pb = PatchBuilder()

# Signal flow order: left to right

# 1. Sampler (Marbles) - generates random CV and gates
sampler = pb.module("AudibleInstruments", "Marbles",  # VCV: "Random Sampler"
    data={'t_deja_vu': False, 'x_deja_vu': False, 't_mode': 2, 'x_mode': 0, 't_range': 2, 'x_range': 0, 'external': False, 'x_scale': 2, 'y_divider_index': 8, 'x_clock_source_internal': 0},
    **{
        "T_deja_vu": 0.0,
        "X_deja_vu": 0.0,
        "Deja_vu_probability": 0.3373,
        "Clock_rate": -0.5783,
        "Probability_distribution": 0.7157,
        "T_mode": 0.0,
        "X_mode": 0.0,
        "Loop_length": 0.7084,
        "Gate_bias": 0.1012,
        "Distribution_bias": 0.3807,
        "Clock_range_mode": 0.0,
        "Output_voltage_range_mode": 0.0,
        "External_processing_mode": 0.0,
        "Randomness_amount": 0.6928,
        "Smoothness": 0.8072,
    })

# 2. Resonator (Rings) - physical modeling synthesis
resonator = pb.module("AudibleInstruments", "Rings",  # VCV: "Resonator"
    data={'polyphony': 0, 'model': 3, 'easterEgg': False},
    **{
        "Polyphony": 0.0,
        "Resonator_type": 0.0,
        "Frequency": 38.4578,
        "Structure": 0.5096,
        "Brightness": 0.0,
        "Damping": 0.7699,
        "Position": 0.6855,
        "Brightness_CV": 0.288,
        "Frequency_CV": 0.0,
        "Damping_CV": 0.0,
        "Structure_CV": 0.0,
        "Position_CV": 0.6587,
    })

# 3. Texture (Clouds) - granular processor
texture = pb.module("AudibleInstruments", "Clouds",  # VCV: "Texture Synthesizer"
    data={'playback': 0, 'quality': 0, 'blendMode': 2},
    **{
        "Freeze": 0.0,
        "Mode": 0.0,
        "Load_save": 0.0,
        "Grain_position": 0.6771,
        "Grain_size": 0.8855,
        "Grain_pitch": -1.0,
        "Audio_input_gain": 0.5,
        "Grain_density": 0.841,
        "Grain_texture": 0.5422,
        "Dry_wet": 0.7108,
        "Stereo_spread": 1.0,
        "Feedback_amount": 0.388,
        "Reverb_amount": 1.0,
    })

# 4. Ladder filter - fully open cutoff (log2(20000) = 14.2877)
# Ladder uses polyphonic Audio input for stereo
ladder = pb.module("AgentRack", "Ladder",
    Cutoff=math.log2(20000),  # Fully open = 14.2877
    Resonance=0.0)

# 5. Saphire reverb - convolution reverb
saphire = pb.module("AgentRack", "Saphire",
    Mix=0.35,
    Time=0.7,
    Tone=0.65,
    IR=38.0)

# 6. Audio output
audio = pb.module("Core", "AudioInterface2",
    data={'audio': {'driver': 6, 'deviceName': 'Speakers (High Definition Audio Device)', 'sampleRate': 48000.0, 'blockSize': 256, 'inputOffset': 0, 'outputOffset': 0}, 'dcFilter': True})

# Cables - signal flow order with port ID labels from discovered JSON

# Marbles self-patching for modulation
pb.connect(sampler.out_id(3), sampler.i.X_bias)      # Y (bipolar jitter CV) -> X bias
pb.connect(sampler.out_id(5), sampler.i.T_rate)      # X₂ (random voltage) -> T rate
pb.connect(sampler.out_id(3), sampler.i.T_jitter)    # Y (bipolar jitter CV) -> T jitter

# Marbles -> Rings (control)
pb.connect(sampler.out_id(3), resonator.i.Position)         # Y (bipolar jitter CV) -> Position
pb.connect(sampler.out_id(0), resonator.i.Strum)            # T₁ (gate) -> Strum
pb.connect(sampler.out_id(4), resonator.i.Pitch__1V_oct_)   # X₁ (random voltage) -> Pitch (1V/oct)

# Rings -> Clouds (audio)
pb.connect(resonator.o.Odd, texture.i.Left)
pb.connect(resonator.o.Even, texture.i.Right)

# Clouds -> Ladder (audio) - polyphonic connections
pb.connect(texture.o.Left, ladder.i.Audio)    # Left channel
pb.connect(texture.o.Right, ladder.i.Audio)   # Right channel (polyphonic)

# Ladder -> Saphire (audio)
pb.connect(ladder.o.Out, saphire.i.In_L)
pb.connect(ladder.o.Out, saphire.i.In_R)

# Saphire -> Audio (final output)
pb.connect(saphire.o.Out_L, audio.i.Left_input)
pb.connect(saphire.o.Out_R, audio.i.Right_input)

print(pb.status)
for w in pb.warnings: 
    print("WARN:", w)

out = __file__.replace("patch.py", "patch.vcv")
pb.save(out)
print(f"Saved: {out}")
