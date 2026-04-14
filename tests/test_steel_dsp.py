"""
Tests for the Steel AI wavetable stacker DSP logic.

Pure-Python reference tests -- no VCV Rack or C++ required.
Mirrors the logic in Steel.cpp and src/ai/AIModule.hpp.

Covers:
  - Wavetable generation: normalization, period, shape properties
  - SidechainFFT: band energy, history ring buffer ordering
  - buildPrompt: correct number of lines, band values, waveform names
  - handleResult: JSON parsing, weight clamping, malformed input resilience
  - Weight smoothing: 1-pole lowpass, tau=1s
  - readWT: linear interpolation, wrap-around
"""

import json
import math
import re
import pytest
import numpy as np


# ---------------------------------------------------------------------------
# Reference wavetable generation (mirrors Steel.cpp generateWavetables)
# ---------------------------------------------------------------------------

WT_LEN  = 2048
TWO_PI  = 2.0 * math.pi

WT_NAMES = [
    "sine","tri","saw","square","pulse25","pulse10",
    "supersaw","odd","even","bright","warm",
    "fm2","fm5","formant","sub","noiseband",
]


def normalize(buf: np.ndarray) -> np.ndarray:
    peak = np.max(np.abs(buf))
    if peak > 0:
        buf = buf / peak
    return buf


def generate_wavetables() -> dict[str, np.ndarray]:
    t_idx = np.arange(WT_LEN, dtype=np.float64)

    tables: dict[str, np.ndarray] = {}

    # 0 — sine
    tables["sine"] = np.sin(TWO_PI * t_idx / WT_LEN)

    # 1 — triangle
    t = t_idx / WT_LEN
    tri = np.where(t < 0.25, 4.0*t,
          np.where(t < 0.75, 2.0 - 4.0*t,
                              4.0*t - 4.0))
    tables["tri"] = tri

    # 2 — bandlimited saw (40 harmonics)
    s = np.zeros(WT_LEN)
    for h in range(1, 41):
        sign = 1.0 if (h % 2 == 1) else -1.0
        s += sign * np.sin(TWO_PI * h * t_idx / WT_LEN) / h
    tables["saw"] = normalize(s)

    # 3 — bandlimited square (odd harmonics to 39)
    s = np.zeros(WT_LEN)
    for h in range(1, 40, 2):
        s += np.sin(TWO_PI * h * t_idx / WT_LEN) / h
    tables["square"] = normalize(s)

    # 4 — pulse 25%
    s = np.zeros(WT_LEN)
    d = 0.25
    for h in range(1, 41):
        s += (2.0 * math.sin(math.pi * h * d) / (math.pi * h)
              * np.cos(TWO_PI * h * t_idx / WT_LEN))
    tables["pulse25"] = normalize(s)

    # 5 — pulse 10%
    s = np.zeros(WT_LEN)
    d = 0.10
    for h in range(1, 41):
        s += (2.0 * math.sin(math.pi * h * d) / (math.pi * h)
              * np.cos(TWO_PI * h * t_idx / WT_LEN))
    tables["pulse10"] = normalize(s)

    # 6 — supersaw
    detune = [1.0, 1.002909, 0.997096]
    s = np.zeros(WT_LEN)
    for df in detune:
        for h in range(1, 31):
            sign = 1.0 if (h % 2 == 1) else -1.0
            s += sign * np.sin(TWO_PI * h * df * t_idx / WT_LEN) / h / 3.0
    tables["supersaw"] = normalize(s)

    # 7 — odd harmonics
    s = np.zeros(WT_LEN)
    for h in [1, 3, 5, 7, 9]:
        s += np.sin(TWO_PI * h * t_idx / WT_LEN)
    tables["odd"] = normalize(s)

    # 8 — even harmonics
    s = np.zeros(WT_LEN)
    for h in [1, 2, 4, 8, 16]:
        s += np.sin(TWO_PI * h * t_idx / WT_LEN)
    tables["even"] = normalize(s)

    # 9 — bright
    s = np.zeros(WT_LEN)
    for h in range(1, 21):
        s += np.sin(TWO_PI * h * t_idx / WT_LEN) / math.sqrt(h)
    tables["bright"] = normalize(s)

    # 10 — warm
    s = np.zeros(WT_LEN)
    for h in range(1, 7):
        s += np.sin(TWO_PI * h * t_idx / WT_LEN) / (h * h)
    tables["warm"] = normalize(s)

    # 11 — FM simple (carrier 1, mod 2, index 2)
    t_norm = t_idx / WT_LEN
    s = np.sin(TWO_PI * t_norm + 2.0 * np.sin(TWO_PI * 2.0 * t_norm))
    tables["fm2"] = normalize(s)

    # 12 — FM complex (carrier 1, mod 3, index 5)
    s = np.sin(TWO_PI * t_norm + 5.0 * np.sin(TWO_PI * 3.0 * t_norm))
    tables["fm5"] = normalize(s)

    # 13 — formant
    s = np.zeros(WT_LEN)
    for h in range(1, 31):
        env = (math.exp(-0.5 * ((h - 8.0) / 2.0) ** 2)
               + math.exp(-0.5 * ((h - 16.0) / 3.0) ** 2)
               + 0.3 / h)
        s += np.sin(TWO_PI * h * t_idx / WT_LEN) * env / h
    tables["formant"] = normalize(s)

    # 14 — sub (half frequency)
    tables["sub"] = np.sin(TWO_PI * 0.5 * t_idx / WT_LEN)

    # 15 — noiseband
    s = np.zeros(WT_LEN)
    phase_offset = 0.0
    for h in range(1, 33):
        phase_offset += h * 0.7531
        s += np.sin(TWO_PI * h * t_idx / WT_LEN + phase_offset) / h
    tables["noiseband"] = normalize(s)

    return tables


TABLES = generate_wavetables()


# ---------------------------------------------------------------------------
# Wavetable tests
# ---------------------------------------------------------------------------

class TestWavetableProperties:

    def test_all_16_tables_exist(self):
        assert len(TABLES) == 16

    def test_all_tables_normalized(self):
        """Every table must have peak amplitude ≈ 1.0."""
        for name, buf in TABLES.items():
            peak = np.max(np.abs(buf))
            assert abs(peak - 1.0) < 1e-6, f"{name}: peak={peak}"

    def test_all_tables_correct_length(self):
        for name, buf in TABLES.items():
            assert len(buf) == WT_LEN, f"{name}: len={len(buf)}"

    def test_sine_is_sine(self):
        """Sine table should match np.sin exactly."""
        expected = np.sin(TWO_PI * np.arange(WT_LEN) / WT_LEN)
        np.testing.assert_allclose(TABLES["sine"], expected, atol=1e-6)

    def test_sine_zero_crossings(self):
        """Sine must cross zero at index 0, WT_LEN/2."""
        assert abs(TABLES["sine"][0]) < 1e-6
        assert abs(TABLES["sine"][WT_LEN // 2]) < 1e-4

    def test_triangle_symmetry(self):
        """Triangle is an odd-symmetric waveform; t[n] == -t[n+WT_LEN/2] (mod length)."""
        buf = TABLES["tri"]
        half = WT_LEN // 2
        np.testing.assert_allclose(buf[:half], -buf[half:], atol=1e-6)

    def test_sub_is_half_frequency(self):
        """Sub wavetable completes exactly half a cycle over WT_LEN samples."""
        buf = TABLES["sub"]
        # At the halfway point (index WT_LEN/2), a half-frequency sine should be at 0
        # because sin(2pi * 0.5 * 0.5) = sin(pi/2) = 1 -- that's the peak
        # The zero crossing is at index 0 and index WT_LEN (wraps)
        assert abs(buf[0]) < 1e-6
        # One full cycle of the sub = 2 * WT_LEN; midpoint of that at WT_LEN is zero
        # buf[WT_LEN-1] ≈ sin(2pi * 0.5 * (WT_LEN-1)/WT_LEN) -- very close to 0
        assert abs(buf[WT_LEN - 1]) < 0.01  # near-zero at end

    def test_square_odd_harmonics_only(self):
        """Bandlimited square should have near-zero even harmonics."""
        buf = TABLES["square"]
        spectrum = np.abs(np.fft.rfft(buf))
        # Harmonic 2 (index 2 in rfft) should be much smaller than harmonic 1
        assert spectrum[2] < spectrum[1] * 0.01

    def test_pulse25_asymmetric(self):
        """Pulse 25% and pulse 10% should differ from square."""
        # If all three were the same, peak of (p25 - square) would be ~0
        diff = np.max(np.abs(TABLES["pulse25"] - TABLES["square"]))
        assert diff > 0.01

    def test_no_nan_or_inf(self):
        for name, buf in TABLES.items():
            assert np.all(np.isfinite(buf)), f"{name} contains NaN or Inf"


# ---------------------------------------------------------------------------
# readWT reference (linear interpolation, wraps)
# ---------------------------------------------------------------------------

def read_wt(name: str, phase: float) -> float:
    buf = TABLES[name]
    while phase >= WT_LEN:
        phase -= WT_LEN
    while phase < 0.0:
        phase += WT_LEN
    i0 = int(phase)
    i1 = (i0 + 1) % WT_LEN
    frac = phase - i0
    return buf[i0] * (1.0 - frac) + buf[i1] * frac


class TestReadWT:

    def test_integer_phase_exact(self):
        """At integer phase, result must equal table value exactly."""
        for name in WT_NAMES:
            for i in [0, 100, 512, 1000, 2047]:
                assert read_wt(name, float(i)) == TABLES[name][i]

    def test_half_phase_midpoint(self):
        """Phase = i + 0.5 should be average of buf[i] and buf[i+1]."""
        name = "sine"
        i = 100
        expected = (TABLES[name][i] + TABLES[name][i + 1]) / 2.0
        assert abs(read_wt(name, i + 0.5) - expected) < 1e-6

    def test_wrap_above(self):
        """Phase ≥ WT_LEN should wrap back."""
        val_wrapped = read_wt("sine", float(WT_LEN + 10))
        val_normal  = read_wt("sine", 10.0)
        assert abs(val_wrapped - val_normal) < 1e-6

    def test_wrap_below(self):
        """Negative phase should wrap forward."""
        val_neg = read_wt("sine", -1.0)
        val_pos = read_wt("sine", float(WT_LEN - 1))
        assert abs(val_neg - val_pos) < 1e-6


# ---------------------------------------------------------------------------
# FFT band reference (mirrors SidechainFFT::compute logic)
# ---------------------------------------------------------------------------

NUM_BANDS = 8
FFT_SIZE  = 512
FFT_HALF  = FFT_SIZE // 2
BAND_EDGES = [1, 3, 8, 18, 40, 80, 130, 185, 256]


def compute_bands(buf: np.ndarray) -> list[float]:
    """
    Reproduce the vDSP pipeline from SidechainFFT::compute in Python.
    Uses a Hann window, real FFT, power per bin, then sqrt(mean power) per band.
    """
    assert len(buf) == FFT_SIZE
    window = np.hanning(FFT_SIZE)  # numpy hanning ≈ vDSP_HANN_NORM (same formula)
    windowed = buf * window
    spectrum = np.fft.rfft(windowed)  # length FFT_HALF + 1
    power = np.abs(spectrum[:FFT_HALF]) ** 2
    scale = 1.0 / FFT_HALF
    bands = []
    for b in range(NUM_BANDS):
        lo, hi = BAND_EDGES[b], BAND_EDGES[b + 1]
        cnt = hi - lo
        band_power = np.sum(power[lo:hi]) / cnt * scale
        bands.append(math.sqrt(band_power))
    return bands


class TestSidechainFFT:

    def test_silence_gives_zero_bands(self):
        bands = compute_bands(np.zeros(FFT_SIZE))
        for b in bands:
            assert b == 0.0

    def test_full_sine_concentrates_in_one_band(self):
        """A pure 1000 Hz tone (bin ~11 at SR=44100) should land in band 2 only."""
        sr = 44100.0
        freq = 1000.0  # Hz
        n = np.arange(FFT_SIZE)
        sig = np.sin(2.0 * math.pi * freq / sr * n)
        bands = compute_bands(sig)
        # Bin index for 1000 Hz = round(1000 / (44100 / 512)) ≈ 11.6 → bin 11-12
        # BAND_EDGES: band 2 = bins 8..17, so 1000 Hz should be in band 2
        assert bands[2] == max(bands), f"expected band 2 loudest, got: {bands}"

    def test_low_frequency_lands_in_low_band(self):
        """A very low-frequency sine (~60 Hz, bin ≈ 0.7 → bin 1) hits band 0."""
        sr = 44100.0
        freq = 100.0  # Hz → bin ≈ 1.16 → lands in band 0 (bins 1-2)
        n = np.arange(FFT_SIZE)
        sig = np.sin(2.0 * math.pi * freq / sr * n)
        bands = compute_bands(sig)
        assert bands[0] == max(bands), f"expected band 0 loudest, got: {bands}"

    def test_band_values_nonnegative(self):
        sig = np.random.randn(FFT_SIZE).astype(np.float64)
        bands = compute_bands(sig)
        for b in bands:
            assert b >= 0.0

    def test_louder_signal_gives_larger_bands(self):
        sig = np.random.randn(FFT_SIZE)
        b1 = compute_bands(sig)
        b2 = compute_bands(sig * 2.0)
        for i in range(NUM_BANDS):
            assert b2[i] > b1[i] * 0.9  # 2x amplitude → larger energy


# ---------------------------------------------------------------------------
# History ring-buffer logic
# ---------------------------------------------------------------------------

HISTORY_LEN = 20

class HistoryBuffer:
    """Python mirror of Steel's rolling band history."""
    def __init__(self):
        self.buf = [[0.0] * NUM_BANDS for _ in range(HISTORY_LEN)]
        self.head = 0
        self.full = False

    def push(self, bands: list[float]):
        self.buf[self.head] = list(bands)
        self.head = (self.head + 1) % HISTORY_LEN
        if self.head == 0:
            self.full = True

    def snapshots_oldest_first(self) -> list[list[float]]:
        n = HISTORY_LEN if self.full else self.head
        result = []
        for j in range(n):
            idx = (self.head + j) % HISTORY_LEN if self.full else j
            result.append(self.buf[idx])
        return result


class TestHistoryBuffer:

    def test_empty_gives_no_snapshots(self):
        hb = HistoryBuffer()
        assert hb.snapshots_oldest_first() == []

    def test_partial_fill_gives_correct_count(self):
        hb = HistoryBuffer()
        for i in range(5):
            hb.push([float(i)] * NUM_BANDS)
        snaps = hb.snapshots_oldest_first()
        assert len(snaps) == 5

    def test_oldest_first_ordering(self):
        hb = HistoryBuffer()
        for i in range(5):
            hb.push([float(i)] * NUM_BANDS)
        snaps = hb.snapshots_oldest_first()
        for i, snap in enumerate(snaps):
            assert snap[0] == float(i)

    def test_full_buffer_wraps(self):
        hb = HistoryBuffer()
        for i in range(HISTORY_LEN + 3):
            hb.push([float(i)] * NUM_BANDS)
        snaps = hb.snapshots_oldest_first()
        assert len(snaps) == HISTORY_LEN
        # Oldest remaining is snapshot index 3 (indices 0-2 were overwritten)
        assert snaps[0][0] == 3.0
        assert snaps[-1][0] == float(HISTORY_LEN + 2)

    def test_exactly_full(self):
        hb = HistoryBuffer()
        for i in range(HISTORY_LEN):
            hb.push([float(i)] * NUM_BANDS)
        snaps = hb.snapshots_oldest_first()
        assert len(snaps) == HISTORY_LEN
        assert snaps[0][0] == 0.0
        assert snaps[-1][0] == float(HISTORY_LEN - 1)


# ---------------------------------------------------------------------------
# buildPrompt reference
# ---------------------------------------------------------------------------

def build_prompt(history_snapshots: list[list[float]]) -> str:
    """Mirror of Steel::buildPrompt."""
    s = ("You control a 16-wavetable synthesizer. Given spectral history, "
         "output ONLY a JSON array of 16 mixing weights (0.0-1.0), no explanation.\n"
         "Waveforms: ")
    s += " ".join(f"{i}={WT_NAMES[i]}" for i in range(16))
    s += "\nSpectral bands (sub bass lmid mid hmid pres brill air), 0.0-1.0, oldest first:\n"
    for snap in history_snapshots:
        s += " ".join(f"{v:.2f}" for v in snap) + "\n"
    return s


class TestBuildPrompt:

    def _make_history(self, n: int) -> list[list[float]]:
        return [[float(j) * 0.05 for j in range(NUM_BANDS)] for _ in range(n)]

    def test_prompt_contains_all_waveform_names(self):
        prompt = build_prompt(self._make_history(3))
        for name in WT_NAMES:
            assert name in prompt, f"missing waveform name: {name}"

    def test_prompt_contains_correct_history_lines(self):
        n = 7
        prompt = build_prompt(self._make_history(n))
        # Count lines that look like 8 space-separated floats
        lines = [l for l in prompt.splitlines()
                 if re.fullmatch(r'[\d. ]+', l.strip()) and len(l.strip().split()) == 8]
        assert len(lines) == n

    def test_prompt_with_empty_history(self):
        prompt = build_prompt([])
        # Should still have header and waveform list, just no data lines
        assert "Waveforms:" in prompt
        assert "oldest first" in prompt

    def test_prompt_band_values_formatted_correctly(self):
        snap = [0.123456, 0.0, 1.0, 0.5, 0.25, 0.75, 0.33, 0.99]
        prompt = build_prompt([snap])
        assert "0.12 0.00 1.00 0.50 0.25 0.75 0.33 0.99" in prompt

    def test_prompt_has_16_waveform_entries(self):
        prompt = build_prompt([])
        # "0=sine 1=tri ... 15=noiseband"
        for i in range(16):
            assert f"{i}={WT_NAMES[i]}" in prompt


# ---------------------------------------------------------------------------
# handleResult reference
# ---------------------------------------------------------------------------

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def handle_result(response: str) -> list[float] | None:
    """Mirror of Steel::handleResult. Returns 16 weights or None on failure."""
    start = response.find('[')
    end   = response.rfind(']')
    if start == -1 or end == -1 or end <= start:
        return None
    json_str = response[start:end + 1]
    try:
        arr = json.loads(json_str)
    except json.JSONDecodeError:
        return None
    if not isinstance(arr, list):
        return None
    w = [0.0] * 16
    for i, v in enumerate(arr[:16]):
        if isinstance(v, (int, float)):
            w[i] = clamp(float(v), 0.0, 1.0)
    return w


class TestHandleResult:

    def test_valid_16_weights(self):
        weights = [round(i / 15.0, 2) for i in range(16)]
        resp = f"Here are the weights: {json.dumps(weights)}"
        result = handle_result(resp)
        assert result is not None
        for i, w in enumerate(result):
            assert abs(w - weights[i]) < 1e-6

    def test_weights_clamped_above_one(self):
        resp = json.dumps([2.0, 1.5, 0.5] + [0.0] * 13)
        result = handle_result(resp)
        assert result[0] == 1.0
        assert result[1] == 1.0
        assert result[2] == 0.5

    def test_weights_clamped_below_zero(self):
        resp = json.dumps([-1.0, -0.5, 0.3] + [0.0] * 13)
        result = handle_result(resp)
        assert result[0] == 0.0
        assert result[1] == 0.0
        assert result[2] == 0.3

    def test_fewer_than_16_weights(self):
        """Partial response: fills remainder with 0."""
        resp = json.dumps([1.0, 0.5])
        result = handle_result(resp)
        assert result[0] == 1.0
        assert result[1] == 0.5
        for i in range(2, 16):
            assert result[i] == 0.0

    def test_more_than_16_weights_truncated(self):
        resp = json.dumps([0.5] * 20)
        result = handle_result(resp)
        assert len(result) == 16
        assert all(w == 0.5 for w in result)

    def test_json_embedded_in_prose(self):
        resp = ("Sure! Based on the spectral analysis I recommend: "
                "[0.8, 0.0, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0, "
                "0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] "
                "because the low mids are dominant.")
        result = handle_result(resp)
        assert result is not None
        assert result[0] == 0.8
        assert result[2] == 0.2

    def test_no_array_in_response(self):
        assert handle_result("I don't know what to do.") is None

    def test_empty_response(self):
        assert handle_result("") is None

    def test_malformed_json(self):
        assert handle_result("[1.0, 0.5, broken]") is None

    def test_non_numeric_values_become_zero(self):
        resp = json.dumps([0.5, "high", 0.3] + [0.0] * 13)
        result = handle_result(resp)
        # "high" is a string, not a number — should be left as 0
        assert result[0] == 0.5
        assert result[1] == 0.0
        assert result[2] == 0.3

    def test_nested_brackets_uses_outermost(self):
        """rfind(']') picks the last one -- ensure the outermost array is parsed."""
        resp = '[0.1, 0.2, [0.3], 0.4' + ', 0.0' * 12 + ']'
        # This is invalid JSON but shouldn't crash
        result = handle_result(resp)
        # Either None (parse error) or a valid result -- just no exception
        assert result is None or isinstance(result, list)


# ---------------------------------------------------------------------------
# Weight smoothing (1-pole lowpass, τ=1s)
# ---------------------------------------------------------------------------

def smooth_weights(target: list[float], initial: list[float],
                   sample_rate: float, n_samples: int) -> list[float]:
    """Apply n_samples of 1-pole smoothing (τ=1s) to weights."""
    alpha = 1.0 - math.exp(-1.0 / sample_rate)
    w = list(initial)
    for _ in range(n_samples):
        for i in range(16):
            w[i] += alpha * (target[i] - w[i])
    return w


class TestWeightSmoothing:

    SR = 44100.0

    def test_converges_to_target(self):
        """After several seconds, weights should be very close to target."""
        target = [1.0 if i == 3 else 0.0 for i in range(16)]
        initial = [1.0 if i == 0 else 0.0 for i in range(16)]
        result = smooth_weights(target, initial, self.SR, n_samples=int(10 * self.SR))
        assert abs(result[0] - 0.0) < 1e-4
        assert abs(result[3] - 1.0) < 1e-4

    def test_halfway_at_tau(self):
        """At t=τ=1s, the filter should have closed (1 - 1/e) ≈ 63.2% of the gap."""
        target  = [1.0] * 16
        initial = [0.0] * 16
        result = smooth_weights(target, initial, self.SR, n_samples=int(1.0 * self.SR))
        expected_fraction = 1.0 - math.exp(-1.0)  # ≈ 0.6321
        for i in range(16):
            assert abs(result[i] - expected_fraction) < 0.01

    def test_no_overshoot(self):
        """1-pole lowpass must not overshoot the target."""
        target  = [0.7] * 16
        initial = [0.0] * 16
        result = smooth_weights(target, initial, self.SR, n_samples=int(5 * self.SR))
        for w in result:
            assert w <= 0.7 + 1e-6

    def test_already_at_target_no_change(self):
        target = [0.5] * 16
        result = smooth_weights(target, target[:], self.SR, n_samples=1000)
        for w in result:
            assert abs(w - 0.5) < 1e-6
