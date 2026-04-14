"""
Rings into Clouds 22
"""
import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder

pb = PatchBuilder()

resonator = pb.module("AudibleInstruments", "Rings",  # VCV: "Resonator"
    data={'polyphony': 1, 'model': 1, 'easterEgg': False},
    **{
        "Polyphony": 0.0,
        "Resonator_type": 0.0,
        "Frequency": 39.3976,
        "Structure": 0.6301,
        "Brightness": 0.6301,
        "Damping": 0.5735,
        "Position": 0.6675,
        "Brightness_CV": 0.0293,
        "Frequency_CV": -0.27,
        "Damping_CV": 0.0453,
        "Structure_CV": 0.0,
        "Position_CV": -0.09,
    })

texture = pb.module("AudibleInstruments", "Clouds",  # VCV: "Texture Synthesizer"
    data={'playback': 1, 'quality': 0, 'blendMode': 0},
    **{
        "Freeze": 0.0,
        "Mode": 0.0,
        "Load_save": 0.0,
        "Grain_position": 0.2024,
        "Grain_size": 0.7867,
        "Grain_pitch": 0.0,
        "Audio_input_gain": 0.7181,
        "Grain_density": 0.1458,
        "Grain_texture": 0.2542,
        "Dry_wet": 0.606,
        "Stereo_spread": 0.4831,
        "Feedback_amount": 0.2181,
        "Reverb_amount": 0.6169,
    })

sampler = pb.module("AudibleInstruments", "Marbles",  # VCV: "Random Sampler"
    data={'t_deja_vu': True, 'x_deja_vu': True, 't_mode': 0, 'x_mode': 0, 't_range': 1, 'x_range': 0, 'external': False, 'x_scale': 2, 'y_divider_index': 8, 'x_clock_source_internal': 0},
    **{
        "T_deja_vu": 0.0,
        "X_deja_vu": 0.0,
        "Deja_vu_probability": 0.4916,
        "Clock_rate": 0.1687,
        "Probability_distribution": 0.3506,
        "T_mode": 0.0,
        "X_mode": 0.0,
        "Loop_length": 0.4193,
        "Gate_bias": 0.3614,
        "Distribution_bias": 0.3289,
        "Clock_range_mode": 0.0,
        "Output_voltage_range_mode": 0.0,
        "External_processing_mode": 0.0,
        "Randomness_amount": 0.1205,
        "Smoothness": 0.6807,
    })

audio = pb.module("Core", "AudioInterface2",
    data={'audio': {'driver': 6, 'deviceName': 'Speakers (High Definition Audio Device)', 'sampleRate': 48000.0, 'blockSize': 256, 'inputOffset': 0, 'outputOffset': 0}, 'dcFilter': True})

# Cables
pb.connect(texture.o.Left, audio.i.Left_input)
pb.connect(texture.o.Right, audio.i.Right_input)
pb.connect(sampler.out_id(5), texture.i.Pitch__1V_oct_)
pb.connect(resonator.o.Odd, texture.i.Left)
pb.connect(resonator.o.Even, texture.i.Right)
pb.connect(sampler.out_id(3), sampler.i.X_bias)
pb.connect(sampler.out_id(0), resonator.i.Strum)

print(pb.status)
for w in pb.warnings: print("WARN:", w)
out = "/Users/palaitis/Development/vcv-rack/patches/resonator-to-texture/22/patch.vcv"
pb.save(out)
print(f"Saved: {out}")
