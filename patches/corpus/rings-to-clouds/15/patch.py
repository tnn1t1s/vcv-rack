"""
Rings into Clouds 15 - Rebuilt with signal flow order and added filter + reverb
"""
import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder

pb = PatchBuilder()

# Signal flow order: sampler -> resonator -> texture -> ladder -> reverb -> audio

# 1. Random Sampler (Marbles) - generates gates and CV
sampler = pb.module("AudibleInstruments", "Marbles",  # VCV: "Random Sampler"
    data={'t_deja_vu': True, 'x_deja_vu': True, 't_mode': 6, 'x_mode': 1, 't_range': 1, 'x_range': 0, 'external': False, 'x_scale': 2, 'y_divider_index': 10, 'x_clock_source_internal': 0},
    **{
        "T_deja_vu": 0.0,
        "X_deja_vu": 0.0,
        "Deja_vu_probability": 1.0,
        "Clock_rate": -0.2434,
        "Probability_distribution": 0.7084,
        "T_mode": 0.0,
        "X_mode": 0.0,
        "Loop_length": 0.4976,
        "Gate_bias": 0.4253,
        "Distribution_bias": 0.794,
        "Clock_range_mode": 0.0,
        "Output_voltage_range_mode": 0.0,
        "External_processing_mode": 0.0,
        "Randomness_amount": 0.7301,
        "Smoothness": 0.7337,
    })

# 2. Resonator (Rings) - modal resonator
resonator = pb.module("AudibleInstruments", "Rings",  # VCV: "Resonator"
    data={'polyphony': 1, 'model': 0, 'easterEgg': False},
    **{
        "Polyphony": 0.0,
        "Resonator_type": 0.0,
        "Frequency": 30.0,
        "Structure": 0.359,
        "Brightness": 0.3663,
        "Damping": 0.9458,
        "Position": 0.8157,
        "Brightness_CV": 0.0,
        "Frequency_CV": 0.0,
        "Damping_CV": 0.0,
        "Structure_CV": -0.4747,
        "Position_CV": 0.0,
    })

# 3. Texture Synthesizer (Clouds) - granular processor
texture = pb.module("AudibleInstruments", "Clouds",  # VCV: "Texture Synthesizer"
    data={'playback': 0, 'quality': 2, 'blendMode': 0},
    **{
        "Freeze": 0.0,
        "Mode": 0.0,
        "Load_save": 0.0,
        "Grain_position": 0.1663,
        "Grain_size": 0.8614,
        "Grain_pitch": 0.0,
        "Audio_input_gain": 0.5,
        "Grain_density": 0.3518,
        "Grain_texture": 0.5566,
        "Dry_wet": 0.8084,
        "Stereo_spread": 0.8578,
        "Feedback_amount": 0.3458,
        "Reverb_amount": 0.8048,
    })

# 4. Ladder filter - fully open (20kHz = log2(20000) = 14.2877)
ladder = pb.module("AgentRack", "Ladder",
    Cutoff=14.2877,  # Fully open cutoff at 20kHz
    Resonance=0.0,
    Spread=0.0,
    Shape=0.0,
    Resonance_mode=2.0)

# 5. Plateau reverb (Valley) - using Plateau as Saphire equivalent
reverb = pb.module("Valley", "Plateau",
    **{
        "Dry_level": 0.5,
        "Wet_level": 0.5,
        "Pre-delay": 0.0,
        "Size": 0.5,
        "Diffusion": 0.5,
        "Decay": 0.5,
    })

# 6. Audio output
audio = pb.module("Core", "AudioInterface2",
    data={'audio': {'driver': 6, 'deviceName': 'Speakers (High Definition Audio Device)', 'sampleRate': 48000.0, 'blockSize': 256, 'inputOffset': 0, 'outputOffset': 0}, 'dcFilter': True})

# Cables - signal flow: sampler CV -> resonator -> texture -> ladder -> reverb -> audio
pb.connect(sampler.out_id(1), resonator.i.Strum)  # T₂ (gate output 2)
pb.connect(sampler.out_id(5), resonator.i.Pitch__1V_oct_)  # X₂ (voltage output 2)
pb.connect(resonator.o.Odd, texture.i.Left)
pb.connect(texture.o.Left, ladder.i.Audio)
pb.connect(texture.o.Right, ladder.i.Audio)  # Mix stereo to mono for ladder
pb.connect(ladder.o.Out, reverb.i.Left)
pb.connect(ladder.o.Out, reverb.i.Right)
pb.connect(reverb.o.Left, audio.i.Left_input)
pb.connect(reverb.o.Right, audio.i.Right_input)

print(pb.status)
for w in pb.warnings: print("WARN:", w)
out = __file__.replace("patch.py", "patch.vcv")
pb.save(out)
print(f"Saved: {out}")
