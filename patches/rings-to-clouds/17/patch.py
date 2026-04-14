"""
Rings into Clouds 17 - Rebuilt
Signal flow: Marbles (sampler) -> Rings (resonator) -> Clouds (texture) -> Ladder -> Plateau reverb -> Audio

Note: Using Plateau reverb instead of Saphire as Saphire is not in module registry.
"""
import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder

pb = PatchBuilder()

# Module 1: Marbles (Random Sampler) - source of gates and CV
sampler = pb.module("AudibleInstruments", "Marbles",  # VCV: "Random Sampler"
    data={'t_deja_vu': False, 'x_deja_vu': False, 't_mode': 0, 'x_mode': 0, 't_range': 2, 'x_range': 0, 'external': False, 'x_scale': 2, 'y_divider_index': 4, 'x_clock_source_internal': 0},
    **{
        "T_deja_vu": 0.0,
        "X_deja_vu": 0.0,
        "Deja_vu_probability": 0.8988,
        "Clock_rate": -0.6578,
        "Probability_distribution": 0.6976,
        "T_mode": 0.0,
        "X_mode": 0.0,
        "Loop_length": 0.7084,
        "Gate_bias": 0.6181,
        "Distribution_bias": 0.6325,
        "Clock_range_mode": 0.0,
        "Output_voltage_range_mode": 0.0,
        "External_processing_mode": 0.0,
        "Randomness_amount": 1.0,
        "Smoothness": 0.7843,
    })

# Module 2: Rings (Resonator) - physical modeling synth voice
resonator = pb.module("AudibleInstruments", "Rings",  # VCV: "Resonator"
    data={'polyphony': 1, 'model': 0, 'easterEgg': False},
    **{
        "Polyphony": 0.0,
        "Resonator_type": 0.0,
        "Frequency": 33.3253,
        "Structure": 0.3133,
        "Brightness": 0.3181,
        "Damping": 0.3614,
        "Position": 0.2446,
        "Brightness_CV": 0.3227,
        "Frequency_CV": 0.0,
        "Damping_CV": 0.3733,
        "Structure_CV": 0.3333,
        "Position_CV": 0.256,
    })

# Module 3: Clouds (Texture Synthesizer) - granular processor
texture = pb.module("AudibleInstruments", "Clouds",  # VCV: "Texture Synthesizer"
    data={'playback': 0, 'quality': 0, 'blendMode': 0},
    **{
        "Freeze": 0.0,
        "Mode": 0.0,
        "Load_save": 0.0,
        "Grain_position": 0.6542,
        "Grain_size": 0.7024,
        "Grain_pitch": 0.0,
        "Audio_input_gain": 0.6904,
        "Grain_density": 0.1217,
        "Grain_texture": 0.2024,
        "Dry_wet": 0.806,
        "Stereo_spread": 1.0,
        "Feedback_amount": 0.4639,
        "Reverb_amount": 0.8096,
    })

# Module 4: Ladder (Filter) - fully open for transparent pass
# Cutoff in log2(Hz): 14.2877 = log2(20000) = fully open
ladder = pb.module("AgentRack", "Ladder",
    Cutoff=14.2877,  # Fully open
    Resonance=0.0,
    Spread=0.0,
    Shape=0.0,
    Resonance_mode=2.0)

# Module 5: Plateau (Reverb) - stereo reverb from Valley
# Using raw port IDs as discovered JSON params are known to be wrong past ID 2
plateau = pb.module("Valley", "Plateau")

# Module 6: AudioInterface2 (output sink)
audio = pb.module("Core", "AudioInterface2",
    data={'audio': {'driver': 6, 'deviceName': 'Speakers (High Definition Audio Device)', 'sampleRate': 48000.0, 'blockSize': 256, 'inputOffset': 0, 'outputOffset': 0}, 'dcFilter': True})

# Wiring - signal flow order
# Marbles internal clock feedback
pb.connect(sampler.out_id(3), sampler.in_id(3))  # Y (bipolar jitter CV) -> T rate

# Marbles -> Rings: gates and pitch
pb.connect(sampler.out_id(1), resonator.i.Strum)  # T₂ (gate) -> Strum
pb.connect(sampler.out_id(5), resonator.i.Pitch__1V_oct_)  # X₂ (pitch CV) -> Pitch (1V/oct)

# Rings -> Clouds: stereo audio
pb.connect(resonator.o.Odd, texture.i.Left)
pb.connect(resonator.o.Even, texture.i.Right)

# Marbles -> Clouds: pitch modulation
pb.connect(sampler.out_id(5), texture.i.Pitch__1V_oct_)  # X₂ (pitch CV) -> Pitch (1V/oct)

# Clouds -> Ladder: left channel through filter
pb.connect(texture.o.Left, ladder.in_id(0))  # Left -> Audio input

# Ladder -> Plateau: filtered signal to reverb
pb.connect(ladder.out_id(0), plateau.i.Left)   # Out -> Left input
pb.connect(ladder.out_id(0), plateau.i.Right)  # Out -> Right input (mono to stereo)

# Plateau -> Audio: reverb output to speakers
pb.connect(plateau.o.Left, audio.i.Left_input)
pb.connect(plateau.o.Right, audio.i.Right_input)

print(pb.status)
for w in pb.warnings: 
    print("WARN:", w)

out = "/Users/palaitis/Development/vcv-rack/patches/rings-to-clouds/17/patch.vcv"
pb.save(out)
print(f"Saved: {out}")
