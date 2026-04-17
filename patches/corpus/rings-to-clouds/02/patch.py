"""
Rings into Clouds 02 - Rebuilt with Ladder and Saphire
Signal flow: Marbles (sampler) → Rings (resonator) → Clouds (texture) → Ladder (filter) → Saphire (reverb) → Audio
"""
import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder
import math

pb = PatchBuilder()

# 1. Random Sampler (source) - generates gates and CV
sampler = pb.module("AudibleInstruments", "Marbles",  # VCV: "Random Sampler"
    data={'t_deja_vu': False, 'x_deja_vu': False, 't_mode': 1, 'x_mode': 0, 't_range': 2, 'x_range': 0, 'external': False, 'x_scale': 2, 'y_divider_index': 8, 'x_clock_source_internal': 0},
    **{
        "T_deja_vu": 0.0,
        "X_deja_vu": 0.0,
        "Deja_vu_probability": 0.6723,
        "Clock_rate": -0.7012,
        "Probability_distribution": 0.6506,
        "T_mode": 0.0,
        "X_mode": 0.0,
        "Loop_length": 0.7145,
        "Gate_bias": 0.7964,
        "Distribution_bias": 0.8096,
        "Clock_range_mode": 0.0,
        "Output_voltage_range_mode": 0.0,
        "External_processing_mode": 0.0,
        "Randomness_amount": 0.3783,
        "Smoothness": 0.8229,
    })

# 2. Physical modeling resonator
resonator = pb.module("AudibleInstruments", "Rings",  # VCV: "Resonator"
    data={'polyphony': 1, 'model': 1, 'easterEgg': False},
    **{
        "Polyphony": 0.0,
        "Resonator_type": 0.0,
        "Frequency": 40.56,
        "Structure": 0.399,
        "Brightness": 0.3144,
        "Damping": 0.3248,
        "Position": 0.6566,
        "Brightness_CV": 0.3637,
        "Frequency_CV": -0.27,
        "Damping_CV": 0.0453,
        "Structure_CV": 0.0,
        "Position_CV": 0.1793,
    })

# 3. Granular texture synthesizer
texture = pb.module("AudibleInstruments", "Clouds",  # VCV: "Texture Synthesizer"
    data={'playback': 0, 'quality': 0, 'blendMode': 3},
    **{
        "Freeze": 0.0,
        "Mode": 0.0,
        "Load_save": 0.0,
        "Grain_position": 0.6241,
        "Grain_size": 0.6036,
        "Grain_pitch": 0.0,
        "Audio_input_gain": 0.4831,
        "Grain_density": 0.0542,
        "Grain_texture": 0.2133,
        "Dry_wet": 0.512,
        "Stereo_spread": 0.0,
        "Feedback_amount": 0.0,
        "Reverb_amount": 0.8867,
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
pb.connect(sampler.out_id(2), resonator.i.Strum)           # T₃ (id=2) → Strum (gate, triggers resonator)
pb.connect(sampler.out_id(6), resonator.i.Pitch__1V_oct_)  # X₃ (id=6) → Pitch (random CV, 1V/oct)
pb.connect(sampler.out_id(3), resonator.i.Position)        # Y  (id=3) → Position (bipolar jitter CV)

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
