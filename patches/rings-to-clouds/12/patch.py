"""
Rings into Clouds 12 - Rebuilt
Signal flow: Marbles (sampler) -> Rings (resonator) -> Clouds (texture) -> Ladder (filter) -> Plateau (reverb) -> Audio
"""
import sys
sys.path.insert(0, "/Users/palaitis/Development/vcv-rack")
from vcvpatch.builder import PatchBuilder
import math

pb = PatchBuilder()

# Signal flow order: sampler first, then resonator, then texture, then ladder, then reverb, then audio

# 1. Sampler: Marbles (Random Sampler) - generates gates and CV
sampler = pb.module("AudibleInstruments", "Marbles",  # VCV: "Random Sampler"
    data={'t_deja_vu': False, 'x_deja_vu': False, 't_mode': 2, 'x_mode': 0, 
          't_range': 0, 'x_range': 0, 'external': False, 'x_scale': 5, 
          'y_divider_index': 4, 'x_clock_source_internal': 0},
    **{
        "T_deja_vu": 0.0,
        "X_deja_vu": 0.0,
        "Deja_vu_probability": 0.347,
        "Clock_rate": 0.0361,
        "Probability_distribution": 0.6964,
        "T_mode": 0.0,
        "X_mode": 0.0,
        "Loop_length": 0.688,
        "Gate_bias": 0.6301,
        "Distribution_bias": 0.388,
        "Clock_range_mode": 0.0,
        "Output_voltage_range_mode": 0.0,
        "External_processing_mode": 0.0,
        "Randomness_amount": 0.0,
        "Smoothness": 0.7277,
    })

# 2. Resonator: Rings
resonator = pb.module("AudibleInstruments", "Rings",  # VCV: "Resonator"
    data={'polyphony': 0, 'model': 1, 'easterEgg': True},
    **{
        "Polyphony": 0.0,
        "Resonator_type": 0.0,
        "Frequency": 37.4458,
        "Structure": 0.6807,
        "Brightness": 0.1904,
        "Damping": 0.3952,
        "Position": 0.5,
        "Brightness_CV": 0.0,
        "Frequency_CV": 0.0,
        "Damping_CV": 0.0,
        "Structure_CV": -0.4747,
        "Position_CV": 0.0,
    })

# 3. Texture Synthesizer: Clouds
texture = pb.module("AudibleInstruments", "Clouds",  # VCV: "Texture Synthesizer"
    data={'playback': 2, 'quality': 0, 'blendMode': 0},
    **{
        "Freeze": 0.0,
        "Mode": 0.0,
        "Load_save": 0.0,
        "Grain_position": 0.6434,
        "Grain_size": 0.7916,
        "Grain_pitch": 0.0,
        "Audio_input_gain": 1.0,
        "Grain_density": 0.2072,
        "Grain_texture": 0.3048,
        "Dry_wet": 0.6639,
        "Stereo_spread": 0.5036,
        "Feedback_amount": 0.4831,
        "Reverb_amount": 0.7904,
    })

# 4. Ladder Filter - fully open cutoff (log2(20000) = 14.2877)
ladder = pb.module("AgentRack", "Ladder",
    Cutoff=14.2877,  # Fully open: log2(20000 Hz)
    Resonance=0.0)

# 5. Saphire Reverb: Valley/Plateau
reverb = pb.module("Valley", "Plateau",
    **{
        "Dry_level": 0.5,
        "Wet_level": 0.5,
        "Pre-delay": 0.0,
        "Size": 0.7,
        "Diffusion": 0.8,
        "Decay": 0.7,
        "Input_low_cut": 0.5,
        "Input_high_cut": 0.5,
        "Reverb_low_cut": 0.5,
        "Reverb_high_cut": 0.5,
    })

# 6. Audio output
audio = pb.module("Core", "AudioInterface2",
    data={'audio': {'driver': 6, 'deviceName': 'Speakers (High Definition Audio Device)', 
                    'sampleRate': 48000.0, 'blockSize': 256, 
                    'inputOffset': 0, 'outputOffset': 0}, 
          'dcFilter': True})

# Cables - following signal flow
# Marbles output IDs verified from discovered JSON:
#   id 0: T₁
#   id 1: T₂  
#   id 2: T₃
#   id 3: Y (bipolar jitter CV)
#   id 4: X₁
#   id 5: X₂
#   id 6: X₃

pb.connect(sampler.out_id(1), resonator.i.Strum)         # T₂ -> Strum (gate)
pb.connect(sampler.out_id(5), resonator.i.Structure)     # X₂ -> Structure (CV)
pb.connect(resonator.o.Odd, texture.i.Left)              # Resonator audio -> Texture
pb.connect(sampler.out_id(1), texture.i.Trigger)         # T₂ -> Trigger (gate)
pb.connect(texture.o.Left, ladder.i.Audio)               # Texture L -> Ladder
pb.connect(texture.o.Right, ladder.i.Audio)              # Texture R -> Ladder (mixed)
pb.connect(ladder.o.Out, reverb.i.Left)                  # Ladder -> Reverb L
pb.connect(ladder.o.Out, reverb.i.Right)                 # Ladder -> Reverb R
pb.connect(reverb.o.Left, audio.i.Left_input)            # Reverb -> Audio L
pb.connect(reverb.o.Right, audio.i.Right_input)          # Reverb -> Audio R

print(pb.status)
for w in pb.warnings: 
    print("WARN:", w)

out = "/Users/palaitis/Development/vcv-rack/patches/rings-to-clouds/12/patch.vcv"
pb.save(out)
print(f"Saved: {out}")
