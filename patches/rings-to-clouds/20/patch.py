"""
Rings into Clouds 20
"""
import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder

pb = PatchBuilder()

resonator = pb.module("AudibleInstruments", "Rings",  # VCV: "Resonator"
    data={'polyphony': 0, 'model': 1, 'easterEgg': False},
    **{
        "Polyphony": 0.0,
        "Resonator_type": 0.0,
        "Frequency": 25.3012,
        "Structure": 0.3169,
        "Brightness": 0.2855,
        "Damping": 0.4,
        "Position": 0.3133,
        "Brightness_CV": 1.0,
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
        "Grain_position": 0.6771,
        "Grain_size": 0.8855,
        "Grain_pitch": 0.0,
        "Audio_input_gain": 1.0,
        "Grain_density": 0.753,
        "Grain_texture": 0.1831,
        "Dry_wet": 0.6566,
        "Stereo_spread": 1.0,
        "Feedback_amount": 0.3229,
        "Reverb_amount": 0.8108,
    })

sampler = pb.module("AudibleInstruments", "Marbles",  # VCV: "Random Sampler"
    data={'t_deja_vu': True, 'x_deja_vu': True, 't_mode': 2, 'x_mode': 0, 't_range': 0, 'x_range': 0, 'external': False, 'x_scale': 1, 'y_divider_index': 8, 'x_clock_source_internal': 0},
    **{
        "T_deja_vu": 0.0,
        "X_deja_vu": 0.0,
        "Deja_vu_probability": 0.8783,
        "Clock_rate": 0.0072,
        "Probability_distribution": 0.3313,
        "T_mode": 0.0,
        "X_mode": 0.0,
        "Loop_length": 0.2735,
        "Gate_bias": 0.5,
        "Distribution_bias": 0.7723,
        "Clock_range_mode": 0.0,
        "Output_voltage_range_mode": 0.0,
        "External_processing_mode": 0.0,
        "Randomness_amount": 0.6928,
        "Smoothness": 0.7795,
    })

audio = pb.module("Core", "AudioInterface2",
    data={'audio': {'driver': 6, 'deviceName': 'Speakers (High Definition Audio Device)', 'sampleRate': 48000.0, 'blockSize': 256, 'inputOffset': 0, 'outputOffset': 0}, 'dcFilter': True})

# Cables
pb.connect(texture.o.Left, audio.i.Left_input)
pb.connect(texture.o.Right, audio.i.Right_input)
pb.connect(sampler.out_id(5), texture.i.Pitch__1V_oct_)
pb.connect(resonator.o.Odd, texture.i.Left)
pb.connect(sampler.out_id(3), texture.i.Texture)
pb.connect(sampler.out_id(5), sampler.i.T_rate)
pb.connect(sampler.out_id(3), sampler.i.T_jitter)
pb.connect(sampler.out_id(6), resonator.i.Brightness)
pb.connect(sampler.out_id(1), resonator.i.Strum)

print(pb.status)
for w in pb.warnings: print("WARN:", w)
out = "/Users/palaitis/Development/vcv-rack/patches/resonator-to-texture/20/patch.vcv"
pb.save(out)
print(f"Saved: {out}")
