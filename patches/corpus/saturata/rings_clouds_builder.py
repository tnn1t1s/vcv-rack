"""
Saturata: Rings into Clouds -- 25 patch builders.

All patches share the same 5-module setup:
  Marbles (random sampler) --> Rings (resonator) --> Clouds (texture synth) --> AudioInterface2

Marbles provides gates (T outputs) and pitch CV (X outputs) to Rings.
Rings resonates and feeds into Clouds for granular processing.
Clouds stereo out goes to the audio interface.

Purfenator is a decorative title/background panel with no audio connections.

Param names from registry.py entries added for Rings, Clouds, Marbles (2026-04-02).
Port names from AudibleInstruments/src/{Rings,Clouds,Marbles}.cpp enum order.

Run a single patch:
    uv run python -m patches.saturata.rings_clouds_builder 01
Run all 25:
    uv run python -m patches.saturata.rings_clouds_builder all
"""

import os
import sys

from vcvpatch.builder import PatchBuilder

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rings-clouds")


def _build(n: int, pb: PatchBuilder = None) -> str:
    """Build patch N (1-25) and return the output path."""
    if pb is None:
        pb = PatchBuilder()

    audio = pb.module("Core",               "AudioInterface2", pos=[84, 4])
    rings = pb.module("AudibleInstruments", "Rings",           pos=[52, 4], **RINGS_PARAMS[n])
    clouds= pb.module("AudibleInstruments", "Clouds",          pos=[64, 4], **CLOUDS_PARAMS[n])
    marbles=pb.module("AudibleInstruments", "Marbles",         pos=[0,  4], **MARBLES_PARAMS[n])
    _     = pb.module("DanTModules",        "Purfenator",      pos=[36, 4])

    # Core audio chain: Rings -> Clouds -> output
    pb.connect(rings.ODD,    clouds.i.IN_L)
    if n in RINGS_EVEN_TO_CLOUDS_R:
        pb.connect(rings.EVEN, clouds.i.IN_R)
    pb.connect(clouds.OUT_L, audio.i.IN_L)
    pb.connect(clouds.OUT_R, audio.i.IN_R)

    # Marbles -> Rings: gate (strum) and pitch
    strum_out, pitch_out = MARBLES_TO_RINGS[n]
    pb.connect(getattr(marbles, strum_out), rings.i.STRUM)
    if pitch_out:
        pb.connect(getattr(marbles, pitch_out), rings.i.PITCH)

    # Patch-specific extra connections
    for src, dst in EXTRA_CABLES.get(n, []):
        src_mod, src_port = src
        dst_mod, dst_port = dst
        mods = {"rings": rings, "clouds": clouds, "marbles": marbles}
        pb.connect(mods[src_mod].output(src_port) if isinstance(src_port, int)
                   else getattr(mods[src_mod], src_port),
                   mods[dst_mod].input(dst_port) if isinstance(dst_port, int)
                   else mods[dst_mod].i.__getattr__(dst_port))

    out_path = os.path.join(OUT_DIR, f"Rings into Clouds {n:02d}.vcv")
    pb.save(out_path)
    return out_path


# ---------------------------------------------------------------------------
# Which patches use Rings EVEN -> Clouds IN_R (stereo feed)
# ---------------------------------------------------------------------------
RINGS_EVEN_TO_CLOUDS_R = {6, 17, 18, 19, 22}

# ---------------------------------------------------------------------------
# Marbles output used for STRUM and PITCH in each patch
# None = no pitch connection for that patch
# ---------------------------------------------------------------------------
MARBLES_TO_RINGS = {
    1:  ("T2", "X2"),
    2:  ("T3", "X3"),
    3:  ("T2", "X2"),
    4:  ("T2", "X2"),
    5:  ("T1", "X1"),
    6:  ("T3", "X3"),
    7:  ("T1", "X1"),
    8:  ("T1", "X1"),
    9:  ("T2", "X2"),
    10: ("T2", "X2"),
    11: ("T1", "X3"),
    12: ("T2", None),
    13: ("T1", None),
    14: ("T3", "X2"),
    15: ("T2", "X2"),
    16: ("T3", None),
    17: ("T2", "X2"),
    18: ("T1", "X1"),
    19: ("T2", "X1"),
    20: ("T2", None),
    21: ("T2", None),
    22: ("T1", None),
    23: ("T1", "X3"),
    24: ("T1", "X3"),
    25: ("T1", "X2"),
}

# ---------------------------------------------------------------------------
# Extra cables beyond the standard Marbles->Rings->Clouds->Audio spine.
# Each entry: (src_mod, src_port_name), (dst_mod, dst_port_name)
# Cable type is auto-detected from the source port's signal type.
# ---------------------------------------------------------------------------
EXTRA_CABLES = {
    2:  [(("marbles", "Y"),  ("rings",   "POSITION_MOD"))],
    6:  [(("marbles", "Y"),  ("clouds",  "PITCH")),
         (("marbles", "X2"), ("rings",   "STRUCTURE_MOD"))],
    7:  [(("marbles", "T2"), ("clouds",  "FREEZE")),
         (("marbles", "Y"),  ("clouds",  "TEXTURE"))],
    9:  [(("marbles", "Y"),  ("marbles", "T_JITTER"))],
    10: [(("marbles", "Y"),  ("marbles", "T_JITTER"))],
    11: [(("marbles", "Y"),  ("marbles", "T_JITTER"))],
    12: [(("marbles", "T2"), ("clouds",  "TRIG")),
         (("marbles", "X2"), ("rings",   "STRUCTURE_MOD"))],
    14: [(("marbles", "X3"), ("marbles", "X_BIAS")),
         (("marbles", "Y"),  ("marbles", "DEJA_VU"))],
    16: [(("marbles", "Y"),  ("clouds",  "TEXTURE")),
         (("marbles", "Y"),  ("rings",   "BRIGHTNESS_MOD")),
         (("marbles", "Y"),  ("rings",   "STRUCTURE_MOD"))],
    17: [(("marbles", "X2"), ("clouds",  "PITCH")),
         (("marbles", "Y"),  ("marbles", "T_RATE"))],
    18: [(("marbles", "Y"),  ("marbles", "X_BIAS")),
         (("marbles", "X2"), ("marbles", "T_RATE")),
         (("marbles", "Y"),  ("marbles", "T_JITTER")),
         (("marbles", "Y"),  ("rings",   "POSITION_MOD"))],
    19: [(("marbles", "T1"), ("clouds",  "TRIG")),
         (("marbles", "X2"), ("marbles", "T_RATE")),
         (("marbles", "Y"),  ("marbles", "T_JITTER")),
         (("marbles", "X3"), ("rings",   "BRIGHTNESS_MOD"))],
    20: [(("marbles", "X2"), ("clouds",  "PITCH")),
         (("marbles", "Y"),  ("clouds",  "TEXTURE")),
         (("marbles", "X2"), ("marbles", "T_RATE")),
         (("marbles", "Y"),  ("marbles", "T_JITTER")),
         (("marbles", "X3"), ("rings",   "BRIGHTNESS_MOD"))],
    21: [(("marbles", "X2"), ("clouds",  "PITCH")),
         (("marbles", "Y"),  ("marbles", "X_BIAS"))],
    22: [(("marbles", "X2"), ("clouds",  "PITCH")),
         (("marbles", "Y"),  ("marbles", "X_BIAS"))],
}

# ---------------------------------------------------------------------------
# Params for each patch (by registry name)
# ---------------------------------------------------------------------------

RINGS_PARAMS = {
    1:  dict(FREQUENCY=30.0,    STRUCTURE=0.3012, BRIGHTNESS=0.4048, DAMPING=0.5012, POSITION=0.6482, BRIGHTNESS_CV=0.1467, DAMPING_CV=0.1333, POSITION_CV=0.1867),
    2:  dict(FREQUENCY=40.56,   STRUCTURE=0.399,  BRIGHTNESS=0.3144, DAMPING=0.3248, POSITION=0.6566, BRIGHTNESS_CV=0.3637, FREQUENCY_CV=-0.27, DAMPING_CV=0.0453, POSITION_CV=0.1793),
    3:  dict(FREQUENCY=24.0,    STRUCTURE=0.5,    BRIGHTNESS=0.2482, DAMPING=0.8855, POSITION=0.2807),
    4:  dict(FREQUENCY=37.4458, STRUCTURE=0.6807, BRIGHTNESS=0.3964, DAMPING=0.8542, POSITION=0.5),
    5:  dict(FREQUENCY=12.4337, STRUCTURE=0.5313, BRIGHTNESS=0.1904, DAMPING=0.6723, POSITION=0.6084),
    6:  dict(FREQUENCY=0.0,     STRUCTURE=1.0,    BRIGHTNESS=1.0,    DAMPING=0.153,  POSITION=1.0,    STRUCTURE_CV=1.0),
    7:  dict(FREQUENCY=23.494,  STRUCTURE=1.0,    BRIGHTNESS=0.4072, DAMPING=0.3964, POSITION=0.388),
    8:  dict(FREQUENCY=30.0,    STRUCTURE=0.3518, BRIGHTNESS=0.3602, DAMPING=0.6783, POSITION=0.3301),
    9:  dict(FREQUENCY=36.2169, STRUCTURE=0.5,    BRIGHTNESS=0.212,  DAMPING=0.6904, POSITION=0.3855, BRIGHTNESS_CV=0.288),
    10: dict(FREQUENCY=30.0,    STRUCTURE=0.3554, BRIGHTNESS=0.2904, DAMPING=0.9277, POSITION=0.0916),
    11: dict(FREQUENCY=30.0,    STRUCTURE=0.3494, BRIGHTNESS=0.3349, DAMPING=0.7699, POSITION=0.1735),
    12: dict(FREQUENCY=37.4458, STRUCTURE=0.6807, BRIGHTNESS=0.1904, DAMPING=0.3952, POSITION=0.5,    STRUCTURE_CV=-0.4747),
    13: dict(FREQUENCY=37.5181, STRUCTURE=1.0,    BRIGHTNESS=1.0,    DAMPING=0.153,  POSITION=0.9723, STRUCTURE_CV=-0.4747),
    14: dict(FREQUENCY=30.0,    STRUCTURE=0.7602, BRIGHTNESS=0.0,    DAMPING=0.1217, POSITION=0.0,    DAMPING_CV=0.2373, POSITION_CV=0.296),
    15: dict(FREQUENCY=30.0,    STRUCTURE=0.359,  BRIGHTNESS=0.3663, DAMPING=0.9458, POSITION=0.8157, STRUCTURE_CV=-0.4747),
    16: dict(FREQUENCY=33.1808, STRUCTURE=0.6807, BRIGHTNESS=0.3193, DAMPING=0.8916, POSITION=1.0,    BRIGHTNESS_CV=0.5067, STRUCTURE_CV=0.2293),
    17: dict(FREQUENCY=33.3253, STRUCTURE=0.3133, BRIGHTNESS=0.3181, DAMPING=0.3614, POSITION=0.2446, BRIGHTNESS_CV=0.3227, DAMPING_CV=0.3733, STRUCTURE_CV=0.3333, POSITION_CV=0.256),
    18: dict(FREQUENCY=38.4578, STRUCTURE=0.5096, BRIGHTNESS=0.0,    DAMPING=0.7699, POSITION=0.6855, BRIGHTNESS_CV=0.288,  POSITION_CV=0.6587),
    19: dict(FREQUENCY=40.56,   STRUCTURE=0.399,  BRIGHTNESS=0.4975, DAMPING=0.3248, POSITION=0.7928, BRIGHTNESS_CV=0.6063, FREQUENCY_CV=-0.27, DAMPING_CV=0.0453, POSITION_CV=-0.09),
    20: dict(FREQUENCY=25.3012, STRUCTURE=0.3169, BRIGHTNESS=0.2855, DAMPING=0.4,    POSITION=0.3133, BRIGHTNESS_CV=1.0,    FREQUENCY_CV=-0.27, DAMPING_CV=0.0453, POSITION_CV=-0.09),
    21: dict(FREQUENCY=22.5542, STRUCTURE=0.3578, BRIGHTNESS=0.4036, DAMPING=0.5506, POSITION=0.3217, BRIGHTNESS_CV=0.0293, FREQUENCY_CV=-0.27, DAMPING_CV=0.0453, POSITION_CV=-0.09),
    22: dict(FREQUENCY=39.3976, STRUCTURE=0.6301, BRIGHTNESS=0.6301, DAMPING=0.5735, POSITION=0.6675, BRIGHTNESS_CV=0.0293, FREQUENCY_CV=-0.27, DAMPING_CV=0.0453, POSITION_CV=-0.09),
    23: dict(FREQUENCY=43.0121, STRUCTURE=0.6735, BRIGHTNESS=0.306,  DAMPING=0.5928, POSITION=0.6675, BRIGHTNESS_CV=0.0293, DAMPING_CV=0.0453,  POSITION_CV=-0.09),
    24: dict(FREQUENCY=30.0,    STRUCTURE=0.359,  BRIGHTNESS=0.3686, DAMPING=0.5651, POSITION=0.3976, BRIGHTNESS_CV=0.0293, DAMPING_CV=0.0453,  POSITION_CV=-0.09),
    25: dict(FREQUENCY=33.0361, STRUCTURE=0.3205, BRIGHTNESS=0.1337, DAMPING=0.8542, POSITION=1.0,    BRIGHTNESS_CV=0.4107, FREQUENCY_CV=0.1493, STRUCTURE_CV=1.0),
}

CLOUDS_PARAMS = {
    1:  dict(POSITION=0.5434, SIZE=0.7916, IN_GAIN=0.5,    DENSITY=0.841,  TEXTURE=0.5422, DRYWET=0.7133, SPREAD=1.0,    FEEDBACK=0.3012, REVERB=0.9892),
    2:  dict(POSITION=0.6241, SIZE=0.6036, IN_GAIN=0.4831, DENSITY=0.0542, TEXTURE=0.2133, DRYWET=0.512,  REVERB=0.8867),
    3:  dict(POSITION=0.2518, SIZE=0.7048, PITCH=0.6024,   IN_GAIN=1.0,    DENSITY=0.306,  TEXTURE=0.7012, DRYWET=0.4952, SPREAD=0.494, FEEDBACK=0.5831, REVERB=0.9145),
    4:  dict(POSITION=0.2518, SIZE=0.7048, IN_GAIN=1.0,    DENSITY=0.306,  TEXTURE=0.7012, DRYWET=1.0,    SPREAD=0.494,  FEEDBACK=0.5831, REVERB=1.0),
    5:  dict(POSITION=0.0602, SIZE=0.7253, PITCH=1.012,    IN_GAIN=1.0,    DENSITY=0.2072, TEXTURE=0.2602, DRYWET=0.4904, SPREAD=0.4843, FEEDBACK=0.394, REVERB=0.3783),
    6:  dict(POSITION=0.1422, SIZE=0.6651, PITCH=0.6602,   IN_GAIN=1.0,    DENSITY=0.1434, TEXTURE=0.3,   DRYWET=0.3819, SPREAD=0.2627, FEEDBACK=0.6398, REVERB=0.8325),
    7:  dict(POSITION=0.2253, SIZE=0.6867, PITCH=1.0,      IN_GAIN=1.0,    DENSITY=0.1614, TEXTURE=0.6554, DRYWET=0.8337, SPREAD=1.0,   FEEDBACK=0.5072, REVERB=0.8349),
    8:  dict(POSITION=0.3277, SIZE=0.1337, PITCH=1.0,      IN_GAIN=1.0,    DENSITY=0.7349, TEXTURE=0.2723, DRYWET=0.806,  SPREAD=1.0,   FEEDBACK=0.3482, REVERB=0.7843),
    9:  dict(POSITION=0.5434, SIZE=0.7916, IN_GAIN=0.5663, DENSITY=0.841,  TEXTURE=0.5422, DRYWET=0.7133, SPREAD=0.5181, REVERB=0.9036),
    10: dict(POSITION=1.0,    SIZE=0.3133, IN_GAIN=0.7012, DENSITY=0.3482, TEXTURE=0.8952, DRYWET=0.8434, SPREAD=0.4807, FEEDBACK=0.353, REVERB=0.9952),
    11: dict(POSITION=0.3,    SIZE=0.7,    IN_GAIN=0.8036, DENSITY=0.3133, TEXTURE=0.6928, DRYWET=0.7699, SPREAD=0.8229, FEEDBACK=0.4229, REVERB=0.8193),
    12: dict(POSITION=0.6434, SIZE=0.7916, IN_GAIN=1.0,    DENSITY=0.2072, TEXTURE=0.3048, DRYWET=0.6639, SPREAD=0.5036, FEEDBACK=0.4831, REVERB=0.7904),
    13: dict(POSITION=0.6181, SIZE=0.6181, PITCH=1.0,      IN_GAIN=1.0,    DENSITY=0.7,    TEXTURE=0.2711, DRYWET=0.8096, SPREAD=0.2193, FEEDBACK=0.2964, REVERB=0.506),
    14: dict(POSITION=0.206,  SIZE=0.6735, IN_GAIN=0.3313, DENSITY=0.1976, TEXTURE=0.8012, DRYWET=0.7928, SPREAD=0.4916, FEEDBACK=0.247, REVERB=0.4277),
    15: dict(POSITION=0.1663, SIZE=0.8614, IN_GAIN=0.5,    DENSITY=0.3518, TEXTURE=0.5566, DRYWET=0.8084, SPREAD=0.8578, FEEDBACK=0.3458, REVERB=0.8048),
    16: dict(POSITION=1.0,    SIZE=1.0,    IN_GAIN=0.3313, DENSITY=0.147,  TEXTURE=0.1145, DRYWET=1.0,    SPREAD=1.0,    FEEDBACK=0.3843, REVERB=1.0),
    17: dict(POSITION=0.6542, SIZE=0.7024, IN_GAIN=0.6904, DENSITY=0.1217, TEXTURE=0.2024, DRYWET=0.806,  SPREAD=1.0,    FEEDBACK=0.4639, REVERB=0.8096),
    18: dict(POSITION=0.6771, SIZE=0.8855, PITCH=-1.0,     IN_GAIN=0.5,    DENSITY=0.841,  TEXTURE=0.5422, DRYWET=0.7108, SPREAD=1.0,   FEEDBACK=0.388, REVERB=1.0),
    19: dict(POSITION=0.6771, SIZE=0.8855, PITCH=-1.0,     IN_GAIN=0.7747, DENSITY=0.841,  TEXTURE=0.5422, DRYWET=0.9048, SPREAD=1.0,   FEEDBACK=0.3229, REVERB=0.8108),
    20: dict(POSITION=0.6771, SIZE=0.8855, IN_GAIN=1.0,    DENSITY=0.753,  TEXTURE=0.1831, DRYWET=0.6566, SPREAD=1.0,    FEEDBACK=0.3229, REVERB=0.8108),
    21: dict(POSITION=0.6771, SIZE=0.7867, IN_GAIN=0.7181, DENSITY=0.1458, TEXTURE=0.2952, DRYWET=0.606,  SPREAD=0.4831, FEEDBACK=0.2181, REVERB=0.6169),
    22: dict(POSITION=0.2024, SIZE=0.7867, IN_GAIN=0.7181, DENSITY=0.1458, TEXTURE=0.2542, DRYWET=0.606,  SPREAD=0.4831, FEEDBACK=0.2181, REVERB=0.6169),
    23: dict(POSITION=0.1867, SIZE=0.8867, PITCH=-1.0,     IN_GAIN=0.7181, DENSITY=0.7795, TEXTURE=0.7988, DRYWET=0.8518, SPREAD=0.4831, FEEDBACK=0.6036, REVERB=0.7229),
    24: dict(POSITION=1.0,    SIZE=1.0,    IN_GAIN=0.8024, DENSITY=0.141,  TEXTURE=0.5349, DRYWET=0.6602, SPREAD=0.4831, REVERB=0.8626),
    25: dict(POSITION=1.0,    SIZE=0.7699, PITCH=-1.0,     IN_GAIN=0.7904, DENSITY=0.7084, TEXTURE=0.3458, DRYWET=0.7205, SPREAD=1.0,   FEEDBACK=0.3952, REVERB=0.9229),
}

MARBLES_PARAMS = {
    1:  dict(DEJA_VU_PROB=0.3373, CLOCK_RATE=-0.5783, DISTRIBUTION=0.7157, LOOP_LENGTH=0.7084, GATE_BIAS=0.6614, DIST_BIAS=0.3807, RANDOMNESS=0.6675, SMOOTHNESS=0.8072),
    2:  dict(DEJA_VU_PROB=0.6723, CLOCK_RATE=-0.7012, DISTRIBUTION=0.6506, LOOP_LENGTH=0.7145, GATE_BIAS=0.7964, DIST_BIAS=0.8096, RANDOMNESS=0.3783, SMOOTHNESS=0.8229),
    3:  dict(DEJA_VU_PROB=0.7566, CLOCK_RATE=-0.6048, DISTRIBUTION=0.6578, LOOP_LENGTH=0.294,  GATE_BIAS=0.5,    DIST_BIAS=0.6518, SMOOTHNESS=0.7988),
    4:  dict(DEJA_VU_PROB=0.7566, CLOCK_RATE=-0.6048, DISTRIBUTION=0.6578, LOOP_LENGTH=0.294,  GATE_BIAS=0.5,    DIST_BIAS=0.6518, SMOOTHNESS=0.7988),
    5:  dict(DEJA_VU_PROB=0.3373, CLOCK_RATE=-0.2048, DISTRIBUTION=0.3386, LOOP_LENGTH=0.7084, GATE_BIAS=0.3253, DIST_BIAS=0.3952, RANDOMNESS=0.706, SMOOTHNESS=0.7964),
    6:  dict(DEJA_VU_PROB=0.5,    CLOCK_RATE=-0.0048, DISTRIBUTION=0.3289, LOOP_LENGTH=0.4157, GATE_BIAS=0.3783, DIST_BIAS=0.3807, RANDOMNESS=1.0),
    7:  dict(DEJA_VU_PROB=0.753,  CLOCK_RATE=-0.7157, DISTRIBUTION=0.5904, LOOP_LENGTH=0.2867, GATE_BIAS=0.3578, DIST_BIAS=0.5494, RANDOMNESS=0.8687),
    8:  dict(DEJA_VU_PROB=0.2217, CLOCK_RATE=-0.2313, DISTRIBUTION=0.6434, LOOP_LENGTH=0.6482, GATE_BIAS=0.312,  DIST_BIAS=0.5795, RANDOMNESS=0.7229, SMOOTHNESS=0.7048),
    9:  dict(DEJA_VU_PROB=0.3373, CLOCK_RATE=-0.3566, DISTRIBUTION=0.7157, LOOP_LENGTH=0.7084, GATE_BIAS=0.6614, DIST_BIAS=0.3807, RANDOMNESS=0.7494, SMOOTHNESS=0.6663),
    10: dict(DEJA_VU_PROB=0.347,  CLOCK_RATE=-0.5133, DISTRIBUTION=0.3313, LOOP_LENGTH=0.688,  GATE_BIAS=0.6301, DIST_BIAS=0.4084, RANDOMNESS=0.512,  SMOOTHNESS=0.8229),
    11: dict(DEJA_VU_PROB=0.347,  CLOCK_RATE=-0.5133, DISTRIBUTION=0.6096, LOOP_LENGTH=0.688,  GATE_BIAS=0.6301, DIST_BIAS=0.4084, SMOOTHNESS=0.8229),
    12: dict(DEJA_VU_PROB=0.347,  CLOCK_RATE=0.0361,  DISTRIBUTION=0.6964, LOOP_LENGTH=0.688,  GATE_BIAS=0.6301, DIST_BIAS=0.388,  SMOOTHNESS=0.7277),
    13: dict(DEJA_VU_PROB=0.2482, CLOCK_RATE=0.3928,  DISTRIBUTION=0.3554, LOOP_LENGTH=1.0,    GATE_BIAS=1.0,    DIST_BIAS=0.3373, SMOOTHNESS=0.8265),
    14: dict(DEJA_VU_PROB=0.6301, CLOCK_RATE=-0.0771, DISTRIBUTION=0.5012, LOOP_LENGTH=0.2831, GATE_BIAS=0.4084, DIST_BIAS=0.5024, SMOOTHNESS=0.8072),
    15: dict(DEJA_VU_PROB=1.0,    CLOCK_RATE=-0.2434, DISTRIBUTION=0.7084, LOOP_LENGTH=0.4976, GATE_BIAS=0.4253, DIST_BIAS=0.794,  RANDOMNESS=0.7301, SMOOTHNESS=0.7337),
    16: dict(DEJA_VU_PROB=0.6301, CLOCK_RATE=-0.2602, DISTRIBUTION=0.5,    LOOP_LENGTH=0.2831, GATE_BIAS=0.3627, DIST_BIAS=0.5024, SMOOTHNESS=0.8072),
    17: dict(DEJA_VU_PROB=0.8988, CLOCK_RATE=-0.6578, DISTRIBUTION=0.6976, LOOP_LENGTH=0.7084, GATE_BIAS=0.6181, DIST_BIAS=0.6325, RANDOMNESS=1.0,    SMOOTHNESS=0.7843),
    18: dict(DEJA_VU_PROB=0.3373, CLOCK_RATE=-0.5783, DISTRIBUTION=0.7157, LOOP_LENGTH=0.7084, GATE_BIAS=0.1012, DIST_BIAS=0.3807, RANDOMNESS=0.6928, SMOOTHNESS=0.8072),
    19: dict(DEJA_VU_PROB=0.6819, CLOCK_RATE=-0.3325, DISTRIBUTION=0.3313, LOOP_LENGTH=0.7084, GATE_BIAS=0.1012, DIST_BIAS=0.6205, RANDOMNESS=0.6928, SMOOTHNESS=0.8072),
    20: dict(DEJA_VU_PROB=0.8783, CLOCK_RATE=0.0072,  DISTRIBUTION=0.3313, LOOP_LENGTH=0.2735, GATE_BIAS=0.5,    DIST_BIAS=0.7723, RANDOMNESS=0.6928, SMOOTHNESS=0.7795),
    21: dict(DEJA_VU_PROB=0.6675, CLOCK_RATE=-0.147,  DISTRIBUTION=0.3506, LOOP_LENGTH=0.294,  GATE_BIAS=0.3614, DIST_BIAS=0.5,    SMOOTHNESS=0.8072),
    22: dict(DEJA_VU_PROB=0.4916, CLOCK_RATE=0.1687,  DISTRIBUTION=0.3506, LOOP_LENGTH=0.4193, GATE_BIAS=0.3614, DIST_BIAS=0.3289, RANDOMNESS=0.1205, SMOOTHNESS=0.6807),
    23: dict(DEJA_VU_PROB=0.8012, CLOCK_RATE=0.1687,  DISTRIBUTION=0.3506, LOOP_LENGTH=0.4193, GATE_BIAS=0.3614, DIST_BIAS=0.5855, RANDOMNESS=0.1205, SMOOTHNESS=0.6807),
    24: dict(DEJA_VU_PROB=0.8398, CLOCK_RATE=0.1253,  DISTRIBUTION=0.4108, LOOP_LENGTH=0.6361, GATE_BIAS=0.7819, DIST_BIAS=0.5542, RANDOMNESS=0.306,  SMOOTHNESS=0.7337),
    25: dict(DEJA_VU_PROB=0.5012, CLOCK_RATE=-0.6217, DISTRIBUTION=0.2771, LOOP_LENGTH=0.1373, GATE_BIAS=0.5699, DIST_BIAS=0.2566, SMOOTHNESS=0.788),
}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build Rings into Clouds patches")
    parser.add_argument("patch", nargs="?", default="all",
                        help="Patch number (01-25) or 'all'")
    args = parser.parse_args()

    if args.patch == "all":
        for i in range(1, 26):
            path = _build(i)
            print(f"  [{i:02d}] {path}")
    else:
        n = int(args.patch)
        path = _build(n)
        print(f"Built: {path}")
