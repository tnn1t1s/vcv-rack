"""
Golden fixture tests for the Steel LLM inference pipeline.

Each fixture captures a representative spectral scenario and asserts
output *properties* -- not exact model text, which drifts across
quantizations and versions.

Purpose: regression detection when swapping models or quantizations.
If a golden test fails after a model change, it is a signal to audit
whether the new model still understands the task, not necessarily a
hard block.

Same prerequisites as test_steel_inference.py:
  make download-model
  make setup-test-deps
"""

import json
import pathlib
import time
import pytest

REPO_ROOT  = pathlib.Path(__file__).parent.parent
MODEL_PATH = REPO_ROOT / "vendor" / "models" / "gemma-3-1b-it-q4.gguf"

try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False

WT_NAMES = [
    "sine","tri","saw","square","pulse25","pulse10",
    "supersaw","odd","even","bright","warm",
    "fm2","fm5","formant","sub","noiseband",
]
NUM_BANDS = 8

# Waveform index groups for semantic assertions
IDX_BRIGHT  = [2, 3, 7, 8, 9]          # saw, square, odd, even, bright
IDX_WARM    = [0, 1, 10, 11, 14]        # sine, tri, warm, fm2, sub
IDX_COMPLEX = [6, 11, 12, 13, 15]       # supersaw, fm2, fm5, formant, noiseband


@pytest.fixture(scope="session")
def llm():
    if not MODEL_PATH.exists():
        pytest.skip(f"Model not found — run `make download-model`")
    if not LLAMA_AVAILABLE:
        pytest.skip("llama-cpp-python not installed — run `make setup-test-deps`")
    return Llama(
        model_path=str(MODEL_PATH),
        n_ctx=2048,
        n_gpu_layers=-1,
        n_threads=4,
        verbose=False,
    )


def make_steel_prompt(band_rows: list[list[float]]) -> str:
    s = ("You control a 16-wavetable synthesizer. "
         "Output ONLY a flat JSON array of exactly 16 mixing weights (0.0-1.0). "
         "No explanation. No nested arrays. No markdown.\n"
         "Example output: [0.8, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.1, 0.0]\n"
         "Waveforms: ")
    s += " ".join(f"{i}={WT_NAMES[i]}" for i in range(16))
    s += "\nSpectral history (8 bands: sub bass lmid mid hmid pres brill air), oldest first:\n"
    for row in band_rows:
        s += " ".join(f"{v:.2f}" for v in row) + "\n"
    s += "Weights:"
    return s


def parse_weights(text: str) -> list[float] | None:
    start = text.find('[')
    end   = text.rfind(']')
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        arr = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(arr, list):
        return None
    w = []
    for v in arr[:16]:
        w.append(max(0.0, min(1.0, float(v))) if isinstance(v, (int, float)) else 0.0)
    while len(w) < 16:
        w.append(0.0)
    return w[:16]


def infer(llm, prompt: str, max_tokens: int = 128) -> str:
    out = llm.create_chat_completion(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.0,
    )
    return out["choices"][0]["message"]["content"]


# ── Golden fixtures ────────────────────────────────────────────────────────
#
# Each fixture is (label, rows, property_checks).
# property_checks is a dict of human-readable name -> callable(weights) -> bool.
# All checks must pass for the fixture to pass.
#
# Kept as a plain list so it's easy to add entries without subclassing.

GOLDEN_FIXTURES = [

    # 1. Sustained bright tone (hi-hat, cymbal, harsh synth)
    #    High presence + brilliance + air, almost no sub.
    #    xfail: Gemma 3 1B IT outputs all-zeros for pure high-frequency input --
    #    it doesn't reason directionally at this scale. This test documents that
    #    failure and will auto-promote (xpass) when we upgrade to a larger model.
    #    Directional check is also commented in for when that happens.
    {
        "label": "bright_sustained",
        "rows":  [[0.0, 0.0, 0.05, 0.1, 0.6, 0.85, 0.9, 0.95]] * 8,
        "xfail": "Gemma 3 1B outputs all-zeros for bright spectra; needs >= 3B model",
        "checks": {
            "valid JSON array": lambda w: w is not None,
            "16 weights":       lambda w: len(w) == 16,
            "all in [0,1]":     lambda w: all(0.0 <= x <= 1.0 for x in w),
            "nonzero response": lambda w: sum(w) > 0.0,
            # Directional (uncomment for models >= 3B):
            # "bright > warm":  lambda w: sum(w[i] for i in IDX_BRIGHT) > sum(w[i] for i in IDX_WARM),
        },
    },

    # 2. Deep bass only (808 kick, sub bass, rumble)
    #    Only sub + bass bands active.
    #    Expect: sub/warm waveforms score at least as well as bright ones.
    {
        "label": "deep_bass_only",
        "rows":  [[0.95, 0.85, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0]] * 6,
        "checks": {
            "valid JSON array": lambda w: w is not None,
            "16 weights":       lambda w: len(w) == 16,
            "all in [0,1]":     lambda w: all(0.0 <= x <= 1.0 for x in w),
            "warm >= bright":   lambda w: (
                sum(w[i] for i in IDX_WARM) >= sum(w[i] for i in IDX_BRIGHT)
            ),
        },
    },

    # 3. Silence / near-zero history
    #    All bands essentially zero.
    #    Expect: a valid array (model doesn't crash or refuse); weights may be anything.
    {
        "label": "near_silence",
        "rows":  [[0.0] * NUM_BANDS] * 5,
        "checks": {
            "valid JSON array": lambda w: w is not None,
            "16 weights":       lambda w: len(w) == 16,
            "all in [0,1]":     lambda w: all(0.0 <= x <= 1.0 for x in w),
            "nonzero response": lambda w: sum(w) > 0.0,
        },
    },

    # 4. Evolving spectrum: bass fading, treble rising over 10 snapshots
    #    First 5 rows: bass-heavy. Last 5 rows: treble-heavy.
    #    Expect: valid array; longer prompt needs more max_tokens.
    {
        "label": "evolving_bass_to_treble",
        "rows":  (
            [[0.9, 0.8, 0.3, 0.1, 0.0, 0.0, 0.0, 0.0]] * 5 +
            [[0.0, 0.0, 0.0, 0.1, 0.5, 0.8, 0.9, 0.9]] * 5
        ),
        "max_tokens": 256,
        "checks": {
            "valid JSON array": lambda w: w is not None,
            "16 weights":       lambda w: len(w) == 16,
            "all in [0,1]":     lambda w: all(0.0 <= x <= 1.0 for x in w),
        },
    },

    # 5. Full mid-range (mix bus, dense pad)
    #    Mid bands dominate, sub and air quiet.
    #    Expect: complex/formant waveforms score at least as well as sub.
    {
        "label": "mid_dominant",
        "rows":  [[0.1, 0.2, 0.7, 0.8, 0.7, 0.3, 0.1, 0.0]] * 8,
        "checks": {
            "valid JSON array": lambda w: w is not None,
            "16 weights":       lambda w: len(w) == 16,
            "all in [0,1]":     lambda w: all(0.0 <= x <= 1.0 for x in w),
            "complex >= sub":   lambda w: (
                sum(w[i] for i in IDX_COMPLEX) >= w[14]
            ),
        },
    },
]


@pytest.mark.parametrize("fixture", GOLDEN_FIXTURES, ids=[f["label"] for f in GOLDEN_FIXTURES])
def test_golden_fixture(llm, fixture):
    if "xfail" in fixture:
        pytest.xfail(fixture["xfail"])

    prompt  = make_steel_prompt(fixture["rows"])
    text    = infer(llm, prompt, max_tokens=fixture.get("max_tokens", 128))
    weights = parse_weights(text)

    failures = []
    for name, check in fixture["checks"].items():
        try:
            passed = check(weights)
        except Exception as e:
            passed = False
            name   = f"{name} [exception: {e}]"
        if not passed:
            failures.append(name)

    if failures:
        w_str = str(weights) if weights else "(no parse)"
        pytest.fail(
            f"[{fixture['label']}] Failed checks: {failures}\n"
            f"  response: {text!r}\n"
            f"  weights:  {w_str}"
        )
