"""
Rings into Clouds 07 - Improved with Ladder filter and Plateau reverb
Signal flow: Marbles -> Rings -> Clouds -> Ladder (L+R) -> Plateau -> Audio
"""
import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder
import math

pb = PatchBuilder()

# Signal flow order: sampler first, then resonator, then texture, then ladder filters, then reverb, then audio

sampler = pb.module("AudibleInstruments", "Marbles",  # VCV: "Random Sampler"
    data={'t_deja_vu': False, 'x_deja_vu': False, 't_mode': 1, 'x_mode': 0, 't_range': 2, 'x_range': 1, 'external': False, 'x_scale': 2, 'y_divider_index': 8, 'x_clock_source_internal': 0},
    **{
        "T_deja_vu": 0.0,
        "X_deja_vu": 0.0,
        "Deja_vu_probability": 0.753,
        "Clock_rate": -0.7157,
        "Probability_distribution": 0.5904,
        "T_mode": 0.0,
        "X_mode": 0.0,
        "Loop_length": 0.2867,
        "Gate_bias": 0.3578,
        "Distribution_bias": 0.5494,
        "Clock_range_mode": 0.0,
        "Output_voltage_range_mode": 0.0,
        "External_processing_mode": 0.0,
        "Randomness_amount": 0.8687,
        "Smoothness": 0.0,
    })

resonator = pb.module("AudibleInstruments", "Rings",  # VCV: "Resonator"
    data={'polyphony': 0, 'model': 0, 'easterEgg': False},
    **{
        "Polyphony": 0.0,
        "Resonator_type": 0.0,
        "Frequency": 23.494,
        "Structure": 1.0,
        "Brightness": 0.4072,
        "Damping": 0.3964,
        "Position": 0.388,
        "Brightness_CV": 0.0,
        "Frequency_CV": 0.0,
        "Damping_CV": 0.0,
        "Structure_CV": 0.0,
        "Position_CV": 0.0,
    })

texture = pb.module("AudibleInstruments", "Clouds",  # VCV: "Texture Synthesizer"
    data={'playback': 0, 'quality': 2, 'blendMode': 0},
    **{
        "Freeze": 0.0,
        "Mode": 0.0,
        "Load_save": 0.0,
        "Grain_position": 0.2253,
        "Grain_size": 0.6867,
        "Grain_pitch": 1.0,
        "Audio_input_gain": 1.0,
        "Grain_density": 0.1614,
        "Grain_texture": 0.6554,
        "Dry_wet": 0.8337,
        "Stereo_spread": 1.0,
        "Feedback_amount": 0.5072,
        "Reverb_amount": 0.8349,
    })

# Ladder filters with fully open cutoff (log2(20000) = 14.2877) - one for each channel
ladder_L = pb.module("AgentRack", "Ladder",
    **{
        "Cutoff": 14.2877,  # fully open = log2(20000)
        "Resonance": 0.0,
        "Spread": 0.0,
        "Shape": 0.0,
        "Resonance_mode": 0.0,
    })

ladder_R = pb.module("AgentRack", "Ladder",
    **{
        "Cutoff": 14.2877,  # fully open = log2(20000)
        "Resonance": 0.0,
        "Spread": 0.0,
        "Shape": 0.0,
        "Resonance_mode": 0.0,
    })

# Valley Plateau reverb
plateau = pb.module("Valley", "Plateau",
    **{
        "Dry_level": 0.65,
        "Wet_level": 0.35,
        "Size": 0.7,
        "Diffusion": 0.8,
        "Decay": 0.6,
        "Modulation_rate": 0.5,
        "Modulation_depth": 0.3,
    })

audio = pb.module("Core", "AudioInterface2",
    data={'audio': {'driver': 6, 'deviceName': 'Speakers (High Definition Audio Device)', 'sampleRate': 48000.0, 'blockSize': 256, 'inputOffset': 0, 'outputOffset': 0}, 'dcFilter': True})

# Cables - signal flow from sampler through chain to audio
# Marbles -> Rings (excitation and pitch control)
pb.connect(sampler.out_id(0), resonator.i.Strum)          # T₁ (id 0) -> Strum
pb.connect(sampler.out_id(4), resonator.i.Pitch__1V_oct_) # X₁ (id 4) -> Pitch

# Rings -> Clouds (audio and modulation)
pb.connect(resonator.o.Odd, texture.i.Left)               # Odd harmonics to Clouds
pb.connect(sampler.out_id(1), texture.i.Freeze)           # T₂ (id 1) -> Freeze
pb.connect(sampler.out_id(3), texture.i.Texture)          # Y (id 3) -> Texture

# Clouds -> Ladder (stereo filtering, fully open)
pb.connect(texture.o.Left, ladder_L.i.Audio)
pb.connect(texture.o.Right, ladder_R.i.Audio)

# Ladder -> Plateau reverb
pb.connect(ladder_L.o.Out, plateau.i.Left)
pb.connect(ladder_R.o.Out, plateau.i.Right)

# Plateau -> Audio (final output)
pb.connect(plateau.o.Left, audio.i.Left_input)
pb.connect(plateau.o.Right, audio.i.Right_input)

print(pb.status)
for w in pb.warnings: 
    print("WARN:", w)

out = "/Users/palaitis/Development/vcv-rack/patches/rings-to-clouds/07/patch.vcv"
pb.save(out)
print(f"Saved: {out}")
