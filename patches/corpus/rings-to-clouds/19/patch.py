"""
Rings into Clouds 19 - Rebuilt with Ladder and Saphire
Signal flow: Marbles (sampler) → Rings (resonator) → Clouds (texture) → Ladder (filter) → Saphire (reverb) → Audio
"""
import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder

pb = PatchBuilder()

# Signal flow order: sampler → resonator → texture → ladder → saphire → audio

sampler = pb.module("AudibleInstruments", "Marbles",  # VCV: "Random Sampler"
    data={'t_deja_vu': False, 'x_deja_vu': False, 't_mode': 2, 'x_mode': 0, 't_range': 2, 'x_range': 0, 'external': False, 'x_scale': 2, 'y_divider_index': 8, 'x_clock_source_internal': 0},
    **{
        "T_deja_vu": 0.0,
        "X_deja_vu": 0.0,
        "Deja_vu_probability": 0.6819,
        "Clock_rate": -0.3325,
        "Probability_distribution": 0.3313,
        "T_mode": 0.0,
        "X_mode": 0.0,
        "Loop_length": 0.7084,
        "Gate_bias": 0.1012,
        "Distribution_bias": 0.6205,
        "Clock_range_mode": 0.0,
        "Output_voltage_range_mode": 0.0,
        "External_processing_mode": 0.0,
        "Randomness_amount": 0.6928,
        "Smoothness": 0.8072,
    })

resonator = pb.module("AudibleInstruments", "Rings",  # VCV: "Resonator"
    data={'polyphony': 1, 'model': 1, 'easterEgg': False},
    **{
        "Polyphony": 0.0,
        "Resonator_type": 0.0,
        "Frequency": 40.56,
        "Structure": 0.399,
        "Brightness": 0.4975,
        "Damping": 0.3248,
        "Position": 0.7928,
        "Brightness_CV": 0.6063,
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
        "Grain_pitch": -1.0,
        "Audio_input_gain": 0.7747,
        "Grain_density": 0.841,
        "Grain_texture": 0.5422,
        "Dry_wet": 0.9048,
        "Stereo_spread": 1.0,
        "Feedback_amount": 0.3229,
        "Reverb_amount": 0.8108,
    })

ladder = pb.module("AgentRack", "Ladder",
    Cutoff=14.2877,  # Fully open: log2(20000)
    Resonance=0.3,
    Spread=0.0,
    Shape=0.0,
    Resonance_mode=2.0)

saphire = pb.module("AgentRack", "Saphire",
    Mix=0.35,
    Time=0.7,
    Tone=0.65,
    IR=38.0)

audio = pb.module("Core", "AudioInterface2",
    data={'audio': {'driver': 6, 'deviceName': 'Speakers (High Definition Audio Device)', 'sampleRate': 48000.0, 'blockSize': 256, 'inputOffset': 0, 'outputOffset': 0}, 'dcFilter': True})

# Sampler self-patching and control of resonator
pb.connect(sampler.out_id(5), sampler.in_id(3))  # X₂ → T rate
pb.connect(sampler.out_id(3), sampler.in_id(4))  # Y → T jitter
pb.connect(sampler.out_id(6), resonator.i.Brightness)  # X₃ → Brightness
pb.connect(sampler.out_id(1), resonator.i.Strum)  # T₂ → Strum
pb.connect(sampler.out_id(4), resonator.i.Pitch__1V_oct_)  # X₁ → Pitch (1V/oct)

# Resonator → Texture
pb.connect(resonator.o.Odd, texture.i.Left)
pb.connect(resonator.o.Even, texture.i.Right)
pb.connect(sampler.out_id(0), texture.i.Trigger)  # T₁ → Trigger

# Texture → Ladder (sum to mono for filter)
pb.connect(texture.o.Left, ladder.i.Audio)
pb.connect(texture.o.Right, ladder.i.Audio)

# Ladder → Saphire (mono in, stereo out)
pb.connect(ladder.o.Out, saphire.i.In_L)
pb.connect(ladder.o.Out, saphire.i.In_R)

# Saphire → Audio
pb.connect(saphire.o.Out_L, audio.i.Left_input)
pb.connect(saphire.o.Out_R, audio.i.Right_input)

print(pb.status)
for w in pb.warnings: print("WARN:", w)
out = __file__.replace("patch.py", "patch.vcv")
pb.save(out)
print(f"Saved: {out}")
