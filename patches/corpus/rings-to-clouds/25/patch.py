"""
Rings into Clouds 25 - Improved
Signal flow: Marbles -> Rings -> Clouds -> Ladder -> Saphire -> Audio
"""
import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder

pb = PatchBuilder()

# 1. SAMPLER - Random Sampler (Marbles) generates gates and CV
sampler = pb.module("AudibleInstruments", "Marbles",  # VCV: "Random Sampler"
    data={'t_deja_vu': False, 'x_deja_vu': True, 't_mode': 1, 'x_mode': 0, 't_range': 1, 'x_range': 0, 'external': False, 'x_scale': 2, 'y_divider_index': 4, 'x_clock_source_internal': 0},
    **{
        "T_deja_vu": 0.0,
        "X_deja_vu": 0.0,
        "Deja_vu_probability": 0.5012,
        "Clock_rate": -0.6217,
        "Probability_distribution": 0.2771,
        "T_mode": 0.0,
        "X_mode": 0.0,
        "Loop_length": 0.1373,
        "Gate_bias": 0.5699,
        "Distribution_bias": 0.2566,
        "Clock_range_mode": 0.0,
        "Output_voltage_range_mode": 0.0,
        "External_processing_mode": 0.0,
        "Randomness_amount": 0.0,
        "Smoothness": 0.788,
    })

# 2. RESONATOR - Rings physical modeling resonator
resonator = pb.module("AudibleInstruments", "Rings",  # VCV: "Resonator"
    data={'polyphony': 0, 'model': 1, 'easterEgg': True},
    **{
        "Polyphony": 0.0,
        "Resonator_type": 0.0,
        "Frequency": 33.0361,
        "Structure": 0.3205,
        "Brightness": 0.1337,
        "Damping": 0.8542,
        "Position": 1.0,
        "Brightness_CV": 0.4107,
        "Frequency_CV": 0.1493,
        "Damping_CV": 0.0,
        "Structure_CV": 1.0,
        "Position_CV": 0.0,
    })

# 3. TEXTURE - Clouds granular texture synthesizer
texture = pb.module("AudibleInstruments", "Clouds",  # VCV: "Texture Synthesizer"
    data={'playback': 0, 'quality': 0, 'blendMode': 0},
    **{
        "Freeze": 0.0,
        "Mode": 0.0,
        "Load_save": 0.0,
        "Grain_position": 1.0,
        "Grain_size": 0.7699,
        "Grain_pitch": -1.0,
        "Audio_input_gain": 0.7904,
        "Grain_density": 0.7084,
        "Grain_texture": 0.3458,
        "Dry_wet": 0.7205,
        "Stereo_spread": 1.0,
        "Feedback_amount": 0.3952,
        "Reverb_amount": 0.9229,
    })

# 4. LADDER FILTER - Fully open cutoff (log2(20000) = 14.2877)
ladder = pb.module("AgentRack", "Ladder",
    Cutoff=14.2877,  # Fully open - log2(20000 Hz)
    Resonance=0.15,
    Spread=0.0,
    Shape=0.0)

# 5. SAPHIRE REVERB - AgentRack convolution reverb
saphire = pb.module("AgentRack", "Saphire",
    Mix=0.35,
    Time=0.7,
    Tone=0.65,
    IR=38.0)

# 6. AUDIO OUTPUT - Core AudioInterface2
audio = pb.module("Core", "AudioInterface2",
    data={'audio': {'driver': 6, 'deviceName': 'Speakers (High Definition Audio Device)', 'sampleRate': 48000.0, 'blockSize': 256, 'inputOffset': 0, 'outputOffset': 0}, 'dcFilter': True})

# CABLES - Signal flow order
# Marbles triggers and modulates Rings
pb.connect(sampler.out_id(0), resonator.i.Strum)           # T₁ gate output
pb.connect(sampler.out_id(5), resonator.i.Pitch__1V_oct_)  # X₂ CV output

# Rings into Clouds
pb.connect(resonator.o.Odd, texture.i.Left)

# Clouds stereo into Ladder (mono filter)
pb.connect(texture.o.Left, ladder.i.Audio)

# Ladder into Saphire stereo reverb
pb.connect(ladder.o.Out, saphire.i.In_L)
pb.connect(ladder.o.Out, saphire.i.In_R)  # Mono to stereo

# Saphire into Audio output
pb.connect(saphire.o.Out_L, audio.i.Left_input)
pb.connect(saphire.o.Out_R, audio.i.Right_input)

print(pb.status)
for w in pb.warnings: 
    print("WARN:", w)

out = __file__.replace("patch.py", "patch.vcv")
pb.save(out)
print(f"Saved: {out}")
