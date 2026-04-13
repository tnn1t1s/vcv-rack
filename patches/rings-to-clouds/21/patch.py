"""
Rings into Clouds 21 - Rebuilt with Ladder + Saphire
Signal flow: Marbles (sampler) → Rings (resonator) → Clouds (texture) → Ladder → Saphire → Audio
"""
import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder

pb = PatchBuilder()

# Signal flow order: left to right

# 1. Random Sampler (Marbles) - generates gates and CV
sampler = pb.module("AudibleInstruments", "Marbles",  # VCV: "Random Sampler"
    data={'t_deja_vu': False, 'x_deja_vu': True, 't_mode': 2, 'x_mode': 0, 't_range': 2, 'x_range': 0, 'external': False, 'x_scale': 2, 'y_divider_index': 8, 'x_clock_source_internal': 0},
    **{
        "T_deja_vu": 0.0,
        "X_deja_vu": 0.0,
        "Deja_vu_probability": 0.6675,
        "Clock_rate": -0.147,
        "Probability_distribution": 0.3506,
        "T_mode": 0.0,
        "X_mode": 0.0,
        "Loop_length": 0.294,
        "Gate_bias": 0.3614,
        "Distribution_bias": 0.5,
        "Clock_range_mode": 0.0,
        "Output_voltage_range_mode": 0.0,
        "External_processing_mode": 0.0,
        "Randomness_amount": 0.0,
        "Smoothness": 0.8072,
    })

# 2. Resonator (Rings) - modal synthesis excited by Marbles
resonator = pb.module("AudibleInstruments", "Rings",  # VCV: "Resonator"
    data={'polyphony': 1, 'model': 0, 'easterEgg': False},
    **{
        "Polyphony": 0.0,
        "Resonator_type": 0.0,
        "Frequency": 22.5542,
        "Structure": 0.3578,
        "Brightness": 0.4036,
        "Damping": 0.5506,
        "Position": 0.3217,
        "Brightness_CV": 0.0293,
        "Frequency_CV": -0.27,
        "Damping_CV": 0.0453,
        "Structure_CV": 0.0,
        "Position_CV": -0.09,
    })

# 3. Texture Synthesizer (Clouds) - granular processing
texture = pb.module("AudibleInstruments", "Clouds",  # VCV: "Texture Synthesizer"
    data={'playback': 1, 'quality': 0, 'blendMode': 0},
    **{
        "Freeze": 0.0,
        "Mode": 0.0,
        "Load_save": 0.0,
        "Grain_position": 0.6771,
        "Grain_size": 0.7867,
        "Grain_pitch": 0.0,
        "Audio_input_gain": 0.7181,
        "Grain_density": 0.1458,
        "Grain_texture": 0.2952,
        "Dry_wet": 0.606,
        "Stereo_spread": 0.4831,
        "Feedback_amount": 0.2181,
        "Reverb_amount": 0.6169,
    })

# 4. Ladder filter - fully open cutoff for transparent passage
ladder = pb.module("AgentRack", "Ladder",
    Cutoff=14.2877,  # log2(20000) - fully open
    Resonance=0.0,
    Spread=0.0,
    Shape=0.0)

# 5. Saphire reverb - AgentRack convolution reverb
saphire = pb.module("AgentRack", "Saphire",
    Mix=0.35,
    Time=0.7,
    Tone=0.65,
    IR=38.0)

# 6. Audio output
audio = pb.module("Core", "AudioInterface2",
    data={'audio': {'driver': 6, 'deviceName': 'Speakers (High Definition Audio Device)', 'sampleRate': 48000.0, 'blockSize': 256, 'inputOffset': 0, 'outputOffset': 0}, 'dcFilter': True})

# Wiring: signal flow sampler → resonator → texture → ladder → saphire → audio

# Marbles feedback: Y output to X bias input
pb.connect(sampler.out_id(3), sampler.i.X_bias)  # Y (bipolar jitter CV)

# Marbles to Rings: T₂ gate triggers strum
pb.connect(sampler.out_id(1), resonator.i.Strum)  # T₂ (gate output 2)

# Rings to Clouds: Odd output to Left input
pb.connect(resonator.o.Odd, texture.i.Left)

# Marbles to Clouds: X₂ CV controls pitch
pb.connect(sampler.out_id(5), texture.i.Pitch__1V_oct_)  # X₂ (CV output 2)

# Clouds to Ladder: stereo through filter
pb.connect(texture.o.Left, ladder.i.Audio)
pb.connect(texture.o.Right, ladder.i.Audio)

# Ladder to Saphire: mono filter out to stereo reverb in
pb.connect(ladder.o.Out, saphire.i.In_L)
pb.connect(ladder.o.Out, saphire.i.In_R)

# Saphire to Audio: stereo out
pb.connect(saphire.o.Out_L, audio.i.Left_input)
pb.connect(saphire.o.Out_R, audio.i.Right_input)

print(pb.status)
for w in pb.warnings:
    print("WARN:", w)

out = "/Users/palaitis/Development/vcv-rack/patches/rings-to-clouds/21/patch.vcv"
pb.save(out)
print(f"Saved: {out}")
