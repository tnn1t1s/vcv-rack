"""
Rings into Clouds 06 - Improved
Signal flow: Marbles (sampler) -> Rings (resonator) -> Clouds (texture) -> Ladder -> Audio
"""
import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder
import math

pb = PatchBuilder()

# Signal flow order: left to right

# 1. Random Sampler (Marbles) - generates clock/gates and CV
sampler = pb.module("AudibleInstruments", "Marbles",  # VCV: "Random Sampler"
    data={'t_deja_vu': False, 'x_deja_vu': False, 't_mode': 0, 'x_mode': 0, 't_range': 2, 'x_range': 0, 'external': False, 'x_scale': 2, 'y_divider_index': 10, 'x_clock_source_internal': 0},
    **{
        "T_deja_vu": 0.0,
        "X_deja_vu": 0.0,
        "Deja_vu_probability": 0.5,
        "Clock_rate": -0.0048,
        "Probability_distribution": 0.3289,
        "T_mode": 0.0,
        "X_mode": 0.0,
        "Loop_length": 0.4157,
        "Gate_bias": 0.3783,
        "Distribution_bias": 0.3807,
        "Clock_range_mode": 0.0,
        "Output_voltage_range_mode": 0.0,
        "External_processing_mode": 0.0,
        "Randomness_amount": 1.0,
        "Smoothness": 0.0,
    })

# 2. Resonator (Rings) - modal synthesis
resonator = pb.module("AudibleInstruments", "Rings",  # VCV: "Resonator"
    data={'polyphony': 1, 'model': 0, 'easterEgg': False},
    **{
        "Polyphony": 0.0,
        "Resonator_type": 0.0,
        "Frequency": 0.0,
        "Structure": 1.0,
        "Brightness": 1.0,
        "Damping": 0.153,
        "Position": 1.0,
        "Brightness_CV": 0.0,
        "Frequency_CV": 0.0,
        "Damping_CV": 0.0,
        "Structure_CV": 1.0,
        "Position_CV": 0.0,
    })

# 3. Texture Synthesizer (Clouds) - granular processing
texture = pb.module("AudibleInstruments", "Clouds",  # VCV: "Texture Synthesizer"
    data={'playback': 0, 'quality': 0, 'blendMode': 0},
    **{
        "Freeze": 0.0,
        "Mode": 0.0,
        "Load_save": 0.0,
        "Grain_position": 0.1422,
        "Grain_size": 0.6651,
        "Grain_pitch": 0.6602,
        "Audio_input_gain": 1.0,
        "Grain_density": 0.1434,
        "Grain_texture": 0.3,
        "Dry_wet": 0.3819,
        "Stereo_spread": 0.2627,
        "Feedback_amount": 0.6398,
        "Reverb_amount": 0.8325,
    })

# 4. Ladder filter - fully open cutoff (log2(20000Hz) = 14.2877)
ladder = pb.module("AgentRack", "Ladder",
    Cutoff=14.2877,  # Fully open: log2(20000) Hz
    Resonance=0.0,
    Spread=0.0,
    Shape=0.0,
    Resonance_mode=2.0)

# 5. Audio output
audio = pb.module("Core", "AudioInterface2",
    data={'audio': {'driver': 6, 'deviceName': 'Speakers (High Definition Audio Device)', 'sampleRate': 48000.0, 'blockSize': 256, 'inputOffset': 0, 'outputOffset': 0}, 'dcFilter': True})

# Cable connections

# Sampler -> Resonator (CV control)
pb.connect(sampler.out_id(2), resonator.i.Strum)              # T₃ (gate output) -> Strum
pb.connect(sampler.out_id(6), resonator.i.Pitch__1V_oct_)     # X₃ (CV output) -> Pitch (1V/oct)
pb.connect(sampler.out_id(5), resonator.i.Structure)          # X₂ (CV output) -> Structure

# Resonator -> Texture (stereo audio)
pb.connect(resonator.o.Odd, texture.i.Left)
pb.connect(resonator.o.Even, texture.i.Right)

# Sampler -> Texture (pitch modulation)
pb.connect(sampler.out_id(3), texture.i.Pitch__1V_oct_)       # Y (bipolar CV output) -> Pitch (1V/oct)

# Texture -> Ladder (stereo audio - using left channel for mono filter)
pb.connect(texture.o.Left, ladder.i.Audio)

# Ladder -> Audio (filtered audio output, mono to stereo)
pb.connect(ladder.o.Out, audio.i.Left_input)
pb.connect(ladder.o.Out, audio.i.Right_input)

print(pb.status)
for w in pb.warnings: 
    print("WARN:", w)

out = __file__.replace("patch.py", "patch.vcv")
pb.save(out)
print(f"Saved: {out}")
