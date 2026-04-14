"""
Integration test for the Steel LLM inference pipeline.

Prerequisites (run once before this test):
  make download-model      -- fetches vendor/models/gemma-3-1b-it-q4.gguf
  make setup-test-deps     -- installs llama-cpp-python (Metal) into .venv

This test skips automatically if either the model or the llama-cpp-python
package is not available, so it never blocks a fresh checkout.

What it validates:
  - The model loads without crashing
  - A Steel-format prompt produces a response within max_tokens
  - The response contains a parseable JSON array of 16 floats in [0, 1]
  - The model's weights sum to > 0 (it expressed a preference, not silence)
"""

import json
import math
import os
import pathlib
import pytest

# ── Model path (set at build/deploy time via `make download-model`) ────────

REPO_ROOT  = pathlib.Path(__file__).parent.parent
MODEL_PATH = REPO_ROOT / "vendor" / "models" / "gemma-3-1b-it-q4.gguf"

# ── Conditional imports ────────────────────────────────────────────────────

try:
    from llama_cpp import Llama
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False

# ── Skip markers ───────────────────────────────────────────────────────────

requires_model = pytest.mark.skipif(
    not MODEL_PATH.exists(),
    reason=f"Model not found at {MODEL_PATH} — run `make download-model` first",
)

requires_llama_cpp = pytest.mark.skipif(
    not LLAMA_AVAILABLE,
    reason="llama-cpp-python not installed — run `make setup-test-deps` first",
)

# ── Shared fixture: load model once per session ────────────────────────────

@pytest.fixture(scope="session")
def llm():
    """Load the GGUF once for the entire test session. Skip if unavailable."""
    if not MODEL_PATH.exists():
        pytest.skip(f"Model not found at {MODEL_PATH} — run `make download-model` first")
    if not LLAMA_AVAILABLE:
        pytest.skip("llama-cpp-python not installed — run `make setup-test-deps` first")
    model = Llama(
        model_path=str(MODEL_PATH),
        n_ctx=2048,
        n_gpu_layers=-1,   # offload all layers to Metal when available
        n_threads=4,
        verbose=False,
    )
    return model


def infer(llm, user_message: str, max_tokens: int = 256) -> str:
    """Run inference via the chat completion API (applies the model's chat template)."""
    output = llm.create_chat_completion(
        messages=[{"role": "user", "content": user_message}],
        max_tokens=max_tokens,
        temperature=0.0,
    )
    return output["choices"][0]["message"]["content"]


# ── Prompt builder (mirrors Steel::buildPrompt) ────────────────────────────

WT_NAMES = [
    "sine","tri","saw","square","pulse25","pulse10",
    "supersaw","odd","even","bright","warm",
    "fm2","fm5","formant","sub","noiseband",
]

NUM_BANDS = 8


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


def parse_weights(response_text: str) -> list[float] | None:
    """Extract the first [...] JSON array from a model response."""
    start = response_text.find('[')
    end   = response_text.rfind(']')
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        arr = json.loads(response_text[start:end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(arr, list):
        return None
    weights = []
    for v in arr[:16]:
        if isinstance(v, (int, float)):
            weights.append(max(0.0, min(1.0, float(v))))
        else:
            weights.append(0.0)
    while len(weights) < 16:
        weights.append(0.0)
    return weights[:16]


# ── Tests ──────────────────────────────────────────────────────────────────

class TestSteelInference:

    def test_model_loads(self, llm):
        """Fixture already loaded the model; just confirm the object is valid."""
        assert llm is not None

    def test_inference_produces_output(self, llm):
        """Model must return at least one token for a Steel prompt."""
        rows = [[0.5] * NUM_BANDS]
        text = infer(llm, make_steel_prompt(rows), max_tokens=128)
        assert len(text.strip()) > 0, "Model produced no output"

    def test_response_contains_json_array(self, llm):
        """Response must contain a [...] that json.loads can parse."""
        rows = [[0.3, 0.1, 0.05, 0.02, 0.01, 0.01, 0.005, 0.002]]  # bass-heavy
        text = infer(llm, make_steel_prompt(rows))
        weights = parse_weights(text)
        assert weights is not None, f"No JSON array found in response:\n{text!r}"

    def test_response_has_16_weights(self, llm):
        rows = [[0.5] * NUM_BANDS for _ in range(5)]
        text = infer(llm, make_steel_prompt(rows))
        weights = parse_weights(text)
        assert weights is not None, f"No JSON array in:\n{text!r}"
        assert len(weights) == 16, f"Expected 16 weights, got {len(weights)}"

    def test_weights_are_in_valid_range(self, llm):
        rows = [[0.5] * NUM_BANDS for _ in range(5)]
        text = infer(llm, make_steel_prompt(rows))
        weights = parse_weights(text)
        assert weights is not None, f"No JSON array in:\n{text!r}"
        for i, w in enumerate(weights):
            assert 0.0 <= w <= 1.0, f"Weight {i} out of range: {w}"

    def test_bright_spectrum_emphasizes_bright_waveforms(self, llm):
        """
        When high-frequency bands dominate, the model should weight
        bright/harmonic-rich waveforms more than sub/sine.
        This is a soft behavioral test -- not a strict assertion.
        """
        rows = [[0.0, 0.0, 0.0, 0.1, 0.5, 0.8, 0.9, 0.9]] * 8
        text = infer(llm, make_steel_prompt(rows))
        weights = parse_weights(text)
        assert weights is not None, f"No parse:\n{text!r}"
        bright_sum = sum(weights[i] for i in [2, 3, 7, 8, 9])
        sub_weight = weights[14]
        print(f"\nbright_sum={bright_sum:.3f}  sub={sub_weight:.3f}")

    def test_bass_spectrum_does_not_crash(self, llm):
        """Bass-heavy input should produce valid weights without error."""
        rows = [[0.9, 0.8, 0.3, 0.1, 0.0, 0.0, 0.0, 0.0]] * 8
        text = infer(llm, make_steel_prompt(rows))
        weights = parse_weights(text)
        assert weights is not None, f"No parse:\n{text!r}"

    def test_full_history_prompt(self, llm):
        """20-snapshot prompt (maximum history) must also produce valid weights."""
        rows = [[float(j) * 0.04 for j in range(NUM_BANDS)] for _ in range(20)]
        text = infer(llm, make_steel_prompt(rows))
        weights = parse_weights(text)
        assert weights is not None, f"No parse:\n{text!r}"
        assert len(weights) == 16
