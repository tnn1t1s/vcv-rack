"""
Rings into Clouds 05 - Rebuilt with AgentRack Ladder & Saphire
Signal flow: Marbles (sampler) -> Rings (resonator) -> Clouds (texture) -> Ladder (filter) -> Saphire (reverb) -> Audio
"""
import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder
import math

pb = PatchBuilder()

# Signal flow order: sampler first, then resonator, then texture, then ladder, then reverb, then audio

# 1. Random Sampler (Marbles) - source
sampler = pb.module("AudibleInstruments", "Marbles",  # VCV: "Random Sampler"
    data={'t_deja_vu': False, 'x_deja_vu': True, 't_mode': 2, 'x_mode': 0, 't_range': 2, 'x_range': 0, 'external': False, 'x_scale': 2, 'y_divider_index': 8, 'x_clock_source_internal': 0},
    **{
        "T_deja_vu": 0.0,
        "X_deja_vu": 0.0,
        "Deja_vu_probability": 0.3373,
        "Clock_rate": -0.2048,
        "Probability_distribution": 0.3386,
        "T_mode": 0.0,
        "X_mode": 0.0,
        "Loop_length": 0.7084,
        "Gate_bias": 0.3253,
        "Distribution_bias": 0.3952,
        "Clock_range_mode": 0.0,
        "Output_voltage_range_mode": 0.0,
        "External_processing_mode": 0.0,
        "Randomness_amount": 0.706,
        "Smoothness": 0.7964,
    })

# 2. Resonator (Rings) - modal resonator
resonator = pb.module("AudibleInstruments", "Rings",  # VCV: "Resonator"
    data={'polyphony': 1, 'model': 1, 'easterEgg': False},
    **{
        "Polyphony": 0.0,
        "Resonator_type": 0.0,
        "Frequency": 12.4337,
        "Structure": 0.5313,
        "Brightness": 0.1904,
        "Damping": 0.6723,
        "Position": 0.6084,
        "Brightness_CV": 0.0,
        "Frequency_CV": 0.0,
        "Damping_CV": 0.0,
        "Structure_CV": 0.0,
        "Position_CV": 0.0,
    })

# 3. Texture Synthesizer (Clouds) - granular processor
texture = pb.module("AudibleInstruments", "Clouds",  # VCV: "Texture Synthesizer"
    data={'playback': 0, 'quality': 2, 'blendMode': 3},
    **{
        "Freeze": 0.0,
        "Mode": 0.0,
        "Load_save": 0.0,
        "Grain_position": 0.0602,
        "Grain_size": 0.7253,
        "Grain_pitch": 1.012,
        "Audio_input_gain": 1.0,
        "Grain_density": 0.2072,
        "Grain_texture": 0.2602,
        "Dry_wet": 0.4904,
        "Stereo_spread": 0.4843,
        "Feedback_amount": 0.394,
        "Reverb_amount": 0.3783,
    })

# 4. Ladder filter - fully open cutoff
ladder = pb.module("AgentRack", "Ladder",
    Cutoff=14.2877,  # Fully open: log2(20000) Hz
    Resonance=0.1,
    Spread=0.0,
    Shape=0.0,
    Resonance_mode=2.0)

# 5. Saphire reverb - AgentRack convolution reverb
saphire = pb.module("AgentRack", "Saphire",
    Mix=0.35,
    Time=0.7,
    Tone=0.65,
    IR=38.0)

# 6. Audio output (sink)
audio = pb.module("Core", "AudioInterface2",
    data={'audio': {'driver': 6, 'deviceName': 'Speakers (High Definition Audio Device)', 'sampleRate': 48000.0, 'blockSize': 256, 'inputOffset': 0, 'outputOffset': 0}, 'dcFilter': True})

# Cables - signal flow order
# Marbles -> Rings
pb.connect(sampler.out_id(0), resonator.i.Strum)  # T₁ (gate output)
pb.connect(sampler.out_id(4), resonator.i.Pitch__1V_oct_)  # X₁ (voltage output)

# Rings -> Clouds
pb.connect(resonator.o.Odd, texture.i.Left)

# Clouds -> Ladder
pb.connect(texture.o.Left, ladder.i.Audio)

# Ladder -> Saphire
pb.connect(ladder.o.Out, saphire.i.In_L)
pb.connect(ladder.o.Out, saphire.i.In_R)  # Duplicate mono to stereo

# Saphire -> Audio Interface
pb.connect(saphire.o.Out_L, audio.i.Left_input)
pb.connect(saphire.o.Out_R, audio.i.Right_input)

print(pb.status)
for w in pb.warnings: 
    print("WARN:", w)

out = "/Users/palaitis/Development/vcv-rack/patches/rings-to-clouds/05/patch.vcv"
pb.save(out)
print(f"Saved: {out}")
