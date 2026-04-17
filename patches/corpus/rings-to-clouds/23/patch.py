"""
Rings into Clouds 23 - Rebuilt
Signal flow: Marbles -> Rings -> Clouds -> Ladder -> Saphire -> Audio
"""
import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder
import math

pb = PatchBuilder()

# Signal flow order: sources first, sinks last

# 1. Source: Random Sampler (Marbles)
sampler = pb.module("AudibleInstruments", "Marbles",  # VCV: "Random Sampler"
    data={'t_deja_vu': True, 'x_deja_vu': True, 't_mode': 0, 'x_mode': 0, 't_range': 1, 'x_range': 0, 'external': False, 'x_scale': 2, 'y_divider_index': 8, 'x_clock_source_internal': 0},
    **{
        "T_deja_vu": 0.0,
        "X_deja_vu": 0.0,
        "Deja_vu_probability": 0.8012,
        "Clock_rate": 0.1687,
        "Probability_distribution": 0.3506,
        "T_mode": 0.0,
        "X_mode": 0.0,
        "Loop_length": 0.4193,
        "Gate_bias": 0.3614,
        "Distribution_bias": 0.5855,
        "Clock_range_mode": 0.0,
        "Output_voltage_range_mode": 0.0,
        "External_processing_mode": 0.0,
        "Randomness_amount": 0.1205,
        "Smoothness": 0.6807,
    })

# 2. Exciter: Resonator (Rings)
resonator = pb.module("AudibleInstruments", "Rings",  # VCV: "Resonator"
    data={'polyphony': 1, 'model': 1, 'easterEgg': False},
    **{
        "Polyphony": 0.0,
        "Resonator_type": 0.0,
        "Frequency": 43.0121,
        "Structure": 0.6735,
        "Brightness": 0.306,
        "Damping": 0.5928,
        "Position": 0.6675,
        "Brightness_CV": 0.0293,
        "Frequency_CV": 0.0,
        "Damping_CV": 0.0453,
        "Structure_CV": 0.0,
        "Position_CV": -0.09,
    })

# 3. Granular processor: Texture Synthesizer (Clouds)
texture = pb.module("AudibleInstruments", "Clouds",  # VCV: "Texture Synthesizer"
    data={'playback': 0, 'quality': 0, 'blendMode': 0},
    **{
        "Freeze": 0.0,
        "Mode": 0.0,
        "Load_save": 0.0,
        "Grain_position": 0.1867,
        "Grain_size": 0.8867,
        "Grain_pitch": -1.0,
        "Audio_input_gain": 0.7181,
        "Grain_density": 0.7795,
        "Grain_texture": 0.7988,
        "Dry_wet": 0.8518,
        "Stereo_spread": 0.4831,
        "Feedback_amount": 0.6036,
        "Reverb_amount": 0.7229,
    })

# 4. Filter: Ladder (fully open cutoff)
ladder = pb.module("AgentRack", "Ladder",
    Cutoff=math.log2(20000),  # Fully open: log2(20kHz) = 14.2877
    Resonance=0.2)

# 5. Reverb: Saphire
saphire = pb.module("AgentRack", "Saphire",
    Mix=0.35,
    Time=0.7,
    Tone=0.65,
    IR=38.0)

# 6. Output: Audio Interface
audio = pb.module("Core", "AudioInterface2",
    data={'audio': {'driver': 6, 'deviceName': 'Speakers (High Definition Audio Device)', 'sampleRate': 48000.0, 'blockSize': 256, 'inputOffset': 0, 'outputOffset': 0}, 'dcFilter': True})

# Wiring: signal flow left-to-right
# Marbles -> Rings excitation
pb.connect(sampler.out_id(0), resonator.i.Strum)        # T₁ (gate output 1)
pb.connect(sampler.out_id(6), resonator.i.Pitch__1V_oct_)  # X₃ (CV output 3)

# Rings -> Clouds audio input
pb.connect(resonator.o.Odd, texture.i.Left)

# Clouds -> Ladder filter
pb.connect(texture.o.Left, ladder.i.Audio)

# Ladder -> Saphire reverb (stereo)
pb.connect(ladder.o.Out, saphire.i.In_L)
pb.connect(ladder.o.Out, saphire.i.In_R)

# Saphire -> Audio output
pb.connect(saphire.o.Out_L, audio.i.Left_input)
pb.connect(saphire.o.Out_R, audio.i.Right_input)

print(pb.status)
for w in pb.warnings: 
    print("WARN:", w)

out = __file__.replace("patch.py", "patch.vcv")
pb.save(out)
print(f"Saved: {out}")
