"""
Rings into Clouds 01
"""
import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder

pb = PatchBuilder()

# Signal flow: sampler -> resonator -> texture -> ladder -> saphire -> audio

sampler = pb.module("AudibleInstruments", "Marbles",  # VCV: "Random Sampler"
    data={'t_deja_vu': False, 'x_deja_vu': False, 't_mode': 2, 'x_mode': 0, 't_range': 2, 'x_range': 0, 'external': False, 'x_scale': 2, 'y_divider_index': 8, 'x_clock_source_internal': 0},
    **{
        "T_deja_vu": 0.0,
        "X_deja_vu": 0.0,
        "Deja_vu_probability": 0.3373,
        "Clock_rate": -0.5783,
        "Probability_distribution": 0.7157,
        "T_mode": 0.0,
        "X_mode": 0.0,
        "Loop_length": 0.7084,
        "Gate_bias": 0.6614,
        "Distribution_bias": 0.3807,
        "Clock_range_mode": 0.0,
        "Output_voltage_range_mode": 0.0,
        "External_processing_mode": 0.0,
        "Randomness_amount": 0.6675,
        "Smoothness": 0.8072,
    })

resonator = pb.module("AudibleInstruments", "Rings",  # VCV: "Resonator"
    data={'polyphony': 1, 'model': 0, 'easterEgg': False},
    **{
        "Polyphony": 0.0,
        "Resonator_type": 0.0,
        "Frequency": 30.0,
        "Structure": 0.3012,
        "Brightness": 0.4048,
        "Damping": 0.5012,
        "Position": 0.6482,
        "Brightness_CV": 0.1467,
        "Frequency_CV": 0.0,
        "Damping_CV": 0.1333,
        "Structure_CV": 0.0,
        "Position_CV": 0.1867,
    })

texture = pb.module("AudibleInstruments", "Clouds",  # VCV: "Texture Synthesizer"
    data={'playback': 0, 'quality': 0, 'blendMode': 2},
    **{
        "Freeze": 0.0,
        "Mode": 0.0,
        "Load_save": 0.0,
        "Grain_position": 0.5434,
        "Grain_size": 0.7916,
        "Grain_pitch": 0.0,
        "Audio_input_gain": 0.5,
        "Grain_density": 0.841,
        "Grain_texture": 0.5422,
        "Dry_wet": 0.7133,
        "Stereo_spread": 1.0,
        "Feedback_amount": 0.3012,
        "Reverb_amount": 0.9892,
    })

ladder = pb.module("AgentRack", "Ladder",  # LDR -- ladder filter
    # Cutoff stored in log2(Hz): log2(20)=4.32 .. log2(20000)=14.29
    **{
        "Cutoff": 14.2877,  # fully open = 20 kHz
        "Resonance": 0.0,
        "Spread": 0.0,
        "Shape": 0.0,
    })

saphire = pb.module("AgentRack", "Saphire",  # SPH -- convolution reverb
    **{
        "Mix": 0.5,
        "Time": 0.5,
        "Bend": 0.0,
        "Tone": 0.65,
        "Pre-delay": 0.0,
        "IR": 38.0,
    })

audio = pb.module("Core", "AudioInterface2",
    data={'audio': {'driver': 6, 'deviceName': 'Speakers (High Definition Audio Device)', 'sampleRate': 48000.0, 'blockSize': 256, 'inputOffset': 0, 'outputOffset': 0}, 'dcFilter': True})

# Cables
pb.connect(sampler.out_id(1), resonator.i.Strum)
pb.connect(sampler.out_id(5), resonator.i.Pitch__1V_oct_)
pb.connect(resonator.o.Odd, texture.i.Left)
pb.connect(texture.o.Left, ladder.i.Audio)
pb.connect(ladder.o.Out, saphire.i.In_L)
pb.connect(ladder.o.Out, saphire.i.In_R)
pb.connect(saphire.o.Out_L, audio.i.Left_input)
pb.connect(saphire.o.Out_R, audio.i.Right_input)

print(pb.status)
for w in pb.warnings: print("WARN:", w)
out = __file__.replace("patch.py", "patch.vcv")
pb.save(out)
print(f"Saved: {out}")
