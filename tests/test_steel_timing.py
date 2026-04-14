"""
Timing budget tests for the Steel LLM inference pipeline.

These are not pass/fail correctness tests -- they measure and log latency
so you can track how the module will feel in a live patch.

In Rack, inference runs on a background thread and the result is polled
by the audio thread every N seconds (RATE_PARAM). The relevant budget is:

  inference latency < RATE_PARAM (typically 3-10 seconds)
  prompt build time < 1ms (it runs on the audio thread)
  parse time < 1ms (also on the audio thread)

Hard limits enforced here:
  - Single inference < 30s (hard fail -- unusable live)
  - Prompt build < 5ms
  - Parse < 1ms

Soft limits printed as warnings (not failures):
  - Inference < 10s (matches minimum RATE_PARAM)
  - Tokens/sec > 5 (below this the module feels unresponsive)

Same prerequisites as the other inference tests:
  make download-model
  make setup-test-deps
"""

import json
import pathlib
import time
import statistics
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
NUM_BANDS    = 8
HISTORY_LEN  = 20

# Hard budget limits
INFERENCE_MAX_S  = 30.0   # hard fail -- completely unusable
PROMPT_BUILD_MAX_MS = 5.0
PARSE_MAX_MS        = 1.0

# Soft limits -- printed but not a test failure
INFERENCE_WARN_S = 10.0   # matches RATE_PARAM minimum
TOKENS_PER_SEC_WARN = 5.0


@pytest.fixture(scope="session")
def llm():
    if not MODEL_PATH.exists():
        pytest.skip("Model not found — run `make download-model`")
    if not LLAMA_AVAILABLE:
        pytest.skip("llama-cpp-python not installed — run `make setup-test-deps`")
    return Llama(
        model_path=str(MODEL_PATH),
        n_ctx=2048,
        n_gpu_layers=-1,
        n_threads=4,
        verbose=False,
    )


def make_steel_prompt(band_rows):
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


def parse_weights(text):
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


class TestSteelTimingBudget:

    def test_prompt_build_time(self):
        """buildPrompt() runs on the audio thread -- must be fast."""
        rows = [[float(b) * 0.05 for b in range(NUM_BANDS)] for _ in range(HISTORY_LEN)]
        N = 1000
        t0 = time.perf_counter()
        for _ in range(N):
            make_steel_prompt(rows)
        elapsed_ms = (time.perf_counter() - t0) / N * 1000

        print(f"\nprompt build: {elapsed_ms:.3f}ms per call (n={N})")
        assert elapsed_ms < PROMPT_BUILD_MAX_MS, (
            f"Prompt build too slow: {elapsed_ms:.3f}ms > {PROMPT_BUILD_MAX_MS}ms limit"
        )

    def test_parse_time(self):
        """parse_weights() runs on the audio thread -- must be fast."""
        # Typical model response
        response = "[0.8, 0.05, 0.0, 0.0, 0.0, 0.0, 0.05, 0.0, 0.0, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]"
        N = 10000
        t0 = time.perf_counter()
        for _ in range(N):
            parse_weights(response)
        elapsed_ms = (time.perf_counter() - t0) / N * 1000

        print(f"\nparse time: {elapsed_ms:.4f}ms per call (n={N})")
        assert elapsed_ms < PARSE_MAX_MS, (
            f"Parse too slow: {elapsed_ms:.4f}ms > {PARSE_MAX_MS}ms limit"
        )

    def test_single_inference_latency(self, llm):
        """One inference call must complete within the hard budget."""
        rows = [[0.5] * NUM_BANDS for _ in range(5)]
        prompt = make_steel_prompt(rows)

        t0 = time.perf_counter()
        out = llm.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=128,
            temperature=0.0,
        )
        elapsed = time.perf_counter() - t0

        text = out["choices"][0]["message"]["content"]
        n_tokens = out["usage"]["completion_tokens"]
        tps = n_tokens / elapsed if elapsed > 0 else 0

        print(f"\ninference: {elapsed:.2f}s  |  {n_tokens} tokens  |  {tps:.1f} tok/s")

        if elapsed > INFERENCE_WARN_S:
            print(f"  WARNING: {elapsed:.1f}s > {INFERENCE_WARN_S}s soft limit "
                  f"(RATE_PARAM minimum). Module may feel sluggish.")
        if tps < TOKENS_PER_SEC_WARN:
            print(f"  WARNING: {tps:.1f} tok/s < {TOKENS_PER_SEC_WARN} soft limit.")

        assert elapsed < INFERENCE_MAX_S, (
            f"Inference took {elapsed:.1f}s -- exceeds hard limit of {INFERENCE_MAX_S}s"
        )

    def test_repeated_inference_latency(self, llm):
        """
        Run N inferences and report min/mean/max/stdev.
        Catches thermal throttling or memory pressure on repeated calls.
        """
        N = 5
        prompts = [
            make_steel_prompt([[float(i % 8) * 0.1 + j * 0.01
                                 for j in range(NUM_BANDS)]
                                for _ in range(3)])
            for i in range(N)
        ]

        latencies = []
        token_counts = []
        for p in prompts:
            t0 = time.perf_counter()
            out = llm.create_chat_completion(
                messages=[{"role": "user", "content": p}],
                max_tokens=128,
                temperature=0.0,
            )
            latencies.append(time.perf_counter() - t0)
            token_counts.append(out["usage"]["completion_tokens"])

        mean_s    = statistics.mean(latencies)
        max_s     = max(latencies)
        stdev_s   = statistics.stdev(latencies) if len(latencies) > 1 else 0.0
        mean_tps  = statistics.mean(t / s for t, s in zip(token_counts, latencies))

        print(f"\n{N} inferences:")
        print(f"  latency  min={min(latencies):.2f}s  mean={mean_s:.2f}s  "
              f"max={max_s:.2f}s  stdev={stdev_s:.2f}s")
        print(f"  tokens/s mean={mean_tps:.1f}")

        if max_s > INFERENCE_WARN_S:
            print(f"  WARNING: max latency {max_s:.1f}s > {INFERENCE_WARN_S}s soft limit.")
        if mean_tps < TOKENS_PER_SEC_WARN:
            print(f"  WARNING: {mean_tps:.1f} tok/s < {TOKENS_PER_SEC_WARN} soft limit.")

        assert max_s < INFERENCE_MAX_S, (
            f"Slowest inference {max_s:.1f}s exceeds hard limit of {INFERENCE_MAX_S}s"
        )

    def test_full_history_inference_latency(self, llm):
        """
        Maximum prompt size (20 snapshots) -- confirms the long prompt
        doesn't blow the context or add unacceptable latency.
        """
        rows = [[float(b) * 0.04 for b in range(NUM_BANDS)] for _ in range(HISTORY_LEN)]
        prompt = make_steel_prompt(rows)

        t0 = time.perf_counter()
        out = llm.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=128,
            temperature=0.0,
        )
        elapsed = time.perf_counter() - t0

        prompt_tokens = out["usage"]["prompt_tokens"]
        completion_tokens = out["usage"]["completion_tokens"]
        print(f"\nfull history: {elapsed:.2f}s  "
              f"prompt_tokens={prompt_tokens}  completion_tokens={completion_tokens}")

        assert elapsed < INFERENCE_MAX_S, (
            f"Full-history inference {elapsed:.1f}s exceeds hard limit"
        )
        assert prompt_tokens < 2048, (
            f"Prompt too long: {prompt_tokens} tokens -- may exceed context window"
        )
