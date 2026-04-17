"""
Rings into Clouds 13 - Rebuilt with signal flow order and added Ladder + Saphire
"""
import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder

pb = PatchBuilder()

# Signal flow order: sampler -> resonator -> texture -> ladder -> reverb -> audio

# 1. Random Sampler (Marbles) - generates gate/CV triggers
sampler = pb.module("AudibleInstruments", "Marbles",  # VCV: "Random Sampler"
    data={'t_deja_vu': False, 'x_deja_vu': False, 't_mode': 2, 'x_mode': 0, 't_range': 1, 'x_range': 0, 'external': False, 'x_scale': 5, 'y_divider_index': 4, 'x_clock_source_internal': 0},
    **{
        "T_deja_vu": 0.0,
        "X_deja_vu": 0.0,
        "Deja_vu_probability": 0.2482,
        "Clock_rate": 0.3928,
        "Probability_distribution": 0.3554,
        "T_mode": 0.0,
        "X_mode": 0.0,
        "Loop_length": 1.0,
        "Gate_bias": 1.0,
        "Distribution_bias": 0.3373,
        "Clock_range_mode": 0.0,
        "Output_voltage_range_mode": 0.0,
        "External_processing_mode": 0.0,
        "Randomness_amount": 0.0,
        "Smoothness": 0.8265,
    })

# 2. Resonator (Rings) - excited by Marbles trigger
resonator = pb.module("AudibleInstruments", "Rings",  # VCV: "Resonator"
    data={'polyphony': 0, 'model': 2, 'easterEgg': False},
    **{
        "Polyphony": 0.0,
        "Resonator_type": 0.0,
        "Frequency": 37.5181,
        "Structure": 1.0,
        "Brightness": 1.0,
        "Damping": 0.153,
        "Position": 0.9723,
        "Brightness_CV": 0.0,
        "Frequency_CV": 0.0,
        "Damping_CV": 0.0,
        "Structure_CV": -0.4747,
        "Position_CV": 0.0,
    })

# 3. Texture Synthesizer (Clouds) - processes resonator audio
texture = pb.module("AudibleInstruments", "Clouds",  # VCV: "Texture Synthesizer"
    data={'playback': 1, 'quality': 0, 'blendMode': 3},
    **{
        "Freeze": 0.0,
        "Mode": 0.0,
        "Load_save": 0.0,
        "Grain_position": 0.6181,
        "Grain_size": 0.6181,
        "Grain_pitch": 1.0,
        "Audio_input_gain": 1.0,
        "Grain_density": 0.7,
        "Grain_texture": 0.2711,
        "Dry_wet": 0.8096,
        "Stereo_spread": 0.2193,
        "Feedback_amount": 0.2964,
        "Reverb_amount": 0.506,
    })

# 4. Ladder filter - fully open cutoff (log2(20000) = 14.2877)
ladder = pb.module("AgentRack", "Ladder",
    Cutoff=14.2877,  # Fully open
    Resonance=0.0,
    Spread=0.0,
    Shape=0.0,
    Resonance_mode=2.0)

# 5. Saphire reverb - high-quality stereo reverb
reverb = pb.module("Valley", "Plateau",
    data={'frozen': 0, 'tuned': 0, 'diffuseInput': 1, 'preDelayCVSens': 0, 'inputSensitivity': 1, 'outputSaturation': 0},
    **{
        "Dry level": 0.2,
        "Wet level": 0.8,
        "Pre-delay": 0.0,
        "Input low cut": 10.0,
        "Input high cut": 10.0,
        "Size": 0.75,
        "Diffusion": 0.9,
        "Decay": 0.7,
        "Reverb high cut": 10.0,
        "Reverb low cut": 1.0,
        "Modulation rate": 0.3,
        "Modulation shape": 0.5,
        "Modulation depth": 0.3,
    })

# 6. Audio output
audio = pb.module("Core", "AudioInterface2",
    data={'audio': {'driver': 6, 'deviceName': 'Speakers (High Definition Audio Device)', 'sampleRate': 48000.0, 'blockSize': 256, 'inputOffset': 0, 'outputOffset': 0}, 'dcFilter': True})

# Wiring: signal flow from left to right
pb.connect(sampler.out_id(0), resonator.i.Strum)  # T₁ (gate output) -> Strum input
pb.connect(resonator.o.Odd, texture.i.Left)  # Resonator odd output -> Clouds left input
pb.connect(texture.o.Left, ladder.i.Audio)  # Clouds left -> Ladder stereo input
pb.connect(texture.o.Right, ladder.i.Audio)  # Clouds right -> Ladder stereo input (mixed)
pb.connect(ladder.o.Out, reverb.i.Left)  # Ladder out -> Reverb left
pb.connect(ladder.o.Out, reverb.i.Right)  # Ladder out -> Reverb right
pb.connect(reverb.o.Left, audio.i.Left_input)  # Reverb left -> Audio interface
pb.connect(reverb.o.Right, audio.i.Right_input)  # Reverb right -> Audio interface

print(pb.status)
for w in pb.warnings: 
    print("WARN:", w)

out = __file__.replace("patch.py", "patch.vcv")
pb.save(out)
print(f"Saved: {out}")
