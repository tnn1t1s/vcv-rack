"""
Rings into Clouds 14 - Rebuilt with signal flow order and added Ladder + Saphire
"""
import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder

pb = PatchBuilder()

# Signal flow order: sampler -> resonator -> texture -> ladder -> saphire -> audio

# 1. Sampler (Random Sampler / Marbles) - generates gates and CV
sampler = pb.module("AudibleInstruments", "Marbles",  # VCV: "Random Sampler"
    data={'t_deja_vu': False, 'x_deja_vu': True, 't_mode': 0, 'x_mode': 0, 't_range': 2, 'x_range': 0, 'external': False, 'x_scale': 2, 'y_divider_index': 4, 'x_clock_source_internal': 0},
    **{
        "T_deja_vu": 0.0,
        "X_deja_vu": 0.0,
        "Deja_vu_probability": 0.6301,
        "Clock_rate": -0.0771,
        "Probability_distribution": 0.5012,
        "T_mode": 0.0,
        "X_mode": 0.0,
        "Loop_length": 0.2831,
        "Gate_bias": 0.4084,
        "Distribution_bias": 0.5024,
        "Clock_range_mode": 0.0,
        "Output_voltage_range_mode": 0.0,
        "External_processing_mode": 0.0,
        "Randomness_amount": 0.0,
        "Smoothness": 0.8072,
    })

# 2. Resonator (Rings) - excited by sampler gates, modulated by sampler CV
resonator = pb.module("AudibleInstruments", "Rings",  # VCV: "Resonator"
    data={'polyphony': 0, 'model': 3, 'easterEgg': False},
    **{
        "Polyphony": 0.0,
        "Resonator_type": 0.0,
        "Frequency": 30.0,
        "Structure": 0.7602,
        "Brightness": 0.0,
        "Damping": 0.1217,
        "Position": 0.0,
        "Brightness_CV": 0.0,
        "Frequency_CV": 0.0,
        "Damping_CV": 0.2373,
        "Structure_CV": 0.0,
        "Position_CV": 0.296,
    })

# 3. Texture (Clouds) - granular processing of resonator output
texture = pb.module("AudibleInstruments", "Clouds",  # VCV: "Texture Synthesizer"
    data={'playback': 0, 'quality': 0, 'blendMode': 3},
    **{
        "Freeze": 0.0,
        "Mode": 0.0,
        "Load_save": 0.0,
        "Grain_position": 0.206,
        "Grain_size": 0.6735,
        "Grain_pitch": 0.0,
        "Audio_input_gain": 0.3313,
        "Grain_density": 0.1976,
        "Grain_texture": 0.8012,
        "Dry_wet": 0.7928,
        "Stereo_spread": 0.4916,
        "Feedback_amount": 0.247,
        "Reverb_amount": 0.4277,
    })

# 4. Ladder - lowpass filter with fully open cutoff
ladder = pb.module("AgentRack", "Ladder",
    **{
        "Cutoff": 14.2877,  # Fully open: log2(20000)
        "Resonance": 0.2,
        "Spread": 0.0,
        "Shape": 0.0,
        "Resonance_mode": 2.0,
    })

# 5. Saphire - reverb for spatial depth
saphire = pb.module("AgentRack", "Saphire",
    **{
        "Mix": 0.35,
        "Time": 0.6,
        "Bend": 0.0,
        "Tone": 0.65,
        "Pre-delay": 0.1,  # Fixed: use hyphen not underscore
        "IR": 38.0,
    })

# 6. Audio Interface - output to speakers
audio = pb.module("Core", "AudioInterface2",
    data={'audio': {'driver': 6, 'deviceName': 'Speakers (High Definition Audio Device)', 'sampleRate': 48000.0, 'blockSize': 256, 'inputOffset': 0, 'outputOffset': 0}, 'dcFilter': True})

# Cables - signal flow connections with port ID labels from discovered JSON

# Sampler self-modulation
pb.connect(sampler.out_id(6), sampler.i.X_bias)  # X₃ -> X bias
pb.connect(sampler.out_id(3), sampler.i.Deja_vu)  # Y -> Deja vu

# Sampler -> Resonator: gate and pitch CV
pb.connect(sampler.out_id(2), resonator.i.Strum)  # T₃ (gate) -> Strum
pb.connect(sampler.out_id(5), resonator.i.Pitch__1V_oct_)  # X₂ (CV) -> Pitch (1V/oct)

# Resonator -> Texture: audio signal
pb.connect(resonator.o.Odd, texture.i.Left)  # Odd output -> Left input

# Texture -> Ladder: stereo audio
pb.connect(texture.o.Left, ladder.i.Audio)  # Left -> Audio input

# Ladder -> Saphire: filtered audio (mono to stereo reverb)
pb.connect(ladder.o.Out, saphire.i.In_L)  # Out -> In L
pb.connect(ladder.o.Out, saphire.i.In_R)  # Out -> In R (duplicate for stereo)

# Saphire -> Audio Interface: final stereo output
pb.connect(saphire.o.Out_L, audio.i.Left_input)  # Out L -> Left input
pb.connect(saphire.o.Out_R, audio.i.Right_input)  # Out R -> Right input

print(pb.status)
for w in pb.warnings:
    print("WARN:", w)

out = "/Users/palaitis/Development/vcv-rack/patches/rings-to-clouds/14/patch.vcv"
pb.save(out)
print(f"Saved: {out}")
