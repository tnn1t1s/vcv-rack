"""
Rings into Clouds 03 - Rebuilt
Signal flow: Marbles (sampler) → Rings (resonator) → Clouds (texture) → Ladder (filter) → Saphire (reverb) → Audio
"""
import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder
import math

pb = PatchBuilder()

# 1. Random Sampler (source) - generates gates and CV
sampler = pb.module("AudibleInstruments", "Marbles",  # VCV: "Random Sampler"
    data={'t_deja_vu': True, 'x_deja_vu': True, 't_mode': 0, 'x_mode': 0, 't_range': 1, 'x_range': 0, 'external': False, 'x_scale': 2, 'y_divider_index': 8, 'x_clock_source_internal': 0},
    **{
        "T_deja_vu": 0.0,
        "X_deja_vu": 0.0,
        "Deja_vu_probability": 0.7566,
        "Clock_rate": -0.6048,
        "Probability_distribution": 0.6578,
        "T_mode": 0.0,
        "X_mode": 0.0,
        "Loop_length": 0.294,
        "Gate_bias": 0.5,
        "Distribution_bias": 0.6518,
        "Clock_range_mode": 0.0,
        "Output_voltage_range_mode": 0.0,
        "External_processing_mode": 0.0,
        "Randomness_amount": 0.0,
        "Smoothness": 0.7988,
    })

# 2. Physical modeling resonator
resonator = pb.module("AudibleInstruments", "Rings",  # VCV: "Resonator"
    data={'polyphony': 0, 'model': 3, 'easterEgg': False},
    **{
        "Polyphony": 0.0,
        "Resonator_type": 0.0,
        "Frequency": 24.0,
        "Structure": 0.5,
        "Brightness": 0.2482,
        "Damping": 0.8855,
        "Position": 0.2807,
        "Brightness_CV": 0.0,
        "Frequency_CV": 0.0,
        "Damping_CV": 0.0,
        "Structure_CV": 0.0,
        "Position_CV": 0.0,
    })

# 3. Granular texture synthesizer
texture = pb.module("AudibleInstruments", "Clouds",  # VCV: "Texture Synthesizer"
    data={'playback': 0, 'quality': 0, 'blendMode': 0},
    **{
        "Freeze": 0.0,
        "Mode": 0.0,
        "Load_save": 0.0,
        "Grain_position": 0.2518,
        "Grain_size": 0.7048,
        "Grain_pitch": 0.6024,
        "Audio_input_gain": 1.0,
        "Grain_density": 0.306,
        "Grain_texture": 0.7012,
        "Dry_wet": 0.4952,
        "Stereo_spread": 0.494,
        "Feedback_amount": 0.5831,
        "Reverb_amount": 0.9145,
    })

# 4. Ladder filter (fully open cutoff)
ladder = pb.module("AgentRack", "Ladder",
    Cutoff=math.log2(20000),  # 20 kHz, fully open
    Resonance=0.0,
    Spread=0.0,
    Shape=0.0)

# 5. Convolution reverb
saphire = pb.module("AgentRack", "Saphire",
    Mix=0.35,
    Time=0.7,
    Bend=0.0,
    Tone=0.65,
    IR=38.0)

# 6. Audio output sink
audio = pb.module("Core", "AudioInterface2",
    data={'audio': {'driver': 6, 'deviceName': 'Speakers (High Definition Audio Device)', 'sampleRate': 48000.0, 'blockSize': 256, 'inputOffset': 0, 'outputOffset': 0}, 'dcFilter': True})

# Signal flow wiring
# Marbles CV → Rings (resonator)
pb.connect(sampler.out_id(1), resonator.i.Strum)           # T₂ (id=1) → Strum (gate)
pb.connect(sampler.out_id(5), resonator.i.Pitch__1V_oct_)  # X₂ (id=5) → Pitch (random CV, 1V/oct)

# Rings → Clouds (texture)
pb.connect(resonator.o.Odd, texture.i.Left)

# Clouds → Ladder (filter)
pb.connect(texture.o.Left, ladder.i.Audio)

# Ladder → Saphire (reverb) stereo
pb.connect(ladder.o.Out, saphire.i.In_L)
pb.connect(ladder.o.Out, saphire.i.In_R)

# Saphire → Audio (output sink)
pb.connect(saphire.o.Out_L, audio.i.Left_input)
pb.connect(saphire.o.Out_R, audio.i.Right_input)

print(pb.status)
for w in pb.warnings: 
    print("WARN:", w)

# Save to correct path
out = __file__.replace("patch.py", "patch.vcv")
pb.save(out)
print(f"Saved: {out}")
